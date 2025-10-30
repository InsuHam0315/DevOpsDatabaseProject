from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import Dict, List, Any, Tuple
import math
import datetime as dt
import json 
import sys 

# 직접 만든 모듈 임포트
try:
    from services.db_handler import get_optimizer_input_data, save_optimization_results
    # co2_calculator에서 상수 로드 함수와 메인 계산 함수 모두 임포트
    from services.co2_calculator import co2_for_route, VehicleEF, Segment, get_settings, get_congestion_factors, get_weather_penalty_value
    from services.path_data_loader import create_kakao_route_matrices, get_kakao_route
except ImportError as e:
    print(f"❌ ERROR: 'services' 모듈 임포트 실패. 경로 확인 필요: {e}")
    sys.exit(1)


# --- Helper Function: 시간창 변환 (Timestamp -> 초) ---
def convert_time_window_to_seconds(tw_start, tw_end, base_time: dt.datetime):
    """DB Timestamp를 경로 시작 기준 초로 변환합니다."""
    if tw_start is None or tw_end is None: return (0, 86400) 
    try:
        start_dt = tw_start if isinstance(tw_start, dt.datetime) else dt.datetime.strptime(str(tw_start)[:19], '%Y-%m-%d %H:%M:%S')
        end_dt = tw_end if isinstance(tw_end, dt.datetime) else dt.datetime.strptime(str(tw_end)[:19], '%Y-%m-%d %H:%M:%S')
        start_seconds = max(0, int((start_dt - base_time).total_seconds()))
        end_seconds = max(0, int((end_dt - base_time).total_seconds()))
        if end_seconds < start_seconds: return (0, 86400)
        return (start_seconds, end_seconds)
    except Exception:
        return (0, 86400)

# --- 2. 메인 최적화 함수 정의 ---
def run_optimization(run_id: str, vehicle_ids: List[str]) -> Dict:
    """ 핵심 최적화 로직 및 카카오 추천 경로 비교 분석을 수행합니다. """
    ECO_ROUTE_NAME = "Our Eco Optimal Route"
    KAKAO_ROUTE_NAME = "Kakao Recommended Route"

    print(f"🚀 run_id: {run_id} 최적화 시작")

    # --- 단계 A: DB 데이터 및 SETTINGS 가져오기 (성능 최적화: 1회만 DB 조회) ---
    try:
        print("   DB에서 데이터 가져오는 중...")
        input_data = get_optimizer_input_data(run_id, vehicle_ids)
        if not input_data.get("depot") or not input_data.get("jobs") or not input_data.get("vehicles"):
            raise ValueError("DB 조회 결과 필수 데이터가 누락되었습니다.")
        
        # ★★★ 성능 최적화 핵심: CO2 계산에 필요한 상수를 1회만 로드 ★★★
        CO2_SETTINGS = get_settings() 
        CO2_WEIGHT = CO2_SETTINGS.get('ECO_CO2_WEIGHT', 0.8)
        TIME_WEIGHT = CO2_SETTINGS.get('ECO_TIME_WEIGHT', 0.2)
        CO2_SCALE_FACTOR = 1000 
        
        base_datetime = input_data['run_date'] 
        CONG_FACTORS = get_congestion_factors(base_datetime) 
        WEATHER_PENALTY = get_weather_penalty_value(base_datetime, CO2_SETTINGS) 
        
        # 사용자 선택 경사도 로드
        DEFAULT_SLOPE = CO2_SETTINGS.get('DEFAULT_SLOPE_PCT', 0.0)
        if DEFAULT_SLOPE not in [0.0, 0.5, 1.0]: DEFAULT_SLOPE = 0.0
        
        print(f"   설정값: CO2_W={CO2_WEIGHT}, TIME_W={TIME_WEIGHT}, SLOPE={DEFAULT_SLOPE}%, TF={CONG_FACTORS['tf']}")
        
    except Exception as e:
        print(f"❌ DB 조회/설정 중 오류 발생: {e}")
        return {"status": "failed", "message": f"DB 조회/설정 실패: {e}", "run_id": run_id}

    # --- 단계 B: OR-Tools 데이터 모델링 (Kakao API 통합) ---
    try:
        print("   OR-Tools용 데이터 모델링 및 Kakao API 호출 중...")
        locations_data = [input_data["depot"]] + input_data["jobs"]
        num_locations = len(locations_data)
        
        # Kakao API를 사용하여 실제 도로 기반 행렬 및 Segment 데이터 생성
        distance_matrix, time_matrix, segment_data_map = create_kakao_route_matrices(locations_data)

        # 차량, 수요, 시간창 설정
        demands = [0] + [int(float(job.get('demand_kg', 0))) for job in input_data['jobs']]
        num_vehicles = len(input_data['vehicles'])
        
        vehicle_capacities = [int(float(v.get('capacity_kg', 0))) for v in input_data['vehicles']]
        vehicle_ef_data = {v['vehicle_id']: VehicleEF(
                                ef_gpkm=float(v.get('co2_gpkm', 0)), idle_gps=float(v.get('idle_gps', 0)),
                                capacity_kg=float(v.get('capacity_kg', 0))
                           ) for v in input_data['vehicles']}

        time_windows = [(0, 86400)] 
        for job in input_data['jobs']:
            tw = convert_time_window_to_seconds(job.get('tw_start'), job.get('tw_end'), base_datetime)
            time_windows.append(tw)

    except Exception as e:
        print(f"❌ 데이터 모델링/Kakao API 호출 중 오류 발생: {e}")
        return {"status": "failed", "message": f"데이터 모델링 오류: {e}", "run_id": run_id}

    # --- 단계 C: OR-Tools 모델 생성 ---
    try:
        # NOTE: 왕복 경로로 모델링 (Depot에서 시작, Depot으로 복귀)
        starts = [0] * num_vehicles
        ends = [0] * num_vehicles
        # ⭐ 이 부분을 단일 라인 변수로 압축하여 들여쓰기 문제를 방지합니다.
        manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, starts, ends) 
        routing = pywrapcp.RoutingModel(manager)
    except Exception as e:
        return {"status": "failed", "message": f"OR-Tools 모델 생성 오류: {e}", "run_id": run_id}

    # --- 단계 D: 비용 함수(CO2 + Time) 정의 - Eco Cost (상수 전달) ---
    capacity_dimension_name = 'Capacity' 

    def eco_cost_callback_func(from_index, to_index):
        """ [성능 최적화] CO2 및 시간 비용을 복합적으로 고려한 친환경 비용을 반환합니다. """
        try:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            vehicle_index = routing.VehicleIndex(from_index)
            
            if not (0 <= from_node < num_locations and 0 <= to_node < num_locations): return math.inf

            segments_raw = segment_data_map.get((from_node, to_node), [])
            if not segments_raw: return math.inf 
                 
            current_time_approx = base_datetime + dt.timedelta(seconds=time_windows[0][0]) 
            current_load_approximation = demands[from_node] 

            segments_for_co2 = [
                Segment(
                    distance_km=s['distance_km'], link_id=s['link_id'], base_time_sec=s['base_time_sec'],
                    slope_pct=DEFAULT_SLOPE, load_kg=float(current_load_approximation)
                ) for s in segments_raw
            ]
            
            current_vehicle_id = input_data['vehicles'][vehicle_index]['vehicle_id']
            vehicle_info = vehicle_ef_data[current_vehicle_id]
            
            # 상수 인자 전달
            co2_result = co2_for_route(segments=segments_for_co2, v=vehicle_info, start_time=current_time_approx,
                                         congestion_factors=CONG_FACTORS, settings=CO2_SETTINGS, 
                                         weather_penalty_value=WEATHER_PENALTY)
            co2_g = co2_result['co2_total_g']
            time_sec_actual = co2_result['total_time_sec']

            eco_cost = (CO2_WEIGHT * (co2_g / CO2_SCALE_FACTOR)) + (TIME_WEIGHT * time_sec_actual)
            
            return int(eco_cost * 1000)
            
        except Exception as e:
            # print(f"❌ eco_cost_callback 오류: {e}")
            return math.inf 

    transit_callback_index = routing.RegisterTransitCallback(eco_cost_callback_func)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)


    # --- 단계 E: 제약 조건 추가 (Time Dimension - 상수 전달) ---
    def time_callback_func(from_index, to_index):
        """ 
        Time Dimension에 사용: ITS/혼잡도 반영된 실제 이동 시간 (초) 
        현재 차량의 정보를 사용하여 정확한 time_sec를 계산합니다. (버그 수정)
        """
        try:
            from_node = manager.IndexToNode(from_index)
            segments_raw = segment_data_map.get((from_node, manager.IndexToNode(to_index)), [])
            if not segments_raw: return 86400

            current_time_approx = base_datetime + dt.timedelta(seconds=time_windows[0][0])
            
            # ⭐ 수정된 로직: 현재 운행 차량의 정보를 사용하여 vehicle_info를 가져옵니다.
            vehicle_index = routing.VehicleIndex(from_index)
            current_vehicle_id = input_data['vehicles'][vehicle_index]['vehicle_id']
            vehicle_info = vehicle_ef_data[current_vehicle_id]
            
            segments_for_co2 = [
                Segment(
                    distance_km=s['distance_km'], link_id=s['link_id'], base_time_sec=s['base_time_sec']
                ) for s in segments_raw 
            ]
            
            # 상수 인자 전달
            co2_result = co2_for_route(segments=segments_for_co2, v=vehicle_info, start_time=current_time_approx,
                                         congestion_factors=CONG_FACTORS, settings=CO2_SETTINGS, 
                                         weather_penalty_value=WEATHER_PENALTY)

            return int(co2_result['total_time_sec'])
        except Exception:
            return 86400 

    # 1. 용량 제약 (유지)
    def demand_callback_func(from_index):
        try:
            node_index = manager.IndexToNode(from_index)
            return demands[node_index]
        except Exception:
            return 0
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback_func)
    
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, vehicle_capacities, True, capacity_dimension_name)

    # 2. Time Dimension 설정 (유지)
    time_callback_index = routing.RegisterTransitCallback(time_callback_func)
    time_dimension_name = 'Time'
    initial_depot_time = int(time_windows[0][0]) 
    
    routing.AddDimension(time_callback_index, 86400, 86400, True, time_dimension_name)
    
    # Dimension 객체를 여기서 정의하여 아래 파싱 헬퍼 함수로 전달합니다.
    capacity_dimension = routing.GetDimensionOrDie(capacity_dimension_name)
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)


    # Depot 및 Job 시간창 설정 (유지)
    for vehicle_id_idx in range(num_vehicles):
        depot_index = routing.Start(vehicle_id_idx)
        time_dimension.CumulVar(depot_index).SetRange(initial_depot_time, initial_depot_time)
        
    for location_idx, time_window in enumerate(time_windows):
        if location_idx == 0: continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(int(time_window[0]), int(time_window[1]))

    # --- 단계 F: OR-Tools Solve ---
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.FromSeconds(10)
    
    solution = None
    try:
        print("   OR-Tools 최적화 (Eco-Cost) 실행 중...")
        solution = routing.SolveWithParameters(search_parameters)
    except Exception as e:
        print(f"❌ OR-Tools Solve 중 오류 발생: {e}")
        return {"status": "failed", "message": f"OR-Tools Solve 오류: {e}", "run_id": run_id}

    # --- 단계 G: 해답 파싱 및 DB 저장 (Our Eco Optimal Route - 편도 경로만 계산) ---
    eco_summary, eco_assignments = {}, []
    
    if solution:
        print(f"✅ Our Eco Optimal Route 파싱 시작 (편도 경로 계산).")
        eco_summary, eco_assignments, total_co2_g_accurate = parse_and_save_solution(
            solution, routing, manager, input_data, vehicle_ef_data, segment_data_map, 
            capacity_dimension, time_dimension, 
            base_datetime, ECO_ROUTE_NAME, DEFAULT_SLOPE,
            CONG_FACTORS, CO2_SETTINGS, WEATHER_PENALTY, distance_matrix, run_id
        )
        save_optimization_results(run_id, eco_summary, eco_assignments)
    else:
        print("⚠️ OR-Tools 해답을 찾지 못했습니다.")
    
    # --- 단계 H: 카카오 추천 경로 분석 및 저장 (Benchmark Route) ---
    print("   카카오 추천 경로 (Benchmark) 분석 중...")
    
    kakao_summary = None
    
    if input_data['jobs']:
        start_coord = (input_data['depot']['longitude'], input_data['depot']['latitude'])
        end_coord = (input_data['jobs'][0]['longitude'], input_data['jobs'][0]['latitude'])
        
        kakao_route_info = get_kakao_route(start_coord, end_coord, car_type=6)

        if kakao_route_info:
            kakao_summary, kakao_assignments, kakao_co2 = analyze_kakao_route(
                run_id, input_data, vehicle_ef_data, KAKAO_ROUTE_NAME, kakao_route_info, DEFAULT_SLOPE,
                CONG_FACTORS, CO2_SETTINGS, WEATHER_PENALTY
            )
            save_optimization_results(run_id, kakao_summary, kakao_assignments)
            
        else:
            print("⚠️ 카카오 API 호출 실패 또는 경로를 찾지 못하여 비교 경로 생략.")
            
    # --- 단계 I: 최종 결과 비교 및 반환 (최종 점검) ---
    final_result = {"status": "success", "run_id": run_id}
    final_result['results'] = []
    
    if eco_summary: final_result['results'].append({"route_name": ECO_ROUTE_NAME, "summary": eco_summary})
    if kakao_summary: final_result['results'].append({"route_name": KAKAO_ROUTE_NAME, "summary": kakao_summary})
    
    if eco_summary and kakao_summary:
        time_diff = kakao_summary['total_time_min'] - eco_summary['total_time_min']
        co2_diff = kakao_summary['total_co2_g'] - eco_summary['total_co2_g']
        
        final_result['comparison'] = {
            "eco_route_is_shorter_time": time_diff > 0,
            "co2_saving_g": round(co2_diff, 3), 
            "co2_saving_pct": round(co2_diff / kakao_summary['total_co2_g'] * 100, 2)
        }
        print(f"✅ 비교 결과: CO2 절감량 {final_result['comparison']['co2_saving_g']:.3f}g (절감율 {final_result['comparison']['co2_saving_pct']}%)")


    if not final_result['results']:
        final_result = {"status": "failed", "message": "최적화 및 비교 경로를 모두 찾지 못했습니다.", "run_id": run_id}

    return final_result


# --------------------------------------------------------------------------
# 3. 헬퍼 함수: OR-Tools 결과 파싱 및 저장 (편도 계산 적용)
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
    
    # 편도 경로의 정확한 총 시간을 계산하기 위한 변수 (각 차량의 최종 시간)
    max_end_time_sec = 0.0 
    
    for vehicle_id_idx in range(num_vehicles):
        index = routing.Start(vehicle_id_idx)
        step_order = 1
        # 차량별 편도 경로 시간 누적
        vehicle_total_time_sec = 0.0
        
        while not routing.IsEnd(index):
            previous_index = index
            start_node_index = manager.IndexToNode(previous_index)
            
            # 1. Dimension 값 추출
            time_start_sec = solution.Value(time_dimension.CumulVar(previous_index))
            time_start_dt = base_datetime + dt.timedelta(seconds=time_start_sec)
            current_load_kg = solution.Value(capacity_dimension.CumulVar(previous_index))
            
            index = solution.Value(routing.NextVar(index))
            
            # ⭐ 핵심 수정: 편도 경로 구현: 다음 이동지가 Depot(End Node)라면 break
            if routing.IsEnd(index):
                print(f"   [One-Way Stop] Vehicle {vehicle_id_idx} reached final job. Skipping return arc to depot.")
                break # 마지막 Job -> Depot 복귀 아크는 계산하지 않고 루프 종료
            # -------------------------------------------------------------
            
            end_node_index = manager.IndexToNode(index)

            segments_raw = segment_data_map.get((start_node_index, end_node_index), [])
            step_actual_distance = distance_matrix[start_node_index][end_node_index]

            if segments_raw:
                current_vehicle_id = input_data['vehicles'][vehicle_id_idx]['vehicle_id']
                vehicle_info = vehicle_ef_data[current_vehicle_id]
                
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
            # 편도 경로 시간 누적
            vehicle_total_time_sec += step_time_sec_accurate

            assignment = {
                "run_id": run_id, "route_option_name": route_option_name, 
                "vehicle_id": current_vehicle_id, "step_order": step_order,
                "start_job_id": None if start_node_index == 0 else input_data['jobs'][start_node_index-1]['job_id'],
                "end_job_id": None if end_node_index == 0 else input_data['jobs'][end_node_index-1]['job_id'],
                "distance_km": step_actual_distance, "co2_g": round(step_co2, 5),
                "load_kg": float(current_load_kg), "time_min": round(step_time_sec_accurate / 60, 2),
                "avg_gradient_pct": default_slope, "congestion_factor": 1.0 
            }
            assignments_to_save.append(assignment)
            step_order += 1

        # OR-Tools의 End CumulVar 대신 수동 누적 시간 중 가장 긴 시간 사용
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
# 4. 헬퍼 함수: 카카오 경로 분석 (Benchmark)
# --------------------------------------------------------------------------

def analyze_kakao_route(run_id: str, input_data: Dict, vehicle_ef_data: Dict, route_option_name: str, kakao_route_info: Dict, default_slope: float, CONG_FACTORS, CO2_SETTINGS, WEATHER_PENALTY):
    """ 카카오 API 결과를 파싱하여 CO2를 계산하고 DB 저장용 구조체를 반환합니다. (편도 계산) """
    total_distance = kakao_route_info['total_distance_km']
    total_time_sec_base = kakao_route_info['total_time_sec']
    segments_raw = kakao_route_info['segments']
    
    start_time = input_data['run_date'] 
    # 차량 정보는 첫 번째 차량을 기준으로 사용 (Kakao Benchmark의 단일 경로 가정을 따름)
    vehicle_id = list(vehicle_ef_data.keys())[0]
    vehicle_info = vehicle_ef_data[vehicle_id]
    
    initial_load_kg = float(input_data['jobs'][0].get('demand_kg', 0)) 
    
    segments_for_co2 = [
        Segment(
            distance_km=s['distance_km'], link_id=s['link_id'], base_time_sec=s['base_time_sec'],
            slope_pct=default_slope, load_kg=initial_load_kg
        ) for s in segments_raw
    ]
    
    co2_result = co2_for_route(segments=segments_for_co2, v=vehicle_info, start_time=start_time,
                                 congestion_factors=CONG_FACTORS, settings=CO2_SETTINGS, 
                                 weather_penalty_value=WEATHER_PENALTY)
    
    total_co2_g_accurate = co2_result['co2_total_g']
    total_time_sec_accurate = co2_result['total_time_sec']

    summary_to_save = {
        "run_id": run_id, "route_option_name": route_option_name,
        "total_distance_km": round(total_distance, 2),
        "total_co2_g": round(total_co2_g_accurate, 3),
        "total_time_min": round(total_time_sec_accurate / 60, 2)
    }

    assignments_to_save = [{
        "run_id": run_id, "route_option_name": route_option_name,
        "vehicle_id": vehicle_id, "step_order": 1,
        "start_job_id": None, "end_job_id": input_data['jobs'][0]['job_id'],
        "distance_km": total_distance, "co2_g": round(total_co2_g_accurate, 5),
        "load_kg": initial_load_kg, "time_min": summary_to_save['total_time_min'],
        "avg_gradient_pct": default_slope, "congestion_factor": 1.0
    }]
    
    return summary_to_save, assignments_to_save, total_co2_g_accurate


# --- 5. 직접 실행 테스트를 위한 메인 블록 ---
if __name__ == '__main__':
    test_run_id = 'RUN_20251015_001'
    test_vehicle_ids = ['부산82가1234']
    try:
        final_result = run_optimization(test_run_id, test_vehicle_ids)
    except ConnectionError:
        print("\n💥 DB 연결 실패로 테스트를 건너뜁니다. config.py 설정을 확인하세요.")
        final_result = {"status": "error", "message": "DB Connection Failed."}
    except Exception as main_e:
        print(f"\n💥 메인 실행 중 심각한 오류 발생: {main_e}")
        final_result = {"status": "error", "message": f"메인 실행 오류: {main_e}"}

    print("\n--- 최종 최적화 결과 ---")
    try:
        print(json.dumps(final_result, indent=2, ensure_ascii=False, default=str))
    except Exception as json_e:
        print(f"💥 결과 출력(JSON) 중 오류 발생: {json_e}")
        print(final_result)
    print("-------------------------------")