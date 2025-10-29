from flask import Blueprint, request, jsonify
import config
# db_handler.py 에서 DB 관련 함수들을 가져온다고 가정
from services.db_handler import get_db_connection # 함수 이름 변경 및 추가
from LLM.llm_db_save import save_run, save_job, save_llm_analysis_summary
from .lat_lon_kakao import enhance_parsed_data_with_geocoding
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

#-----------------------------------------------------------------------------------------------------
def get_sector_coordinates(sector_name: str) -> dict:
    """SECTOR 테이블에서 sector_name에 해당하는 좌표를 조회 - 디버깅 강화"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cleaned_name = sector_name.strip()
        print(f"🔍 SECTOR 테이블 조회: '{cleaned_name}'")
        
        # 1. 먼저 SECTOR 테이블에 어떤 데이터가 있는지 전체 조회
        cursor.execute("SELECT sector_name, lat, lon FROM SECTOR")
        all_sectors = cursor.fetchall()
        print(f"📋 SECTOR 테이블 전체 데이터: {all_sectors}")
        
        # 2. 정확한 매칭 시도
        cursor.execute("""
            SELECT lat, lon FROM SECTOR WHERE sector_name = :sector_name
        """, {'sector_name': cleaned_name})
        
        result = cursor.fetchone()
        if result:
            print(f"✅ SECTOR 테이블에서 찾음: '{cleaned_name}' -> ({result[0]}, {result[1]})")
            return {'lat': result[0], 'lon': result[1]}
        else:
            print(f"❌ SECTOR 테이블에서 찾지 못함: '{cleaned_name}'")
            
            # 3. 유사한 데이터가 있는지 확인
            cursor.execute("""
                SELECT sector_name, lat, lon FROM SECTOR 
                WHERE sector_name LIKE '%' || :partial_name || '%'
            """, {'partial_name': cleaned_name})
            
            similar_results = cursor.fetchall()
            if similar_results:
                print(f"🔍 유사한 SECTOR 데이터: {similar_results}")
            else:
                print(f"🔍 '{cleaned_name}'와 유사한 데이터도 없음")
                
            return None
    except Exception as e:
        print(f"SECTOR 테이블 조회 오류: {e}")
        return None
    finally:
        if conn:
            conn.close()

def preprocess_with_sector_data(parsed_data: dict) -> dict:
    """SECTOR 테이블을 참조하여 좌표를 미리 채움"""
    if not parsed_data.get('runs') or not parsed_data.get('jobs'):
        return parsed_data
    
    # 출발지(runs) 좌표 채우기
    for run in parsed_data.get('runs', []):
        depot_address = run.get('depot_address')
        if depot_address:
            # 🔥 주소 문자열 그대로 SECTOR 테이블에서 검색
            coords = get_sector_coordinates(depot_address)
            if coords:
                run['depot_lat'] = coords['lat']
                run['depot_lon'] = coords['lon']
                print(f"✅ SECTOR에서 출발지 좌표 채움: {depot_address}")
            else:
                print(f"ℹ️  SECTOR에 없는 출발지: {depot_address}")
    
    # 도착지(jobs) 좌표 채우기 - 주소 그대로 SECTOR 테이블에서 검색
    for job in parsed_data.get('jobs', []):
        address = job.get('address')
        if address:
            # 🔥 주소 문자열 그대로 SECTOR 테이블에서 검색
            coords = get_sector_coordinates(address)
            if coords:
                job['lat'] = coords['lat']
                job['lon'] = coords['lon']
                print(f"✅ SECTOR에서 도착지 좌표 채움: {address}")
            else:
                print(f"ℹ️  SECTOR에 없는 도착지: {address}")
    
    return parsed_data
#-----------------------------------------------------------------------------------------------------




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
    파싱된 계획 데이터(JSON)를 받아 DB에 저장하고,
    저장된 데이터를 기반으로 LLM 분석을 수행하여 그 결과를 DB에 저장한 후 run_id를 반환합니다.
    """
    plan_data = request.json
    if not plan_data:
        return jsonify({"error": "계획 데이터(JSON)가 필요합니다."}), 400
    
    conn = None
    try:
        conn = get_db_connection() #DB 연결 가져오기 (db_handler.py 구현 필요)
        cursor = conn.cursor()

        # --- 1. RUNS 테이블에 기본 정보 저장 --- 
        run_date_str = plan_data.get('run_date')
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
                "optimization_status": "ANALYZING"
            }
            save_run(cursor, run_params)
            all_run_ids.append(run_id)

        # --- 2. JOBS 테이블에 작업 정보 저장 ---
        jobs_data = plan_data.get('jobs', [])
        saved_job_ids = []
        for job in jobs_data:
            job_params = {
                "run_id": run_id,
                "sector_id": job.get('sector_id'),
                "address": job.get('resolved_address', job['address']),
                "lat": job.get('lat'),
                "lon": job.get('lon'),
                "demand_kg": job.get('demand_kg')
            }
            job_id = save_job(cursor, job_params) # db_handler.py에 구현 필요
            saved_job_ids.append(job_id)

        conn.commit() # RUNS, JOBS 저장 완료
        # RUNS 테이블 상태 업데이트
        cursor.execute("UPDATE runs SET optimization_status = 'ANALYZED' WHERE run_id = :run_id", {"run_id": run_id})

        conn.commit() # 분석 결과 저장 및 상태 업데이트 커밋

        return jsonify({"message": "계획 저장 및 LLM 분석 완료", "run_id": run_id}), 200
    except ValueError as ve: # 데이터 형식 오류 등
        if conn: conn.rollback()
        return jsonify({"error": "데이터 처리 오류", "details": str(ve)}), 400
    except Exception as e:
        if conn: conn.rollback()
        print(f"계획 저장/분석 중 오류: {e}")
        # import traceback
        # traceback.print_exc() # 필요시 스택 트레이스
        return jsonify({"error": "계획 저장/분석 중 내부 서버 오류 발생", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


# --- API #3: 결과 조회 API ---
# (이전 제안과 거의 동일, 분석 결과만 가져오도록 명확화)
@llm_bp.route('/api/get-results/<string:run_id>', methods=['GET'])
def get_results(run_id):
    """
    주어진 run_id에 해당하는 저장된 계획 정보와 LLM 분석 결과를 DB에서 조회하여 반환합니다.
    (실제 경로 데이터 대신 분석 결과만 반환)
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None: # 연결 실패 시 처리 (get_db_connection이 None 반환 시)
             raise ConnectionError("DB 연결 객체를 가져오지 못했습니다.")
        cursor = conn.cursor()

        # RUN_SUMMARY 조회 (LLM 설명 포함)
        cursor.execute("""
            SELECT total_distance_km, total_co2_g, total_time_min, saving_pct, llm_explanation
            FROM run_summary WHERE run_id = :run_id
        """, {"run_id": run_id})
        summary_row = cursor.fetchone()
        if not summary_row:
            return jsonify({"error": f"Run ID '{run_id}'에 대한 분석 정보를 찾을 수 없습니다."}), 404

        summary_cols = [col[0].lower() for col in cursor.description]
        summary_data = dict(zip(summary_cols, summary_row))
        llm_explanation_lob = summary_data.get('llm_explanation')
        llm_explanation_str = "" # 기본값 빈 문자열
        if llm_explanation_lob and hasattr(llm_explanation_lob, 'read'):
            # LOB 객체이면 .read() 메소드로 문자열 변환
            llm_explanation_str = llm_explanation_lob.read()
        elif isinstance(llm_explanation_lob, str):
            # 이미 문자열이면 그대로 사용 (LOB 객체가 아닐 경우 대비)
            llm_explanation_str = llm_explanation_lob
        # 필요하다면 RUNS, JOBS 테이블 정보도 추가 조회 가능
        cursor.execute("""
            SELECT vehicle_id, step_order, start_job_id, end_job_id, distance_km, co2_g, time_min
            FROM assignments
            WHERE run_id = :run_id
            ORDER BY vehicle_id, step_order
        """, {"run_id": run_id})
        assignments_rows = cursor.fetchall()
        assignments_cols = [col[0].lower() for col in cursor.description]
        assignments_data = [dict(zip(assignments_cols, row)) for row in assignments_rows]
        # 결과 조합 (KPI는 임시값 또는 0, 경로 정보는 없음)
        results = {
            "run_id": run_id,
            "kpis": {
                "total_distance_km": summary_data.get('total_distance_km', 0),
                "total_co2_kg": (summary_data.get('total_co2_g', 0) or 0) / 1000.0, # g -> kg, None 방지
                "total_time_min": summary_data.get('total_time_min', 0),
                "saving_percent": summary_data.get('saving_pct', 0)
            },
            # 👇 변환된 문자열 사용
            "llm_explanation": llm_explanation_str,
            # 👇 group_assignments_by_vehicle 함수 필요 (이전 답변 참고)
            "routes": group_assignments_by_vehicle(assignments_data)
        }

        # 👇 이제 results 딕셔너리에는 LOB 객체가 없으므로 jsonify 가능
        return jsonify(results), 200

    except ConnectionError as ce: # DB 연결 자체 실패 처리
         print(f"DB 연결 오류: {ce}")
         return jsonify({"error": "데이터베이스 연결 실패", "details": str(ce)}), 500
    except Exception as e:
        print(f"결과 조회 중 오류 (run_id: {run_id}): {e}")
        # import traceback # 상세 오류 확인 시 주석 해제
        # traceback.print_exc()
        return jsonify({"error": "결과 조회 중 내부 서버 오류 발생", "details": str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception as close_err:
                 print(f"DB 연결 종료 중 오류: {close_err}")

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
# # --- Flask 앱 실행 ---
# if __name__ == '__main__':
#     # config 파일에서 포트 가져오기 (없으면 5001 기본값)
#     port = getattr(config, 'FLASK_PORT', 5000)
#     app.run(debug=True, port=port)
