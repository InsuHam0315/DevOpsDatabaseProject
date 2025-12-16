from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import Dict, List, Any, Tuple
import math
import datetime as dt
import json
import sys

try:
    from services.db_handler import get_optimizer_input_data, save_optimization_results
    from services.co2_calculator import (
        co2_for_route,
        VehicleEF,
        Segment,
        get_settings,
        get_congestion_factors,
        get_weather_penalty_value
    )
    from services.path_data_loader import create_kakao_route_matrices, get_combined_route_alternatives
except ImportError as e:
    print(f"ERROR: 'services' ?? ??? ??. ?? ?? ??: {e}")
    sys.exit(1)


# --- Helper Function: 시간창 변환 (Timestamp -> 초) ---
def convert_time_window_to_seconds(tw_start, tw_end, base_time: dt.datetime):
    """DB Timestamp를 경로 시작 기준 초로 변환합니다."""
    if tw_start is None or tw_end is None:
        return (0, 86400)
    try:
        start_dt = tw_start if isinstance(tw_start, dt.datetime) else dt.datetime.strptime(str(tw_start)[:19], '%Y-%m-%d %H:%M:%S')
        end_dt = tw_end if isinstance(tw_end, dt.datetime) else dt.datetime.strptime(str(tw_end)[:19], '%Y-%m-%d %H:%M:%S')
        start_seconds = max(0, int((start_dt - base_time).total_seconds()))
        end_seconds = max(0, int((end_dt - base_time).total_seconds()))
        if end_seconds < start_seconds:
            return (0, 86400)
        return (start_seconds, end_seconds)
    except Exception:
        return (0, 86400)


def _build_p2p_response_summary(summary_db: Dict, route_option_name: str,
                                origin_coord: Tuple[float, float],
                                dest_coord: Tuple[float, float],
                                vehicle_id: str,
                                route_label: str = None,
                                provider: str = None,
                                polyline_override: Any = None) -> Dict:
    """Response 용 요약 + polyline(없으면 직선)을 추가해 지도에서 바로 사용할 수 있게 만든다."""
    start_latlng = {"lat": origin_coord[1], "lng": origin_coord[0]}
    end_latlng = {"lat": dest_coord[1], "lng": dest_coord[0]}
    polyline = polyline_override if polyline_override else [
        [origin_coord[0], origin_coord[1]],
        [dest_coord[0], dest_coord[1]]
    ]
    response_summary = {**summary_db}
    response_summary.update({
        "route_option_name": route_option_name,
        "route_label": route_label,
        "vehicle_id": vehicle_id,
        "provider": provider,
        "start": start_latlng,
        "end": end_latlng,
        "polyline": polyline
    })
    return response_summary


# --- 2. 메인 최적화 함수 정의 ---
def run_optimization(run_id: str, vehicle_ids: List[str]) -> Dict:
    """P2P: 거리/CO2 두 경로 비교, VRP: 기존 Eco-Cost 최적화."""
    ECO_ROUTE_NAME = "CO2 Optimal Route"  # legacy label (kept for compatibility)
    KAKAO_ROUTE_NAME = "Kakao Route"
    ORS_ROUTE_NAME = "ORS Route"

    print(f"🚀 run_id: {run_id} 최적화 시작")

    eco_summary, kakao_summary = {}, None
    eco_assignments, kakao_assignments = [], []
    route_results_payload: List[Dict[str, Any]] = []
    comparison_payload: Dict[str, Any] = {}

    # --- 단계 A: DB 데이터 및 SETTINGS 가져오기 ---
    try:
        print("   DB에서 데이터 가져오는 중...")
        input_data = get_optimizer_input_data(run_id, vehicle_ids)
        if not input_data.get("depot") or not input_data.get("jobs") or not input_data.get("vehicles"):
            raise ValueError("DB 조회 결과 필수 데이터가 누락되었습니다.")

        num_jobs = len(input_data.get("jobs", []))
        if num_jobs == 0:
            return {"status": "failed", "message": "최적화할 작업(Job)이 없습니다.", "run_id": run_id}

        CO2_SETTINGS = get_settings()
        base_datetime = input_data['run_date']
        CONG_FACTORS = get_congestion_factors(base_datetime)
        WEATHER_PENALTY = get_weather_penalty_value(base_datetime, CO2_SETTINGS)
        DEFAULT_SLOPE = CO2_SETTINGS.get('DEFAULT_SLOPE_PCT', 0.0)

        total_demand = sum(int(float(job.get('demand_kg', 0))) for job in input_data['jobs'])
        vehicle_ef_data = {
            v['vehicle_id']: VehicleEF(
                ef_gpkm=float(v.get('co2_gpkm', 0)),
                idle_gps=float(v.get('idle_gps', 0)),
                capacity_kg=float(v.get('capacity_kg', 0))
            )
            for v in input_data['vehicles']
        }

    except Exception as e:
        print(f"❌ DB 조회/설정 중 오류 발생: {e}")
        return {"status": "failed", "message": f"DB 조회/설정 실패: {e}", "run_id": run_id}

    # -----------------------------------------------------------------
    # --- ⭐ 로직 분기 1: Job이 1개일 때 (P2P - 대안 경로 비교) ---
    # -----------------------------------------------------------------
    if num_jobs == 1:
        print(" 🚗 단일 작업(P2P) 최적화 로직 실행...")
        try:
            depot = input_data["depot"]
            job = input_data["jobs"][0]

            origin_coord = (depot['longitude'], depot['latitude'])
            dest_coord = (job['longitude'], job['latitude'])

            tw_p2p = convert_time_window_to_seconds(job.get('tw_start'), job.get('tw_end'), base_datetime)

            vehicle_id = input_data['vehicles'][0]['vehicle_id']
            vehicle_info = vehicle_ef_data[vehicle_id]

            alternative_routes = get_combined_route_alternatives(origin_coord, dest_coord)
            if not alternative_routes:
                raise ValueError("대안 경로를 가져오지 못했습니다.")

            valid_routes = []

            print(f"   {len(alternative_routes)}개의 대안 경로 CO2 재평가 시작...")

            for route in alternative_routes:
                route_label = route.get('route_name') or route.get('priority') or "ROUTE"
                raw_segments = route.get('segments', []) or []
                segments = [
                    Segment(
                        distance_km=s.get('distance_km', 0.0),
                        link_id=s.get('link_id'),
                        base_time_sec=s.get('base_time_sec', 0.0),
                        slope_pct=DEFAULT_SLOPE,
                        load_kg=float(total_demand)
                    )
                    for s in raw_segments
                    if s.get('distance_km', 0) is not None
                ]
                # ORS가 세그먼트를 비워서 줄 경우를 대비해 단일 구간으로 보정
                if not segments:
                    segments = [
                        Segment(
                            distance_km=float(route.get('total_distance_km', 0.0)),
                            link_id=None,
                            base_time_sec=float(route.get('total_time_sec', 0.0)),
                            slope_pct=DEFAULT_SLOPE,
                            load_kg=float(total_demand)
                        )
                    ]

                co2_result = co2_for_route(
                    segments=segments,
                    v=vehicle_info,
                    start_time=base_datetime,
                    congestion_factors=CONG_FACTORS,
                    settings=CO2_SETTINGS,
                    weather_penalty_value=WEATHER_PENALTY
                )

                arrival_time_sec = co2_result['total_time_sec']
                if arrival_time_sec > tw_p2p[1]:
                    print(f"   ⚠️ 경로 ({route_label}) 시간 초과 (예상: {arrival_time_sec:.0f}s, 마감: {tw_p2p[1]}s)")
                    continue

                valid_routes.append({
                    "provider": route.get("provider"),
                    "route_name": route_label,
                    "total_distance_km": float(route.get('total_distance_km', 0)),
                    "co2_total_g": float(co2_result['co2_total_g']),
                    "total_time_sec": float(co2_result['total_time_sec']),
                    "total_time_min": float(co2_result['total_time_sec']) / 60.0,
                    "segments": route.get('segments', []),
                    "polyline": route.get("polyline")
                })

            if not valid_routes:
                raise ValueError("시간창을 만족하는 경로가 없습니다.")

            kakao_route = None
            ors_route = None
            for r in valid_routes:
                if r.get("provider") == "kakao" and (kakao_route is None or r['co2_total_g'] < kakao_route['co2_total_g']):
                    kakao_route = r
                if r.get("provider") == "ors" and (ors_route is None or r['co2_total_g'] < ors_route['co2_total_g']):
                    ors_route = r

            candidates = [r for r in [kakao_route, ors_route] if r]
            if not candidates:
                raise ValueError("Kakao/ORS 경로가 유효하지 않습니다.")

            # 추천 = CO2 최소, 동률시 거리/시간 순
            def _score(r):
                return (r['co2_total_g'], r['total_distance_km'], r['total_time_sec'])
            recommended = min(candidates, key=_score)
            baseline = [c for c in candidates if c is not recommended]
            baseline = baseline[0] if baseline else recommended

            # Summary/assignments 저장
            def _route_name_for_provider(r):
                return ORS_ROUTE_NAME if r.get("provider") == "ors" else KAKAO_ROUTE_NAME

            rec_route_name = _route_name_for_provider(recommended)
            base_route_name = _route_name_for_provider(baseline)

            # 저장/응답
            rec_summary = _format_p2p_summary(recommended, run_id, rec_route_name)
            rec_assignments = _format_p2p_assignments(
                recommended, run_id, rec_route_name, vehicle_id, job['job_id'],
                total_demand, DEFAULT_SLOPE, origin_coord, dest_coord
            )
            rec_summary_response = _build_p2p_response_summary(
                rec_summary, rec_route_name, origin_coord, dest_coord, vehicle_id,
                recommended.get("route_name"), recommended.get("provider"), recommended.get("polyline")
            )
            save_optimization_results(run_id, rec_summary, rec_assignments)

            base_summary = _format_p2p_summary(baseline, run_id, base_route_name)
            base_assignments = _format_p2p_assignments(
                baseline, run_id, base_route_name, vehicle_id, job['job_id'],
                total_demand, DEFAULT_SLOPE, origin_coord, dest_coord
            )
            base_summary_response = _build_p2p_response_summary(
                base_summary, base_route_name, origin_coord, dest_coord, vehicle_id,
                baseline.get("route_name"), baseline.get("provider"), baseline.get("polyline")
            )
            save_optimization_results(run_id, base_summary, base_assignments)

            route_results_payload.append({
                "route_name": rec_route_name,
                "summary": rec_summary_response,
                "assignments": rec_assignments
            })
            if baseline is not recommended:
                route_results_payload.append({
                    "route_name": base_route_name,
                    "summary": base_summary_response,
                    "assignments": base_assignments
                })

            base_co2 = base_summary.get('total_co2_g', 0) or 0.0
            rec_co2 = rec_summary.get('total_co2_g', 0) or 0.0
            base_distance = base_summary.get('total_distance_km', 0) or 0.0
            rec_distance = rec_summary.get('total_distance_km', 0) or 0.0
            base_time = base_summary.get('total_time_min', 0) or 0.0
            rec_time = rec_summary.get('total_time_min', 0) or 0.0

            co2_saving_g = round(base_co2 - rec_co2, 3)
            co2_saving_pct = round((co2_saving_g / (base_co2 if base_co2 != 0 else 1.0)) * 100, 2)
            distance_diff_km = round(rec_distance - base_distance, 3)
            distance_diff_pct = round((distance_diff_km / (base_distance if base_distance != 0 else 1.0)) * 100, 2)
            time_diff_min = round(rec_time - base_time, 3)

            comparison_payload = {
                "recommended_route": rec_route_name,
                "baseline_route": base_route_name,
                "recommended_provider": recommended.get("provider"),
                "baseline_provider": baseline.get("provider"),
                "co2_saving_g": co2_saving_g,
                "co2_saving_pct": co2_saving_pct,
                "distance_diff_km": distance_diff_km,
                "distance_diff_pct": distance_diff_pct,
                "time_diff_min": time_diff_min
            }

        except Exception as e:
            print(f"❌ P2P 최적화 중 오류 발생: {e}")
            return {"status": "failed", "message": f"P2P 최적화 오류: {e}", "run_id": run_id}

    # -----------------------------------------------------------------
    # --- ⭐ 로직 분기 2: Job이 2개 이상일 때 (VRP - 순서 최적화) ---
    # -----------------------------------------------------------------
    else:
        print(" 🚚 다중 작업(VRP) 최적화 로직 실행...")
        try:
            locations_data = [input_data["depot"]] + input_data["jobs"]
            num_locations = len(locations_data)

            distance_matrix, time_matrix, segment_data_map = create_kakao_route_matrices(locations_data)

            demands = [0] + [-int(float(job.get('demand_kg', 0))) for job in input_data['jobs']]
            num_vehicles = len(input_data['vehicles'])
            vehicle_capacities = [int(float(v.get('capacity_kg', 0))) for v in input_data['vehicles']]

            time_windows = [(0, 86400)]
            for job in input_data['jobs']:
                tw = convert_time_window_to_seconds(job.get('tw_start'), job.get('tw_end'), base_datetime)
                time_windows.append(tw)

            starts = [0] * num_vehicles
            ends = [0] * num_vehicles
            manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, starts, ends)
            routing = pywrapcp.RoutingModel(manager)

            capacity_dimension_name = 'Capacity'
            CO2_WEIGHT = CO2_SETTINGS.get('ECO_CO2_WEIGHT', 0.8)
            TIME_WEIGHT = CO2_SETTINGS.get('ECO_TIME_WEIGHT', 0.2)
            CO2_SCALE_FACTOR = 1000

            def eco_cost_callback_func(from_index, to_index):
                try:
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    vehicle_index = routing.VehicleIndex(from_index)
                    segments_raw = segment_data_map.get((from_node, to_node), [])
                    if not segments_raw:
                        return math.inf

                    current_load_approximation = total_demand
                    segments_for_co2 = [
                        Segment(s['distance_km'], s['link_id'], s['base_time_sec'], DEFAULT_SLOPE, float(current_load_approximation))
                        for s in segments_raw
                    ]
                    current_vehicle_id = input_data['vehicles'][vehicle_index]['vehicle_id']
                    vehicle_info = vehicle_ef_data[current_vehicle_id]
                    co2_result = co2_for_route(segments_for_co2, vehicle_info, base_datetime, CONG_FACTORS, CO2_SETTINGS, WEATHER_PENALTY)
                    co2_g = co2_result['co2_total_g']
                    time_sec_actual = co2_result['total_time_sec']
                    eco_cost = (CO2_WEIGHT * (co2_g / CO2_SCALE_FACTOR)) + (TIME_WEIGHT * time_sec_actual)
                    return int(eco_cost * 1000)
                except Exception:
                    return math.inf
            transit_callback_index = routing.RegisterTransitCallback(eco_cost_callback_func)

            def time_callback_func(from_index, to_index):
                try:
                    from_node = manager.IndexToNode(from_index)
                    segments_raw = segment_data_map.get((from_node, manager.IndexToNode(to_index)), [])
                    if not segments_raw:
                        return 86400

                    vehicle_index = routing.VehicleIndex(from_index)
                    current_vehicle_id = input_data['vehicles'][vehicle_index]['vehicle_id']
                    vehicle_info = vehicle_ef_data[current_vehicle_id]

                    segments_for_co2 = [Segment(s['distance_km'], s['link_id'], s['base_time_sec']) for s in segments_raw]
                    co2_result = co2_for_route(segments_for_co2, vehicle_info, base_datetime, CONG_FACTORS, CO2_SETTINGS, WEATHER_PENALTY)
                    return int(co2_result['total_time_sec'])
                except Exception:
                    return 86400
            time_callback_index = routing.RegisterTransitCallback(time_callback_func)

            def demand_callback_func(from_index):
                try:
                    node_index = manager.IndexToNode(from_index)
                    return demands[node_index]
                except Exception:
                    return 0
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback_func)

            max_capacity = max(vehicle_capacities) if vehicle_capacities else 0
            routing.AddDimension(demand_callback_index, 0, max_capacity, False, capacity_dimension_name)

            time_dimension_name = 'Time'
            initial_depot_time = int(time_windows[0][0])
            routing.AddDimension(time_callback_index, 86400, 86400, True, time_dimension_name)
            time_dimension = routing.GetDimensionOrDie(time_dimension_name)

            for vehicle_id_idx in range(num_vehicles):
                depot_index = routing.Start(vehicle_id_idx)
                time_dimension.CumulVar(depot_index).SetRange(initial_depot_time, initial_depot_time)
            for location_idx, time_window in enumerate(time_windows):
                if location_idx == 0:
                    continue
                index = manager.NodeToIndex(location_idx)
                time_dimension.CumulVar(index).SetRange(int(time_window[0]), int(time_window[1]))

            capacity_dimension = routing.GetDimensionOrDie(capacity_dimension_name)
            for vehicle_id_idx in range(num_vehicles):
                depot_index = routing.Start(vehicle_id_idx)
                capacity_dimension.CumulVar(depot_index).SetRange(total_demand, total_demand)

            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            search_parameters.time_limit.FromSeconds(10)

            print("   OR-Tools 최적화 (Eco-Cost) 실행 중...")
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            solution = routing.SolveWithParameters(search_parameters)

            if solution:
                print(f"✅ {ECO_ROUTE_NAME} 파싱 시작 (편도 경로 계산).")
                eco_summary, eco_assignments, _ = parse_and_save_solution(
                    solution, routing, manager, input_data, vehicle_ef_data, segment_data_map,
                    capacity_dimension, time_dimension,
                    base_datetime, ECO_ROUTE_NAME, DEFAULT_SLOPE,
                    CONG_FACTORS, CO2_SETTINGS, WEATHER_PENALTY, distance_matrix, run_id
                )
                save_optimization_results(run_id, eco_summary, eco_assignments)
                route_results_payload.append({
                    "route_name": ECO_ROUTE_NAME,
                    "summary": eco_summary,
                    "assignments": eco_assignments
                })
            else:
                print("⚠️ OR-Tools 해답을 찾지 못했습니다.")

        except Exception as e:
            print(f"❌ VRP 최적화 중 오류 발생: {e}")
            return {"status": "failed", "message": f"VRP 최적화 오류: {e}", "run_id": run_id}

    # --- 단계 I: 최종 결과 비교 및 반환 ---
    final_result = {"status": "success", "run_id": run_id, "results": route_results_payload}

    if comparison_payload:
        final_result['comparison'] = comparison_payload

    if not final_result['results']:
        final_result = {"status": "failed", "message": "최적화 및 비교 경로를 모두 찾지 못했습니다.", "run_id": run_id}

    return final_result


# --------------------------------------------------------------------------
# 3. 헬퍼 함수: OR-Tools 결과 파싱 (VRP용)
# (이 함수는 VRP 시나리오에서만 사용됨)
# --------------------------------------------------------------------------
def parse_and_save_solution(solution, routing, manager, input_data, vehicle_ef_data, segment_data_map,
                            capacity_dimension, time_dimension,
                            base_datetime, route_option_name, default_slope,
                            CONG_FACTORS, CO2_SETTINGS, WEATHER_PENALTY, distance_matrix, run_id):
    """ OR-Tools Solution을 파싱하여 DB 저장용 Summary와 Assignments를 반환합니다. (편도 계산) """
    total_distance = 0
    assignments_to_save = []
    total_co2_g_accurate = 0.0
    num_vehicles = manager.GetNumberOfVehicles()

    max_end_time_sec = 0.0

    for vehicle_id_idx in range(num_vehicles):
        index = routing.Start(vehicle_id_idx)
        step_order = 1
        vehicle_total_time_sec = 0.0

        while not routing.IsEnd(index):
            previous_index = index
            start_node_index = manager.IndexToNode(previous_index)

            time_start_sec = solution.Value(time_dimension.CumulVar(previous_index))
            time_start_dt = base_datetime + dt.timedelta(seconds=time_start_sec)
            current_load_kg = solution.Value(capacity_dimension.CumulVar(previous_index))

            index = solution.Value(routing.NextVar(index))

            if routing.IsEnd(index):
                print(f"   [One-Way Stop] Vehicle {vehicle_id_idx} reached final job. Skipping return arc to depot.")
                break

            end_node_index = manager.IndexToNode(index)

            segments_raw = segment_data_map.get((start_node_index, end_node_index), [])
            step_actual_distance = distance_matrix[start_node_index][end_node_index]

            current_vehicle_id = input_data['vehicles'][vehicle_id_idx]['vehicle_id']
            vehicle_info = vehicle_ef_data.get(current_vehicle_id)

            if segments_raw:
                segments_for_co2 = [
                    Segment(
                        distance_km=s['distance_km'], link_id=s['link_id'], base_time_sec=s['base_time_sec'],
                        slope_pct=default_slope, load_kg=float(current_load_kg)
                    ) for s in segments_raw
                ]

                co2_result = co2_for_route(segments=segments_for_co2, v=vehicle_info, start_time=time_start_dt,
                                             congestion_factors=CONG_FACTORS, settings=CO2_SETTINGS,
                                             weather_penalty_value=WEATHER_PENALTY)
                step_co2 = co2_result['co2_total_g']
                step_time_sec_accurate = co2_result['total_time_sec']
            else:
                step_co2 = 0.0
                step_time_sec_accurate = 0.0

            total_co2_g_accurate += step_co2
            total_distance += step_actual_distance
            vehicle_total_time_sec += step_time_sec_accurate

            assignment = {
                "run_id": run_id, "route_option_name": route_option_name,
                "vehicle_id": current_vehicle_id, "step_order": step_order,
                "start_job_id": None if start_node_index == 0 else input_data['jobs'][start_node_index-1]['job_id'],
                "end_job_id": None if end_node_index == 0 else input_data['jobs'][end_node_index-1]['job_id'],
                "distance_km": step_actual_distance, "co2_g": round(step_co2, 5),
                "load_kg": float(current_load_kg),
                "time_min": round(step_time_sec_accurate / 60, 2),
                "avg_gradient_pct": default_slope, "congestion_factor": 1.0
            }
            assignments_to_save.append(assignment)
            step_order += 1

        max_end_time_sec = max(max_end_time_sec, vehicle_total_time_sec)

    total_time_min_accurate = round(max_end_time_sec / 60, 2)

    summary_to_save = {
        "run_id": run_id, "route_option_name": route_option_name,
        "total_distance_km": round(total_distance, 2),
        "total_co2_g": round(total_co2_g_accurate, 3),
        "total_time_min": total_time_min_accurate
    }
    return summary_to_save, assignments_to_save, total_co2_g_accurate


# --------------------------------------------------------------------------
# 4. [신규] 헬퍼 함수: P2P 결과 포맷팅
# (이 함수들은 P2P 시나리오에서만 사용됨)
# --------------------------------------------------------------------------

def _format_p2p_summary(route_data: Dict, run_id: str, route_option_name: str) -> Dict:
    """ P2P Kakao 대안 경로 데이터를 RUN_SUMMARY 형식으로 포맷합니다. """
    return {
        "run_id": run_id,
        "route_option_name": route_option_name,
        "total_distance_km": round(route_data['total_distance_km'], 2),
        "total_co2_g": round(route_data['co2_total_g'], 3),
        "total_time_min": round(route_data['total_time_min'], 2)
    }


def _format_p2p_assignments(route_data: Dict, run_id: str, route_option_name: str,
                            vehicle_id: str, job_id: int, load_kg: float, slope_pct: float,
                            origin_coord: Tuple[float, float] = None, dest_coord: Tuple[float, float] = None) -> List[Dict]:
    """ P2P Kakao 대안 경로 데이터를 ASSIGNMENTS 형식(리스트)으로 포맷합니다. """
    assignment = {
        "run_id": run_id,
        "route_option_name": route_option_name,
        "vehicle_id": vehicle_id,
        "step_order": 1,
        "start_job_id": None,
        "end_job_id": job_id,
        "distance_km": round(route_data['total_distance_km'], 3),
        "co2_g": round(route_data['co2_total_g'], 5),
        "load_kg": float(load_kg),
        "time_min": round(route_data['total_time_min'], 2),
        "avg_gradient_pct": slope_pct,
        "congestion_factor": 1.0
    }
    if origin_coord and dest_coord:
        assignment.update({
            "start_lat": origin_coord[1],
            "start_lng": origin_coord[0],
            "end_lat": dest_coord[1],
            "end_lng": dest_coord[0],
        })
    return [assignment]


# --------------------------------------------------------------------------
# 5. 직접 실행 테스트를 위한 메인 블록
# --------------------------------------------------------------------------
if __name__ == '__main__':

    print("--- Engine.py 단독 테스트 시작 ---")

    print("\n[테스트 1: 단일 작업 (RUN_20251015_001)]")
    test_run_id_p2p = 'RUN_20251015_001'
    test_vehicle_ids_p2p = ['부산82가1234']
    try:
        final_result_p2p = run_optimization(test_run_id_p2p, test_vehicle_ids_p2p)
        print("\n--- P2P 최종 최적화 결과 ---")
        print(json.dumps(final_result_p2p, indent=2, ensure_ascii=False, default=str))
    except Exception as main_e:
        print(f"\n💥 P2P 메인 실행 중 심각한 오류 발생: {main_e}")

    print("\n[테스트 2: 다중 작업 (RUN_VRP_TEST_001)]")
    test_run_id_vrp = 'RUN_VRP_TEST_001'
    test_vehicle_ids_vrp = ['부산82가1234']
    try:
        final_result_vrp = run_optimization(test_run_id_vrp, test_vehicle_ids_vrp)
        print("\n--- VRP 최종 최적화 결과 ---")
        print(json.dumps(final_result_vrp, indent=2, ensure_ascii=False, default=str))
    except ConnectionError:
        print("\n💥 DB 연결 실패: config.py 설정을 확인하세요.")
    except Exception as main_e:
        print(f"\n💥 VRP 메인 실행 중 심각한 오류 발생: {main_e}")

    print("-------------------------------")
