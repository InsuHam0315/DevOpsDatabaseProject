from flask import Blueprint, request, jsonify
import config
# db_handler.py 에서 DB 관련 함수들을 가져온다고 가정
from services.db_handler import get_db_connection # 함수 이름 변경 및 추가
from LLM.llm_db_save import save_run, save_job
from LLM.lat_lon_kakao import enhance_parsed_data_with_geocoding
from LLM.llm_sub_def import preprocess_with_sector_data
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import json
from datetime import datetime # datetime 임포트 추가
from optimizer.engine import run_optimization

llm_bp = Blueprint('llm', __name__) #flask는 독립적이므로 app이 아닌 blueprint를 사용

genai.configure(api_key=config.GOOGLE_API_KEY)
def call_llm(prompt: str) -> str:

    model = genai.GenerativeModel('gemini-2.5-flash')

    retries = 3
    delay = 2 # 2초부터 시작
    for attempt in range(retries):
        try:
            # Google API 호출
            response = model.generate_content(prompt)
            
            # (중요) Google API는 응답 본문에 .text로 바로 접근
            if not response.candidates:
                 raise ValueError("API 응답에 유효한 'candidates'가 없습니다. (안전 문제로 차단되었을 수 있음)")
            return response.text

        except (google_exceptions.ResourceExhausted,  # 429 Too Many Requests
                google_exceptions.ServiceUnavailable, # 5xx 서버 오류
                google_exceptions.DeadlineExceeded) as e: # 타임아웃
            
            if attempt < retries - 1:
                print(f"⚠️ LLM API 오류 (시도 {attempt + 1}/{retries}): {e}. {delay}초 후 재시도...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"❌ LLM API 비-재시도 오류 (최대 재시도): {e}")
                raise # 최대 재시도 도달 시 즉시 실패
        
        except (KeyError, IndexError, TypeError, ValueError) as e:
            # 응답 파싱 오류 또는 안전 문제로 인한 차단 처리
            print(f"API 응답 구조 오류 또는 차단: {e}")
            try:
                # 차단 시 피드백이 있는지 확인
                print(f"    차단 피드백: {response.prompt_feedback}")
            except Exception:
                pass
            raise ValueError(f"API 응답 구조가 예상과 다르거나 콘텐츠가 차단되었습니다: {e}")
            
        except Exception as e:
            # 기타 예상치 못한 오류
            print(f"❌ LLM API 알 수 없는 오류: {e}")
            if attempt < retries - 1:
                 time.sleep(delay)
                 delay *= 2
            else:
                raise # 최대 재시도 도달
    raise Exception("LLM 호출 재시도 모두 실패")




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
                "vehicle_model" : "vehicles의 문자열 그대로 입력해주세요" <!-- 데이터가 전부 입력해주세요 -->

                - "jobs": [ 
                    {{ 
                    "sector_id": null,
                    "address": "정확한 주소 문자열",  <!-- 가능한 상세한 주소로 추출해주세요 -->
                    "demand_kg": 숫자, 
                    "lat": null,  <!-- null로 설정. 후처리에서 좌표가 채워질 수 있습니다 -->
                    "lon": null   <!-- null로 설정. 후처리에서 좌표가 채워질 수 있습니다 -->
                    "tw_start": "HH:MM",  <!-- 시간창 시작 (없으면 null)-->
                    "tw_end": "HH:MM"    <!-- 시간창 종료 (없으면 null)-->
                    }}, 
                    ... 
                ]
            }},
            ...
        ]
        [추가 지침]
        1.  사용자 요청이 "A에서 B로", "C에서 D, E로"와 같이 여러 개의 개별 운행을 포함할 수 있습니다.
        2.  각 출발지("A", "C")를 기준으로 "runs" 배열에 별도의 객체를 생성해야 합니다.
        3.  각 출발지에 속한 도착지들("B", "D", "E")을 해당 "runs" 객체 안의 "jobs" 배열에 정확히 그룹화해주세요.
        4.  "vehicles" 배열은 모든 운행에서 공통으로 사용될 수 있는 차량 목록입니다.
        5.  lat, lon 값은 항상 null로 설정해주세요.
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
            if not all(k in parsed_data for k in ["run_date", "vehicles", "runs"]):
                 raise ValueError("필수 키(run_date, vehicles, runs)가 누락되었습니다.")

        except (json.JSONDecodeError, ValueError) as json_err:
             print(f"LLM 응답 JSON 파싱 오류: {json_err}, 원본 응답: {llm_response_content}")
             raise ValueError(f"LLM 응답을 JSON으로 파싱하는 데 실패했습니다: {json_err}")

        parsed_data = preprocess_with_sector_data(parsed_data)
        parsed_data = enhance_parsed_data_with_geocoding(parsed_data)

        return jsonify(parsed_data), 200

    except ValueError as ve:
        return jsonify({"error": "LLM 응답 처리 실패", "details": str(ve)}), 500
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
    
    # ⭐ [수정] 모든 Run의 결과를 담을 리스트
    all_run_results = []
    
    # 공통 차량 ID (루프 밖에서 한 번만 가져옴)
    vehicle_ids = plan_data.get('vehicles', [])
    if not vehicle_ids:
        print("⚠️ JSON에 'vehicles' 정보가 없거나 비어있습니다. DB의 모든 차량을 대상으로 최적화를 시도합니다.")
        vehicle_ids = [] # 3단계에서 수정한 폴백 로직이 db_handler에 있으므로 [] 전달
    
    runs_data = plan_data.get('runs', [])
    if not runs_data:
        return jsonify({"error": "JSON에 'runs' 데이터가 없습니다."}), 400
    
    for i, run_item in enumerate(runs_data):
        conn = None
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{i}"
        
        try:
            # ⭐ [추가] 10-1. 좌표 유효성 검사 (DB 저장 전)
            if not run_item.get('depot_lat') or not run_item.get('depot_lon'):
                raise ValueError(f"출발지 '{run_item.get('depot_address')}'의 좌표를 찾을 수 없습니다. (Geocoding 실패)")

            jobs_data = run_item.get('jobs', [])
            if not jobs_data:
                raise ValueError(f"Jobs가 없습니다. (run index: {i})")

            # ⭐ [추가] 10-1. Job 좌표 유효성 검사
            for job in jobs_data:
                if not job.get('lat') or not job.get('lon'):
                    raise ValueError(f"도착지 '{job.get('address')}'의 좌표를 찾을 수 없습니다. (Geocoding 실패)")
                
            conn = get_db_connection()
            cursor = conn.cursor()

            # --- 1. RUNS 테이블에 저장 ---
            run_date_str = run_item.get('run_date')
            if not run_date_str:
                raise ValueError(f"run_date가 없습니다. (run index: {i})")

            run_params = {
                "run_id": run_id,
                "run_date_str": run_date_str,
                "depot_lat": run_item.get('depot_lat'),
                "depot_lon": run_item.get('depot_lon'),
                "natural_language_input": run_item.get('natural_language_input'),
                "optimization_status": "ANALYZED",
            }
            save_run(cursor, run_params)

            # --- 2. 해당 RUN에 속한 JOBS 저장 ---
            jobs_data = run_item.get('jobs', [])
            if not jobs_data:
                raise ValueError(f"Jobs가 없습니다. (run index: {i})")

            for job in jobs_data:
                job_params = {
                    "run_id": run_id, # ⬅️ 이 Run에 종속된 ID 사용
                    "run_date_str": run_date_str,
                    "sector_id": job.get('sector_id'),
                    "address": job.get('resolved_address', job['address']),
                    "lat": job.get('lat'),
                    "lon": job.get('lon'),
                    "demand_kg": job.get('demand_kg'),
                    "tw_start": job.get('tw_start'), 
                    "tw_end": job.get('tw_end')
                }
                save_job(cursor, job_params)

            conn.commit() # 1. 이 Run의 DB 저장 완료
            
            # --- 2. 최적화 엔진 실행 ---
            print(f"▶ (Run {i+1}/{len(runs_data)}) 1단계 (DB 저장) 완료. 2단계 (최적화 엔진) 호출 시작 (Run ID: {run_id})")
            optimization_result = run_optimization(run_id, vehicle_ids)
            
            if optimization_result.get("status") != "success":
                raise Exception(f"최적화 엔진 실행 실패: {optimization_result.get('message', '알 수 없는 오류')}")

            # --- 3. LLM 비교 분석 실행 ---
            print(f"▶ (Run {i+1}/{len(runs_data)}) 2단계 (최적화 엔진) 완료. 3단계 (LLM 분석) 호출 시작 (Run ID: {run_id})")
            llm_explanation_text = generate_route_comparison_explanation(run_id)

            # --- 4. 이 Run의 결과 저장 ---
            all_run_results.append({
                "status": "success",
                "run_id": run_id,
                "optimization_result": optimization_result,
                "llm_explanation": llm_explanation_text
            })

        except Exception as e:
            if conn: conn.rollback()
            print(f"❌ Run ID {run_id} 처리 중 오류 발생: {e}")
            all_run_results.append({
                "status": "failed",
                "run_id": run_id,
                "message": str(e)
            })
        finally:
            if conn:
                conn.close()

    # --- 최종 결과 반환 (모든 Run 처리 후) ---
    print("✅ 모든 Run 배치 처리 완료.")
    return jsonify({
        "message": f"총 {len(runs_data)}개의 Run 중 {len([r for r in all_run_results if r['status'] == 'success'])}개 성공",
        "batch_results": all_run_results
    }), 200
        

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
            WHERE RUN_ID = :run_id AND ROUTE_OPTION_NAME = 'Our Eco Optimal Route'
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
#-------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------
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
        
        # ⭐ [핵심 수정] .get()으로 가져온 값이 None일 경우를 대비해 0.0으로 폴백
        total_co2_g = route.get('total_co2_g') or 0.0
        total_dist = route.get('total_distance_km') or 0.0
        total_time = route.get('total_time_min') or 0.0
        saving_pct = route.get('saving_pct') or 0.0 # ⬅️ 이것이 오류의 원인

        co2_kg = total_co2_g / 1000.0 # 0.0 / 1000.0은 0.0이므로 안전
        
        prompt += f"""
{i}. {route.get('route_option_name', 'N/A')}:
   - 총 거리: {total_dist:.2f} km
   - 총 CO2 배출량: {co2_kg:.2f} kg
   - 총 소요 시간: {total_time:.2f} 분
   - 절감율: {saving_pct:.2f}%
"""
    
    prompt += f"""
[분석 요청]
다음 내용을 중심으로 "Our Eco Optimal Route" 경로가 다른 경로에 비해 왜 가장 우수한지 분석해주세요:

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
- "Our Eco Optimal Route" 경로의 우수성을 강조해주세요
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

