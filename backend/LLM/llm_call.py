from flask import Blueprint, request, jsonify
import config
# db_handler.py 에서 DB 관련 함수들을 가져온다고 가정
from services.db_handler import get_db_connection, get_available_vehicle_ids
from .llm_db_save import save_run, save_job
from .lat_lon_kakao import enhance_parsed_data_with_geocoding
from .llm_sub_def import validate_sector_id, get_sector_coordinates, preprocess_with_sector_data
from optimizer.engine import run_optimization
import requests
import json
from datetime import datetime # datetime 임포트 추가

llm_bp = Blueprint('llm', __name__) #flask는 독립적이므로 app이 아닌 blueprint를 사용


def call_llm(prompt: str) -> str:
    # ... (이전 코드와 동일하게 유지하되, 오류 로깅 등 개선된 부분 유지) ...
    headers = {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"}
    payload = {"model": "google/gemini-2.0-flash-exp:free", "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(config.OPENROUTER_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        # 실제 응답 구조 확인 필요
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"API 호출 오류: {e}")
        raise # 오류 재발생
    except (KeyError, IndexError, TypeError) as e: # TypeError 추가
        print(f"API 응답 구조 오류: {e}, 응답: {response.text if 'response' in locals() else 'N/A'}")
        raise ValueError("API 응답 구조가 예상과 다릅니다.")


# --- API #1: 자연어 파싱 API ---
# (이전 제안과 동일하게 유지 - DB 저장 로직 없음)
@llm_bp.route('/api/parse-natural-language', methods=['POST'])
def parse_natural_language():
    """
    사용자의 자연어 입력을 받아 LLM으로 분석하여 JSON 형식으로 변환하여 반환합니다.
    """
    if request.method == 'OPTIONS':
        # flask-cors가 응답하므로 여기서 별도 응답 불필요
        # 또는 간단한 200 OK 응답을 보내도 무방 (flask-cors가 헤더 추가)
        return jsonify(success=True) # 예시 응답
    
    user_input = request.json.get('natural_input')
    if not user_input:
        return jsonify({"error": "natural_input is required"}), 400

    try:
        current_date = datetime.now()
        current_date_str = current_date.strftime('%Y-%m-%d')
        # --- 자연어를 JSON으로 변환 (LLM 호출) ---
        prompt = f"""
        당신은 물류 계획 전문가의 자연어 요청을 VRP(Vehicle Routing Problem)용 JSON 데이터로 변환하는 AI입니다.
        현재 날짜는 **{current_date_str}** 입니다. 이 정보를 바탕으로 "오늘", "내일", "모레" 등의 상대적인 날짜 표현을 정확한 "YYYY-MM-DD" 형식으로 변환해주세요.

        아래 사용자 요청에서 다음 구조에 맞춰 정보를 추출하여 JSON 형식으로만 응답해주세요. 다른 설명은 절대 추가하지 마세요.

        [JSON 구조]
        - "run_date": "YYYY-MM-DD" 형식의 날짜 문자열
        - "vehicles": ["차량ID1", "차량ID2", ...] 형식의 차량 ID 문자열 배열
        - "runs": [
            {{
                "run_date": "YYYY-MM-DD",
                "depot_address": "출발지 주소",  <!-- 출발지 주소 추가 -->
                "depot_lat": null,  <!-- null로 설정. 후처리에서 좌표가 채워질 수 있습니다 -->
                "depot_lon": null,  <!-- null로 설정. 후처리에서 좌표가 채워질 수 있습니다 -->
                "natural_language_input": "원본 사용자 요청문"
            }}
        ]
        - "jobs": [ 
            {{ 
            "sector_id": "도착지의 앞 지역명_NEW_PORT" <!-- 이 양식을 준수해주세요--> 
            "address": "정확한 주소 문자열",  <!-- 가능한 상세한 주소로 추출해주세요 -->
            "demand_kg": 숫자, 
            "lat": null,  <!-- null로 설정. 후처리에서 좌표가 채워질 수 있습니다 -->
            "lon": null   <!-- null로 설정. 후처리에서 좌표가 채워질 수 있습니다 -->
            "tw_start": "HH:MM",  <!-- 시간창 시작 (없으면 null)-->
            "tw_end": "HH:MM"    <!-- 시간창 종료 (없으면 null)-->
            }}, 
            ... 
        ]

        [추가 지침]
        1. 사용자 요청에서 **출발지**와 **도착지**를 구분해주세요:
            - 출발지: "~에서 출발", "~부터", "~에서" 등으로 표현된 곳
            - 도착지: "~에 배송", "~로", "~에" 등으로 표현된 곳
        2. 출발지는 "depot_address"에, 도착지는 "jobs"의 "address"에 넣어주세요.
        3. 주소(address)는 가능한 정확한 도로명 주소나 지번 주소로 추출해주세요.
        4. lat, lon 값은 항상 null로 설정해주세요.
        5. 날짜, 시간 형식과 JSON 구조를 정확히 지켜주세요.
        6. "depot_lat"과 "depot_lon"은 출발 지점 좌표, "lat"과 "lon"은 도착지점 좌표입니다.
        7. "natural_language_input"에는 사용자의 원본 요청문을 그대로 넣어주세요. (단 요구사항이 2개 이상일때 '\n'으로 줄바꿈을 한다면 각각 적어주세요.)
        8. 8. 시간창(tw_start, tw_end)은 사용자 요청에서 명시적으로 언급된 경우에만 추출해주세요. 예를 들어 "오전 10시부터 오후 2시까지" 등의 표현이 있으면 "HH:MM" 형식으로 넣어주세요. 시간이 명시되지 않았다면 null로 설정해주세요.
        <!--sector_id 예시) 도착지가 군산이라면 GUNSAN_NEW_PORT, 서울이라면 SEOUL_NEW_PORT, 부산이라면 BUSAN_NEW_PORT-->
        사용자 요청: "{user_input}"
        """
        llm_response_content = call_llm(prompt)

        # LLM 응답에서 JSON 추출 (개선된 방식 유지)
        json_match = None
        # ... (이전 코드의 JSON 추출 및 기본 유효성 검사 로직 유지) ...
        try:
            # 코드 블록(```json ... ```) 처리
            if '```json' in llm_response_content:
                json_str = llm_response_content.split('```json')[1].split('```')[0].strip()
            # 일반 JSON 객체 처리
            elif '{' in llm_response_content and '}' in llm_response_content:
                 json_str = llm_response_content[llm_response_content.find('{'):llm_response_content.rfind('}') + 1]
            else:
                 raise ValueError("LLM 응답에서 JSON 형식을 찾을 수 없습니다.")

            parsed_data = json.loads(json_str)
            if not all(k in parsed_data for k in ["run_date", "vehicles", "jobs"]):
                 raise ValueError("필수 키(run_date, vehicles, jobs)가 누락되었습니다.")

        except (json.JSONDecodeError, ValueError) as json_err:
             print(f"LLM 응답 JSON 파싱 오류: {json_err}, 원본 응답: {llm_response_content}")
             raise ValueError(f"LLM 응답을 JSON으로 파싱하는 데 실패했습니다: {json_err}")
        if not parsed_data.get('vehicles'):
            print("ℹ️ LLM이 차량 ID를 추출하지 못했습니다. DB에서 사용 가능한 모든 차량 ID를 조회합니다.")
            try:
                available_vehicles = get_available_vehicle_ids() # DB 조회
                if available_vehicles:
                    parsed_data['vehicles'] = available_vehicles
                    print(f"✅ 사용 가능한 차량 ID로 대체: {available_vehicles}")
                else:
                    # DB에도 차량이 없으면 (이러면 안되지만) 최소한 빈 리스트 보장
                    parsed_data['vehicles'] = [] 
                    print("⚠️ DB에서도 사용 가능한 차량을 찾을 수 없습니다.")
            except Exception as db_e:
                print(f"❌ 차량 ID 조회 중 DB 오류: {db_e}")
                parsed_data['vehicles'] = [] # 오류 시 빈 리스트
        parsed_data = preprocess_with_sector_data(parsed_data)
        
        parsed_data = enhance_parsed_data_with_geocoding(parsed_data)

        return jsonify(parsed_data), 200

    except ValueError as ve:
        return jsonify({"error": "LLM 응답 처리 실패", "details": str(ve)}), 500
    except requests.exceptions.RequestException as re:
        return jsonify({"error": "LLM API 호출 실패", "details": str(re)}), 502
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        return jsonify({"error": "내부 서버 오류 발생", "details": str(e)}), 500

# --- API #2: 계획 저장 및 LLM 분석 API ---
@llm_bp.route('/api/save-plan-and-analyze', methods=['POST'])
def save_plan_and_analyze():
    if request.method == 'OPTIONS':
        return jsonify(success=True)
    """
    파싱된 계획 데이터(JSON)를 받아 DB에 저장합니다.
    """
    plan_data = request.json
    if not plan_data:
        return jsonify({"error": "계획 데이터(JSON)가 필요합니다."}), 400
    
    conn = None
    run_id = None
    vehicles_list = []

    try:
        conn = get_db_connection() #DB 연결 가져오기 (db_handler.py 구현 필요)
        cursor = conn.cursor()

        # --- 1. RUNS 테이블에 기본 정보 저장 --- 
        run_date_str = plan_data.get('run_date')
        if not vehicles_list:
            raise ValueError("vehicles 데이터가 없습니다. (최적화 엔진 실행 불가)")
        
        try:
             # Oracle DATE 타입으로 변환 (python-oracledb 2.0 이상)
             # run_date_obj = datetime.strptime(run_date_str, '%Y-%m-%d')
             # 이전 버전 호환성 위해 TO_DATE 사용 예시
             pass # 아래 save_run 함수 내에서 처리 가정
        except (ValueError, TypeError):
            return jsonify({"error": "run_date 형식이 잘못되었습니다. (YYYY-MM-DD 필요)"}), 400

        all_run_ids = []
        runs_data = plan_data.get('runs', [])

        if not runs_data:
            return jsonify({"error": "runs 데이터가 없습니다."}), 400
        
        for i, run_item in enumerate(runs_data):
            run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{i}"

            run_date_str = run_item.get('run_date')
            if not run_date_str:
                return jsonify({"error": f"run_date가 없습니다. (run index: {i})"}), 400

            # RUNS 테이블 저장
            run_params = {
                "run_id": run_id,
                "run_date_str": run_date_str,
                "depot_lat": run_item.get('depot_lat'),
                "depot_lon": run_item.get('depot_lon'),
                "natural_language_input": run_item.get('natural_language_input'),
                "optimization_status": "ANALYZED"
            }
            save_run(cursor, run_params)

        # --- 2. JOBS 테이블에 작업 정보 저장 ---
        jobs_data = plan_data.get('jobs', [])
        for job in jobs_data:
            validated_sector_id = validate_sector_id(cursor, job.get('sector_id'))
            job_params = {
                "run_id": run_id,
                "sector_id": validated_sector_id,
                "address": job.get('resolved_address', job['address']),
                "lat": job.get('lat'),
                "lon": job.get('lon'),
                "demand_kg": job.get('demand_kg'),
                "tw_start": job.get('tw_start'), 
                "tw_end": job.get('tw_end')
            }
            save_job(cursor, job_params)

        conn.commit() # RUNS, JOBS 저장 완료
        # RUNS 테이블 상태 업데이트
        print(f"✅ 1/3: RUNS/JOBS 저장 완료 (run_id: {run_id})")
        # --- 5. [⭐ 추가] 3단계: LLM 경로 비교 분석 실행 ---
        # (이 함수도 내부적으로 DB에 연결하고 LLM_EXPLANATION을 UPDATE한 뒤 커밋합니다)
        print(f"🧠 3/3: LLM 경로 비교 분석 실행 (run_id: {run_id})")
        
        llm_explanation_text = generate_route_comparison_explanation(run_id)
        
        if not llm_explanation_text:
            raise Exception("최적화는 성공했으나 LLM 비교 분석 리포트 생성에 실패했습니다.")

        print(f"✅ 3/3: LLM 분석 완료. 모든 프로세스 종료. (run_id: {run_id})")

        # --- 6. [⭐ 수정] 최종 성공 응답 반환 ---
        return jsonify({
            "message": "계획 저장, 최적화 및 LLM 분석 완료", 
            "run_id": run_id,
            "llm_explanation": llm_explanation_text # 분석 결과도 함께 전달
        }), 200

    except Exception as e:
        if conn: conn.rollback()
        print(f"계획 저장/분석/최적화 통합 처리 중 오류: {e}")
        
        # [⭐ 추가] 만약 run_id가 생성된 상태에서 오류가 났다면, RUNS 상태를 'FAILED'로 업데이트 시도
        if run_id:
            try:
                if not conn or not conn.is_connected():
                    conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE runs SET optimization_status = 'FAILED' WHERE run_id = :run_id", {"run_id": run_id})
                conn.commit()
            except Exception as update_e:
                print(f"오류 상태 업데이트 중 추가 오류: {update_e}")

        return jsonify({"error": "전체 프로세스 중 내부 서버 오류 발생", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()




#-----------------------------------------------------------------------------------------------------
# --- API #3: 결과 조회 API ---
# (이전 제안과 거의 동일, 분석 결과만 가져오도록 명확화)
def generate_route_comparison_explanation(run_id: str):
    """
    같은 RUN_ID의 여러 경로 옵션을 비교 분석하여 LLM 설명을 생성하고 저장합니다.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. RUN_SUMMARY에서 같은 RUN_ID의 모든 경로 옵션 조회
        cursor.execute("""
            SELECT ROUTE_OPTION_NAME, TOTAL_DISTANCE_KM, TOTAL_CO2_G, TOTAL_TIME_MIN, SAVING_PCT
            FROM RUN_SUMMARY 
            WHERE RUN_ID = :run_id
            ORDER BY ROUTE_OPTION_NAME
        """, {'run_id': run_id})
        
        routes = cursor.fetchall()
        if not routes:
            print(f"⚠️ RUN_ID '{run_id}'에 대한 경로 데이터가 없습니다.")
            return None
            
        if len(routes) < 2:
            print(f"⚠️ RUN_ID '{run_id}'에 비교할 경로 옵션이 2개 이상 필요합니다.")
            return None
        
        # 2. 데이터를 딕셔너리 리스트로 변환
        columns = [col[0].lower() for col in cursor.description]
        route_data = [dict(zip(columns, route)) for route in routes]
        
        # 3. LLM 분석 프롬프트 생성
        analysis_prompt = create_route_comparison_prompt(route_data, run_id)
        
        # 4. LLM 호출하여 분석 결과 생성
        llm_explanation = call_llm(analysis_prompt)
        
        # 5. "OR-Tools Optimal" 경로의 LLM_EXPLANATION 업데이트
        cursor.execute("""
            UPDATE RUN_SUMMARY 
            SET LLM_EXPLANATION = :llm_explanation
            WHERE RUN_ID = :run_id AND ROUTE_OPTION_NAME = 'OR-Tools Optimal'
        """, {
            'llm_explanation': llm_explanation,
            'run_id': run_id
        })
        
        conn.commit()
        print(f"✅ 경로 비교 분석 완료 및 LLM_EXPLANATION 저장 (RUN_ID: {run_id})")
        return llm_explanation
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 경로 비교 분석 중 오류: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_route_comparison_prompt(route_data: list, run_id: str) -> str:
    """
    경로 비교 분석을 위한 LLM 프롬프트 생성
    """
    prompt = f"""
당신은 물류 경로 최적화 전문가입니다. 다음은 동일한 배송 요청(RUN_ID: {run_id})에 대한 여러 경로 옵션의 성능 비교 데이터입니다.

[경로 옵션 비교 데이터]
"""
    
    # 각 경로 옵션의 데이터 추가
    for i, route in enumerate(route_data, 1):
        co2_kg = route.get('total_co2_g', 0) / 1000 if route.get('total_co2_g') else 0
        prompt += f"""
{i}. {route.get('route_option_name', 'N/A')}:
   - 총 거리: {route.get('total_distance_km', 0):.2f} km
   - 총 CO2 배출량: {co2_kg:.2f} kg
   - 총 소요 시간: {route.get('total_time_min', 0):.2f} 분
   - 절감율: {route.get('saving_pct', 0):.2f}%
"""
    
    prompt += f"""
[분석 요청]
다음 내용을 중심으로 "OR-Tools Optimal" 경로가 다른 경로에 비해 왜 가장 우수한지 분석해주세요:

1. **거리 효율성**: 총 주행 거리 비교 및 분석
2. **환경적 영향**: CO2 배출량 차이와 환경적 이점
3. **시간 효율성**: 소요 시간 비교 및 운영 효율성
4. **종합 평가**: 세 가지 요소를 종합적으로 고려한 최적의 선택 이유
5. **비즈니스 관점**: 비용 절감, 고객 서비스, 환경 규제 준수 측면에서의 장점

[작성 지침]
- 데이터에 기반한 객관적인 분석을 제공해주세요
- 숫자와 수치를 구체적으로 언급하며 비교해주세요
- 전문적이지만 이해하기 쉽게 설명해주세요
- 한국어로 답변해주세요
- "OR-Tools Optimal" 경로의 우수성을 강조해주세요
- 분석 결과는 RUN_SUMMARY 테이블의 LLM_EXPLANATION 컬럼에 저장될 것입니다

분석 결과:
"""
    
    return prompt
#-----------------------------------------------------------------------------------------------------




def group_assignments_by_vehicle(assignments_data: list) -> list:
    """
    DB에서 조회된 assignments 딕셔너리 리스트를
    프론트엔드 Route 타입에 맞는 딕셔너리 리스트로 변환합니다.
    """
    routes_dict = {}
    job_details = {} # 간단한 Job 정보 캐싱 (필요시 DB 조회 추가)

    # 1. assignments 데이터를 순회하며 차량별로 그룹화하고 RouteStep 생성
    for assign in assignments_data:
        vehicle_id = assign.get('vehicle_id')
        if not vehicle_id:
            continue

        # 해당 차량의 route 딕셔너리가 없으면 새로 생성
        if vehicle_id not in routes_dict:
            routes_dict[vehicle_id] = {
                "vehicle_id": vehicle_id,
                "steps": [],
                "total_distance_km": 0.0,
                "total_co2_kg": 0.0,
                "total_time_min": 0,
                "polyline": [] # 폴리라인 정보는 현재 없으므로 빈 리스트
            }

        # RouteStep 객체 생성 (프론트엔드 타입 참고)
        # TODO: 실제 최적화 결과가 없으므로 시간 정보 등은 임시값 사용
        #       ASSIGNMENTS 테이블 구조에 따라 job_id -> sector_id 매핑 필요
        #       DB에서 JOBS 테이블을 조회하여 sector_id 가져오는 로직 추가 필요
        end_job_id = assign.get('end_job_id') # 예시로 end_job_id 사용
        sector_id = f"JOB_{end_job_id}" # 임시 Sector ID (실제로는 JOBS 테이블 조회 필요)

        step = {
            "sector_id": sector_id,
            "arrival_time": "미정", # 실제 최적화 결과 없으므로 임시값
            "departure_time": "미정", # 실제 최적화 결과 없으므로 임시값
            "distance_km": assign.get('distance_km', 0.0),
            "co2_kg": (assign.get('co2_g', 0.0) or 0.0) / 1000.0, # g -> kg 변환, None 방지
            # step_order: assign.get('step_order') # 필요시 추가
        }
        routes_dict[vehicle_id]["steps"].append(step)

        # 각 Route의 합계 업데이트
        routes_dict[vehicle_id]["total_distance_km"] += step["distance_km"] or 0.0
        routes_dict[vehicle_id]["total_co2_kg"] += step["co2_kg"] or 0.0
        routes_dict[vehicle_id]["total_time_min"] += assign.get('time_min', 0) or 0 # None 방지

    # 2. total 값들 소수점 정리 (선택 사항)
    for route in routes_dict.values():
        route["total_distance_km"] = round(route["total_distance_km"], 2)
        route["total_co2_kg"] = round(route["total_co2_kg"], 3)

    # 딕셔너리의 값들(Route 객체들)을 리스트로 변환하여 반환
    return list(routes_dict.values())

