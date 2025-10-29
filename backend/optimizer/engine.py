# backend/optimizer/engine.py
"""
OR-Tools 기반 VRP 엔진.
- 목표: 총 CO2 배출 최소화(기본). 거리/시간/CO2 가중치 조합 가능.
- 엔진은 DB에 직접 접근하지 않는다. 모든 데이터는 서비스/ETL에서 준비해 주입한다.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from ortools.constraint_solver import pywrapcp, routing_enums_pb2


# ------------------------------
# 데이터 모델
# ------------------------------

@dataclass
class VehicleSpec:
    """엔진이 이해하는 차량 스펙"""
    name: str
    capacity_kg: float
    ef_gpkm: float     # 주행 배출계수 (g/km)
    idle_gps: float    # 공회전 배출계수 (g/sec)


@dataclass
class EngineSettings:
    """목표함수 가중치/임계치 (SETTINGS에서 읽어 전달 권장)"""
    alpha_load: float = 0.10            # 적재율 가중(코스트에는 영향 제한적으로 사용)
    beta_grade: float = 0.03            # 경사 1% 당 추가 배출률
    grade_cap: float = 0.30             # 경사 가중 상한
    speed_idle_threshold: float = 15.0  # km/h 이하이면 저속/공회전
    w_distance: float = 0.0             # 거리 최소화 가중 (현재 목적함수에는 반영 X)
    w_time: float = 0.0                 # 시간 최소화 가중  (현재 목적함수에는 반영 X)
    w_co2: float = 1.0                  # CO2 최소화 가중 (사후 평가에 반영)
    large_penalty: int = 10_000_000     # 미방문 벌점(Disjunction)


@dataclass
class SolveInput:
    """
    엔진 입력 (서비스/ETL에서 계산/수집한 값을 그대로 넣는다)
    """
    # 네트워크
    distance_km: List[List[float]]      # 대칭/비대칭 허용
    duration_sec: List[List[float]]     # 기본 이동시간(혼잡 전/후 어느 쪽이든 일관되게)
    slope_pct: Optional[List[List[float]]] = None  # 각 엣지 평균 경사(%) [선택]
    # 수요/제약
    demands_kg: Optional[List[int]] = None         # 각 노드 수요(Depot=0은 0)
    time_windows: Optional[List[Tuple[int, int]]] = None  # 각 노드 TW(sec) (Depot 포함)
    depot_index: int = 0
    # 차량
    vehicles: List[VehicleSpec] = field(default_factory=list)
    # 환경/가중
    settings: EngineSettings = field(default_factory=EngineSettings)
    # 혼잡 계수 (시간 늘리기/저속비율 보정) - 선택
    tf: float = 1.0
    idle_f: float = 0.0


@dataclass
class RouteResult:
    """한 차량의 결과 경로"""
    vehicle_name: str
    node_sequence: List[int]  # 방문 순서(노드 인덱스)
    distance_km: float
    drive_time_sec: float
    co2_drive_g: float
    co2_idle_g: float
    co2_total_g: float


@dataclass
class SolveResult:
    """전체 해 결과"""
    routes: List[RouteResult]
    total_distance_km: float
    total_time_sec: float
    total_co2_drive_g: float
    total_co2_idle_g: float
    total_co2_g: float
    status: str  # "NOT_SOLVED"/"FEASIBLE"/"INFEASIBLE"/"TIMEOUT"/"UNKNOWN"


# ------------------------------
# 내부 유틸
# ------------------------------

def _avg_speed_kmh(dist_km: float, sec: float) -> float:
    if sec <= 0:
        return 999.0
    return dist_km / (sec / 3600.0)


def _edge_co2_grams(
    dist_km: float,
    base_sec: float,
    slope_pct: float,
    load_ratio: float,
    veh: VehicleSpec,
    s: EngineSettings,
    tf: float,
    idle_f: float,
):
    """
    co2 계산식(네 co2_calculator와 동일한 로직)을 엣지 단위로 적용.
    반환: (drive_g, idle_g, total_g)
    """
    # 혼잡 보정 시간
    t = base_sec * max(1.0, tf)

    # 가중치
    load_w = 1.0 + s.alpha_load * max(0.0, min(1.0, load_ratio))
    grade_w = 1.0 + min(s.grade_cap, s.beta_grade * max(0.0, slope_pct))

    # 주행 CO2
    drive_g = dist_km * veh.ef_gpkm * load_w * grade_w

    # 평균속도 → 저속/공회전 계수
    v_kmh = _avg_speed_kmh(dist_km, t)
    idle_factor = max(0.0, (s.speed_idle_threshold - v_kmh) / s.speed_idle_threshold)

    idle_g = t * veh.idle_gps * (idle_factor + max(0.0, idle_f))
    return drive_g, idle_g, (drive_g + idle_g)


# ------------------------------
# 메인 엔진
# ------------------------------

def solve_vrp(inp: SolveInput) -> SolveResult:
    """OR-Tools로 VRP(TW/용량 지원)를 풀고 CO2/거리/시간 요약을 반환."""
    if not inp.vehicles:
        return SolveResult([], 0.0, 0.0, 0.0, 0.0, 0.0, "INFEASIBLE")

    n_nodes = len(inp.distance_km)
    n_vehicles = len(inp.vehicles)
    depot = inp.depot_index

    # 라우팅 모델 구성
    manager = pywrapcp.RoutingIndexManager(n_nodes, n_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    # Index ↔ Node
    def nid(index):  # RoutingIndex -> Node
        return manager.IndexToNode(index)

    # 데이터 단축표기
    data_dist = inp.distance_km
    data_time = inp.duration_sec
    data_slope = inp.slope_pct or [[0.0] * n_nodes for _ in range(n_nodes)]
    demands = inp.demands_kg or [0] * n_nodes
    s = inp.settings
    vehicles = inp.vehicles

    # 거리 콜백 (m 단위 정수)
    def distance_cb(from_index, to_index):
        i, j = nid(from_index), nid(to_index)
        return int(round(data_dist[i][j] * 1000))

    transit_distance = routing.RegisterTransitCallback(distance_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_distance)

    # 시간 콜백 (초 단위 정수) — 차원 추가
    def time_cb(from_index, to_index):
        i, j = nid(from_index), nid(to_index)
        return int(round(data_time[i][j]))

    transit_time = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(
        transit_time,
        3600,          # wait 허용(1시간)
        24 * 3600,     # 24시간 상한
        False,         # 누적 시작 0 고정 아님
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    # 타임 윈도우(있으면 적용)
    if inp.time_windows:
        for node, (tw_start, tw_end) in enumerate(inp.time_windows):
            index = manager.NodeToIndex(node)
            time_dim.CumulVar(index).SetRange(int(tw_start), int(tw_end))

    # 용량 차원(수요가 있으면)
    if any(demands):
        def demand_cb(from_index):
            i = nid(from_index)
            return int(demands[i])

        demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
        routing.AddDimensionWithVehicleCapacity(
            demand_idx,
            0,  # slack
            [int(v.capacity_kg) for v in vehicles],
            True,
            "Capacity",
        )

    # 미방문 벌점(soft constraints)
    for node in range(n_nodes):
        if node == depot:
            continue
        routing.AddDisjunction([manager.NodeToIndex(node)], s.large_penalty)

    # 탐색 파라미터
    search = pywrapcp.DefaultRoutingSearchParameters()
    search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search.time_limit.FromSeconds(10)  # 필요시 늘리기

    # 풀기
    solution = routing.SolveWithParameters(search)

    # 상태코드 매핑 (pywrapcp.RoutingModel.* 상수 사용)
    status_code = routing.status()
    status_map = {
        pywrapcp.RoutingModel.ROUTING_NOT_SOLVED: "NOT_SOLVED",
        pywrapcp.RoutingModel.ROUTING_SUCCESS: "FEASIBLE",
        pywrapcp.RoutingModel.ROUTING_FAIL: "INFEASIBLE",
        pywrapcp.RoutingModel.ROUTING_FAIL_TIMEOUT: "TIMEOUT",
    }
    status = status_map.get(status_code, "UNKNOWN")

    # 해를 못 찾으면 빈 결과 반환
    if solution is None:
        return SolveResult([], 0.0, 0.0, 0.0, 0.0, 0.0, status)

    # 해석: 경로 별 co2/거리/시간 계산 (혼잡/경사/적재 반영)
    routes: List[RouteResult] = []
    total_dist_km = 0.0
    total_time_sec = 0.0
    total_co2_drive = 0.0
    total_co2_idle = 0.0

    for v_idx in range(n_vehicles):
        idx = routing.Start(v_idx)
        path_nodes: List[int] = []
        veh = vehicles[v_idx]

        route_dist = 0.0
        route_time = 0.0
        route_drive = 0.0
        route_idle = 0.0

        # 간단 로드 모델: 출발 시 풀 적재로 가정, 고객 방문 시 하차
        remaining_load = veh.capacity_kg

        while not routing.IsEnd(idx):
            next_idx = solution.Value(routing.NextVar(idx))
            i, j = nid(idx), nid(next_idx)

            d_km = data_dist[i][j]
            t_sec = data_time[i][j]
            slope = data_slope[i][j] if data_slope else 0.0

            # 적재율 추정
            cap = max(veh.capacity_kg, 1.0)
            load_ratio = min(1.0, max(0.0, remaining_load / cap))

            # 엣지 CO2
            drive_g, idle_g, _ = _edge_co2_grams(
                dist_km=d_km,
                base_sec=t_sec,
                slope_pct=slope,
                load_ratio=load_ratio,
                veh=veh,
                s=s,
                tf=inp.tf,
                idle_f=inp.idle_f,
            )

            route_dist += d_km
            route_time += t_sec * max(1.0, inp.tf)  # 보고용 시간은 tf 반영
            route_drive += drive_g
            route_idle += idle_g

            path_nodes.append(i)

            # 하차 처리(다음 노드가 고객이면)
            if j != depot and inp.demands_kg:
                remaining_load = max(0.0, remaining_load - max(0, inp.demands_kg[j]))

            idx = next_idx

        path_nodes.append(nid(idx))  # End(보통 depot)

        routes.append(RouteResult(
            vehicle_name=veh.name,
            node_sequence=path_nodes,
            distance_km=round(route_dist, 4),
            drive_time_sec=int(round(route_time)),
            co2_drive_g=round(route_drive, 2),
            co2_idle_g=round(route_idle, 2),
            co2_total_g=round(route_drive + route_idle, 2),
        ))

        total_dist_km += route_dist
        total_time_sec += route_time
        total_co2_drive += route_drive
        total_co2_idle += route_idle

    return SolveResult(
        routes=routes,
        total_distance_km=round(total_dist_km, 4),
        total_time_sec=int(round(total_time_sec)),
        total_co2_drive_g=round(total_co2_drive, 2),
        total_co2_idle_g=round(total_co2_idle, 2),
        total_co2_g=round(total_co2_drive + total_co2_idle, 2),
        status=status,
    )
