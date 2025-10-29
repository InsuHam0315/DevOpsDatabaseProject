# backend/optimizer/engine.py

# --- 1. 필요한 라이브러리 임포트 ---
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import Dict, List, Any
import math
import datetime as dt
import json # JSON 출력을 위해 추가

# 직접 만든 모듈 임포트
try:
    from services.db_handler import get_optimizer_input_data, save_optimization_results
    from services.co2_calculator import co2_for_route, VehicleEF, Segment
except ImportError:
    print("❌ ERROR: 'services' 모듈을 찾을 수 없습니다. backend 폴더에서 실행 중인지 확인하세요.")
    exit()


# --- Helper Function: 거리 계산 (Haversine 공식) ---
def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """두 지점의 위도, 경도를 받아 직선 거리(km)를 계산합니다."""
    R = 6371
    if not all([lat1, lon1, lat2, lon2]):
        print(f"⚠️ 좌표값이 누락되어 거리를 0으로 처리합니다: ({lat1}, {lon1}) -> ({lat2}, {lon2})")
        return 0.0
    try:
        lat1_f, lon1_f, lat2_f, lon2_f = map(float, [lat1, lon1, lat2, lon2])
    except (ValueError, TypeError) as e:
        print(f"⚠️ 좌표값 변환 오류 ({e}), 거리를 0으로 처리합니다.")
        return 0.0

    phi1, phi2 = math.radians(lat1_f), math.radians(lat2_f)
    delta_phi = math.radians(lat2_f - lat1_f)
    delta_lambda = math.radians(lon2_f - lon1_f)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# --- Helper Function: 시간창 변환 (Timestamp -> 초) ---
def convert_time_window_to_seconds(tw_start, tw_end, base_time: dt.datetime):
    """DB Timestamp를 경로 시작 기준 초로 변환합니다."""
    if tw_start is None or tw_end is None:
        return (0, 86400) # 제약 없음
    try:
        # DB에서 datetime 객체로 오는지 확인 필요 (oracledb 설정 따라 다름)
        start_dt = tw_start if isinstance(tw_start, dt.datetime) else dt.datetime.strptime(str(tw_start)[:19], '%Y-%m-%d %H:%M:%S')
        end_dt = tw_end if isinstance(tw_end, dt.datetime) else dt.datetime.strptime(str(tw_end)[:19], '%Y-%m-%d %H:%M:%S')

        start_seconds = max(0, int((start_dt - base_time).total_seconds()))
        end_seconds = max(0, int((end_dt - base_time).total_seconds()))

        if end_seconds < start_seconds:
            print(f"⚠️ 시간창 오류: 종료 시간({end_dt}) < 시작 시간({start_dt}). 제약 없음 처리.")
            return (0, 86400)
        return (start_seconds, end_seconds)
    except Exception as e:
        print(f"⚠️ 시간창 변환 오류 ({e}): TW_START={tw_start}, TW_END={tw_end}. 제약 없음 처리.")
        return (0, 86400)

# --- 2. 메인 최적화 함수 정의 ---
def run_optimization(run_id: str, vehicle_ids: List[str], route_option_name: str = "OR-Tools Optimal") -> Dict:
    """ 핵심 최적화 로직 """
    print(f"🚀 run_id: {run_id} 차량: {vehicle_ids} 최적화 시작 (옵션: {route_option_name})")

    # --- 단계 A: DB 데이터 가져오기 ---
    try:
        print("   DB에서 데이터 가져오는 중...")
        input_data = get_optimizer_input_data(run_id, vehicle_ids)
        if not input_data.get("depot") or not input_data.get("jobs") or not input_data.get("vehicles"):
             raise ValueError("DB 조회 결과 필수 데이터(depot, jobs, vehicles)가 누락되었습니다.")
    except Exception as e:
        print(f"❌ DB 조회 중 오류 발생: {e}")
        return {"status": "failed", "message": f"DB 조회 실패: {e}"}

    # --- 단계 B: OR-Tools 데이터 모델링 ---
    print("   OR-Tools용 데이터 모델링 중...")
    try:
        locations_data = [input_data["depot"]] + input_data["jobs"]
        num_locations = len(locations_data)
        if num_locations <= 1: raise ValueError("최소 2개 이상의 위치(차고지 포함) 필요.")

        distance_matrix = [[0] * num_locations for _ in range(num_locations)]
        time_matrix = [[0] * num_locations for _ in range(num_locations)]
        AVG_SPEED_KMH = 40

        for i in range(num_locations):
            for j in range(num_locations):
                if i != j:
                    dist_km = calculate_haversine_distance(
                        locations_data[i].get('latitude'), locations_data[i].get('longitude'),
                        locations_data[j].get('latitude'), locations_data[j].get('longitude')
                    )
                    distance_matrix[i][j] = dist_km
                    time_sec = int((dist_km / (AVG_SPEED_KMH / 3600))) if AVG_SPEED_KMH > 0 else 0
                    time_matrix[i][j] = time_sec

        print(f"   거리 및 시간 행렬 생성 완료 (크기: {num_locations}x{num_locations})")

        demands = [0] + [int(float(job.get('demand_kg', 0))) for job in input_data['jobs']]
        num_vehicles = len(input_data['vehicles'])
        if num_vehicles <= 0: raise ValueError("최소 1대 이상의 차량 필요.")
        vehicle_capacities = [int(float(v.get('capacity_kg', 0))) for v in input_data['vehicles']]
        vehicle_ef_data = {v['vehicle_id']: VehicleEF(
                                ef_gpkm=float(v.get('co2_gpkm', 0)),
                                idle_gps=float(v.get('idle_gps', 0)),
                                capacity_kg=float(v.get('capacity_kg', 0))
                           ) for v in input_data['vehicles']}

        run_date_str = run_id.split('_')[1]
        base_datetime = dt.datetime.strptime(run_date_str, '%Y%m%d')
        time_windows = [(0, 86400)] # 차고지
        for job in input_data['jobs']:
            tw = convert_time_window_to_seconds(job.get('tw_start'), job.get('tw_end'), base_datetime)
            time_windows.append(tw)
        print(f"   시간창 데이터 준비 완료: {time_windows}")

    except Exception as e:
        print(f"❌ 데이터 모델링 중 오류 발생: {e}")
        return {"status": "failed", "message": f"데이터 모델링 오류: {e}"}

    # --- 단계 C: OR-Tools 모델 생성 ---
    print("   OR-Tools 모델 생성 중...")
    try:
        manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)
        print(f"    DEBUG: manager 생성 완료 (Nodes: {manager.GetNumberOfNodes()}, Vehicles: {manager.GetNumberOfVehicles()})")
    except Exception as e:
         print(f"❌ OR-Tools 모델 생성 실패 (num_locations={num_locations}, num_vehicles={num_vehicles}): {e}")
         return {"status": "failed", "message": f"OR-Tools 모델 생성 오류: {e}"}

    # --- 단계 D: 비용 함수(CO2) 정의 ---
    print("   CO2 비용 함수 정의 중...")
    capacity_dimension_name = 'Capacity' # 용량 차원 이름 일관성 유지

    # 비용 콜백 함수 정의 (예외 처리 강화)
    def co2_callback_func(from_index, to_index):
        try:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            vehicle_index = routing.VehicleIndex(from_index) # Should be valid if called during solve

            # 인덱스 유효성 검사 (추가)
            if not (0 <= from_node < num_locations and 0 <= to_node < num_locations):
                 print(f"⚠️ co2_callback: 유효하지 않은 노드 인덱스! from:{from_node}, to:{to_node}")
                 return 9999999 # 매우 큰 비용 반환하여 해당 경로 회피 유도

            current_vehicle_id = input_data['vehicles'][vehicle_index]['vehicle_id']
            vehicle_info = vehicle_ef_data[current_vehicle_id]

            # TODO: 정확한 load_kg 반영 필요 (State dependent transit callback 등 고급 기법)
            current_load_approximation = demands[from_node] # 임시

            segment = Segment(
                distance_km=distance_matrix[from_node][to_node],
                base_time_sec=time_matrix[from_node][to_node],
                slope_pct=0.0,
                load_kg=float(current_load_approximation)
            )
            co2_result = co2_for_route(segments=[segment], v=vehicle_info)
            return int(co2_result['co2_total_g'])
        except OverflowError as oe:
             print(f"❌ co2_callback: OverflowError! from:{from_index}, to:{to_index}, Error:{oe}")
             raise # 에러 전파하여 Solve 단계에서 잡도록 함
        except Exception as e:
             print(f"❌ co2_callback: 예외 발생! from:{from_index}, to:{to_index}, Error:{e}")
             return 9999999 # 매우 큰 비용 반환

    transit_callback_index = routing.RegisterTransitCallback(co2_callback_func)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # --- 단계 E: 제약 조건 추가 (용량, 시간창) ---
    print("   제약 조건 추가 중...")
    # 1. 용량 제약
    def demand_callback_func(from_index):
        try:
            node_index = manager.IndexToNode(from_index)
            if 0 <= node_index < len(demands):
                return demands[node_index]
            else:
                print(f"⚠️ demand_callback: 유효하지 않은 노드 인덱스 {node_index} (from_index: {from_index})")
                return 0
        except OverflowError as oe: # Overflow 에러 명시적 처리
             print(f"❌ demand_callback: OverflowError! from_index:{from_index}, Error:{oe}")
             raise # 에러 전파
        except Exception as e:
             print(f"❌ demand_callback: 오류 발생! from_index:{from_index}, Error:{e}")
             return 0

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback_func)
    try:
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0, vehicle_capacities, True, capacity_dimension_name
        )
    except Exception as e:
         print(f"❌ 용량 제약 추가 실패: {e}")
         return {"status": "failed", "message": f"용량 제약 추가 오류: {e}"}

    # 2. 시간창 제약
    def time_callback_func(from_index, to_index):
        try:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            if not (0 <= from_node < num_locations and 0 <= to_node < num_locations):
                 print(f"⚠️ time_callback: 유효하지 않은 노드 인덱스! from:{from_node}, to:{to_node}")
                 return 86400 # 매우 긴 시간 반환
            service_time = 0
            return time_matrix[from_node][to_node] + service_time
        except OverflowError as oe:
             print(f"❌ time_callback: OverflowError! from:{from_index}, to:{to_index}, Error:{oe}")
             raise # 에러 전파
        except Exception as e:
             print(f"❌ time_callback: 오류 발생! from:{from_index}, to:{to_index}, Error:{e}")
             return 86400

    time_callback_index = routing.RegisterTransitCallback(time_callback_func)
    time_dimension_name = 'Time'
    try:
        routing.AddDimension(
            time_callback_index, 86400, 86400, False, time_dimension_name
        )
        time_dimension = routing.GetDimensionOrDie(time_dimension_name)
        for location_idx, time_window in enumerate(time_windows):
            if location_idx == 0: continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(int(time_window[0]), int(time_window[1]))
    except Exception as e:
         print(f"❌ 시간 제약 추가 실패: {e}")
         return {"status": "failed", "message": f"시간 제약 추가 오류: {e}"}


    # --- 단계 F: 탐색 파라미터 설정 및 해결 ---
    print("   최적화 문제 해결 중...")
    solution = None # solution 변수 초기화
    try:
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.FromSeconds(10)
        # 디버깅: 로그 레벨 설정
        # search_parameters.log_search = True

        solution = routing.SolveWithParameters(search_parameters)

    except (SystemError, OverflowError) as e: # Solve 단계에서 OverflowError 잡기
         print(f"❌ 최적화 실행 중 심각한 오류 발생: {e}")
         # TODO: RUNS 테이블 상태 'FAILED'로 업데이트
         return {"status": "failed", "message": f"최적화 실행 오류: {e}"}
    except Exception as e:
         print(f"❌ 최적화 실행 중 예상치 못한 오류 발생: {e}")
         # TODO: RUNS 테이블 상태 'FAILED'로 업데이트
         return {"status": "failed", "message": f"최적화 실행 오류: {e}"}


    # --- 단계 G: 해답 파싱 및 DB 저장 ---
    print("   해답 파싱 중...")
    if solution:
        print(f"✅ run_id: {run_id} 최적화 완료")
        # (이하 결과 파싱 및 저장 로직은 이전과 동일...)
        total_co2 = solution.ObjectiveValue()
        total_distance = 0
        assignments_to_save = []
        capacity_dimension = routing.GetDimensionOrDie(capacity_dimension_name)
        time_dimension = routing.GetDimensionOrDie(time_dimension_name)

        for vehicle_id_idx in range(num_vehicles):
            index = routing.Start(vehicle_id_idx)
            step_order = 1
            start_node_index = manager.IndexToNode(index) # 루프 전 초기화

            while not routing.IsEnd(index):
                previous_index = index
                start_node_index = manager.IndexToNode(previous_index)
                index = solution.Value(routing.NextVar(index))
                end_node_index = manager.IndexToNode(index)

                step_actual_distance = distance_matrix[start_node_index][end_node_index]
                step_time_sec = time_matrix[start_node_index][end_node_index]
                load_var_start = capacity_dimension.CumulVar(previous_index)
                current_load_kg = solution.Value(load_var_start)

                step_co2 = 0.0 # 초기화
                try:
                    current_vehicle_id = input_data['vehicles'][vehicle_id_idx]['vehicle_id']
                    vehicle_info = vehicle_ef_data[current_vehicle_id]
                    segment = Segment(
                        distance_km=step_actual_distance,
                        base_time_sec=step_time_sec,
                        slope_pct=0.0,
                        load_kg=float(current_load_kg)
                    )
                    co2_result = co2_for_route(segments=[segment], v=vehicle_info)
                    step_co2 = co2_result['co2_total_g']
                except Exception as e:
                     print(f"⚠️ Warning: 스텝별 CO2 재계산 중 오류 ({e}). 0으로 처리.")

                assignment = {
                    "run_id": run_id, "route_option_name": route_option_name,
                    "vehicle_id": input_data['vehicles'][vehicle_id_idx]['vehicle_id'],
                    "step_order": step_order,
                    "start_job_id": None if start_node_index == 0 else input_data['jobs'][start_node_index-1]['job_id'],
                    "end_job_id": None if end_node_index == 0 else input_data['jobs'][end_node_index-1]['job_id'],
                    "distance_km": step_actual_distance, "co2_g": round(step_co2, 5),
                    "load_kg": float(current_load_kg), "time_min": round(step_time_sec / 60),
                    "avg_gradient_pct": 0.0, "congestion_factor": 1.0
                }
                assignments_to_save.append(assignment)
                total_distance += step_actual_distance
                step_order += 1

        max_end_time = 0
        for i in range(num_vehicles):
            try:
                end_index = routing.End(i)
                time_var = time_dimension.CumulVar(end_index)
                max_end_time = max(max_end_time, solution.Min(time_var))
            except Exception as e:
                 print(f"⚠️ Warning: 차량 {i}의 종료 시간 가져오기 실패 ({e})")
        total_time_min_accurate = round(max_end_time / 60)

        summary_to_save = {
            "run_id": run_id, "route_option_name": route_option_name,
            "total_distance_km": round(total_distance, 2),
            "total_co2_g": total_co2,
            "total_time_min": total_time_min_accurate
        }

        try:
            print("   결과를 DB에 저장하는 중...")
            save_optimization_results(run_id, summary_to_save, assignments_to_save)
        except Exception as e:
             print(f"❌ DB 저장 중 오류 발생: {e}")
             return {
                 "status": "warning",
                 "message": f"Optimization succeeded but failed to save results: {e}",
                 "summary": summary_to_save, "assignments": assignments_to_save
             }

        result = {
            "status": "success", "run_id": run_id,
            "summary": summary_to_save, "assignments": assignments_to_save
        }
        return result
    else:
        print(f"❌ run_id: {run_id} 해답을 찾지 못함")
        return {"status": "failed", "message": "해답을 찾지 못했습니다"}

# --- 3. 직접 실행 테스트를 위한 메인 블록 ---
if __name__ == '__main__':
    test_run_id = 'RUN_20251015_001'
    test_vehicle_ids = ['부산82가1234']
    try:
        final_result = run_optimization(test_run_id, test_vehicle_ids)
    except Exception as main_e: # 최상위 레벨에서 예외 처리
        print(f"💥 메인 실행 중 심각한 오류 발생: {main_e}")
        final_result = {"status": "error", "message": f"메인 실행 오류: {main_e}"}

    print("\n--- 최종 최적화 결과 ---")
    try:
        # datetime 객체 직렬화 오류 방지 위해 default=str 추가
        print(json.dumps(final_result, indent=2, ensure_ascii=False, default=str))
    except Exception as json_e:
        print(f"💥 결과 출력(JSON) 중 오류 발생: {json_e}")
        print(final_result) # JSON 변환 실패 시 원본 객체 출력
    print("-------------------------------")