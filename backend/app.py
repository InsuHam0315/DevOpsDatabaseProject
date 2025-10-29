from flask import Flask, request, jsonify
from flask_cors import CORS
import config
import json
import oracledb
from datetime import datetime
from google import genai
import requests # LLM API 오류 처리를 위해 사용

# db_handler.py 에서 DB 관련 함수들을 가져옵니다.
from services.db_handler import test_db_connection, save_run, save_job, save_llm_analysis_summary, get_db_connection

app = Flask(__name__)
CORS(app)

# 설정값이 잘 로드되었는지 터미널에 출력해서 확인해봅니다.
# config.DB_USER 형태로 사용합니다.
print(f"DB User from config: {config.DB_USER}")
print(f"DB DSN from config: {config.DB_DSN}")


# --- 1. LLM 호출 함수 (Google Gemini로 수정) ---
def call_llm(prompt: str) -> str:
    """
    Google Gemini API를 호출하여 응답을 받아옵니다.
    """
    try:
        # GOOGLE_API_KEY를 사용하여 client 객체 생성
        client = genai.Client(api_key=config.GOOGLE_API_KEY)
        
        # 모델 호출 및 응답 텍스트 반환
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Google에서 공식적으로 지원하는 모델 사용
            contents=prompt
        )
        return response.text
    except genai.errors.APIError as e: # Gemini API 오류 처리... # Gemini API 오류 처리 (인증, 권한, API 키 문제 등)
        print(f"Gemini API 호출 오류: {e}")
        # 상위 함수에서 502로 처리할 수 있도록 requests.exceptions.RequestException으로 변환
        raise requests.exceptions.RequestException(f"Gemini API 호출 실패 (APIError): {e}")
    except Exception as e:
        print(f"예상치 못한 LLM 오류: {e}")
        raise ValueError(f"LLM 처리 중 오류 발생: {e}")


# --- API #1: 자연어 파싱 API ---
@app.route('/api/parse-natural-language', methods=['POST'])
def parse_natural_language():
    """
    사용자의 자연어 입력을 받아 LLM으로 분석하여 JSON 형식으로 변환하여 반환합니다.
    (이 함수는 DB에 저장하는 STEP 4와 연결되지 않으므로, 순수 LLM 호출만 수행합니다.)
    """
    if request.method == 'OPTIONS':
        return jsonify(success=True)
    
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
        아래 사용자 요청에서 다음 구조에 맞춰 정보를 추출하여 **JSON 형식으로만** 응답해주세요. 다른 설명은 절대 추가하지 마세요.
        - "run_date": "YYYY-MM-DD" 형식의 날짜 문자열
        - "vehicles": [ {{"type": "차량종류", "capacity": 숫자(톤), "count": 숫자(대) }} ] 형식의 차량 객체 배열 (예: 25톤 트럭 2대는 {{"type": "truck", "capacity": 25, "count": 2}})
        - "jobs": [ {{ "from": "출발지", "to": "도착지", "weight": 숫자(톤), "priority": 숫자(1부터) }}, ... ] 형식의 작업 객체 배열
        - lat, lon, tw_start, tw_end 값은 모르면 생성하지 마세요.
        - 우선순위(priority)에는 절대로 0이 들어갈 수 없습니다. 순서대로 1,2,3,4를 지정해주세요.
        사용자 요청: "{user_input}"
        """
        llm_response_content = call_llm(prompt) # 수정된 call_llm 함수 사용

        # LLM 응답에서 JSON 추출 (개선된 방식 유지)
        json_match = None
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


        return jsonify(parsed_data), 200

    except ValueError as ve: # 데이터 형식 오류 등 (call_llm 내부 오류 포함)
        return jsonify({"error": "LLM 응답 처리 실패", "details": str(ve)}), 500
    except requests.exceptions.RequestException as re: # API 호출 실패 (502 Bad Gateway)
        return jsonify({"error": "LLM API 호출 실패", "details": str(re)}), 502
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        return jsonify({"error": "내부 서버 오류 발생", "details": str(e)}), 500


# --- API #2: 계획 저장 및 LLM 분석 API ---
@app.route('/api/save-plan-and-analyze', methods=['POST'])
def save_plan_and_analyze():
    """
    파싱된 계획 데이터(JSON)를 받아 DB에 저장하고,
    저장된 데이터를 기반으로 LLM 분석을 수행하여 그 결과를 DB에 저장한 후 run_id를 반환합니다.
    """
    if request.method == 'OPTIONS':
        return jsonify(success=True)
        
    plan_data = request.json
    if not plan_data:
        return jsonify({"error": "계획 데이터(JSON)가 필요합니다."}), 400

    conn = None
    try:
        # app.py (save_plan_and_analyze 함수 내부)
        # conn = test_db_connection() ⬅️ (X) 이 줄을 삭제하고
        conn = get_db_connection()    # ⬅️ (O) 이 줄로 변경
        cursor = conn.cursor()
        # ... (이하 동일) ...

        # --- 1. RUNS 테이블에 기본 정보 저장 ---
        run_date_str = plan_data.get('run_date')
        if not run_date_str:
             return jsonify({"error": "run_date가 누락되었습니다."}), 400

        # run_id 생성 (DB 시퀀스 또는 Python UUID 등 사용 권장)
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}" # 임시 ID

        run_params = {
            "run_id": run_id,
            "run_date_str": run_date_str, 
            "depot_lat": plan_data.get('depot_lat', 35.940000),
            "depot_lon": plan_data.get('depot_lon', 126.680000),
            "natural_language_input": plan_data.get('natural_input', None), 
            "optimization_status": "ANALYZING" # 상태 변경: 분석 중
        }
        # 👇 db_handler.py에 구현되어 있어야 합니다.
        save_run(cursor, run_params) 

        # --- 2. JOBS 테이블에 작업 정보 저장 ---
        jobs_data = plan_data.get('jobs', [])
        saved_job_ids = []
        for job in jobs_data:
            job_params = {
                "run_id": run_id,
                # 'from'과 'to'를 주소로 사용한다고 가정
                "sector_id": f"{job.get('from')}_{job.get('to')}", # 임시 섹터 ID
                "address": f"{job.get('from')}에서 {job.get('to')}", 
                "latitude": job.get('lat') if job.get('lat') is not None else 0,
                "longitude": job.get('lon') if job.get('lon') is not None else 0,
                "demand_kg": job.get('weight'), # weight를 demand_kg으로 사용
                "tw_start_str": job.get('tw_start', '00:00'),
                "tw_end_str": job.get('tw_end', '23:59'),
                "priority": job.get('priority', 1),
                "run_date_str": run_date_str
            }
            # 👇 db_handler.py에 구현되어 있어야 합니다.
            job_id = save_job(cursor, job_params) 
            saved_job_ids.append(job_id)

        conn.commit() # RUNS, JOBS 저장 완료

        # --- 3. LLM 분석/설명 생성 ---
        vehicle_count = sum(v.get('count', 0) for v in plan_data.get('vehicles', []))
        job_count = len(jobs_data)
        total_demand = sum(job.get('weight', 0) for job in jobs_data) # weight 기준

        llm_prompt_for_analysis = f"""
        당신은 물류 계획 분석 전문가 AI입니다. 아래 제공된 계획 데이터를 바탕으로, 이 계획의 특징과 예상되는 효율성, 그리고 친환경 측면에 대해 전문적인 분석 보고서 형식으로 작성해주세요.

        [계획 기본 정보 (ID: {run_id})]
        - 실행 날짜: {run_date_str}
        - 사용 예정 차량 수: {vehicle_count} 대
        - 총 작업 수: {job_count} 건
        - 총 배송 물량: {total_demand} 톤 (입력 데이터 기준)

        분석 내용에는 다음 사항을 포함해주세요:
        - 분석 내용은 아래 세 가지 요구사항만 넣습니다 그 외에는 아무것도 넣지 않습니다.
        1. 사용 차량(종류, 대수)과 총 물량 간의 적절성 예측 (가능하다면).
        2. 시간 제약 조건(TW)이 경로 계획에 미칠 영향 예측.
        3. 친환경 차량(EV, 하이브리드 등) 사용 여부 및 예상되는 환경적 이점 언급.
        - 모든 설명은 간결하고 짧게 가능하면 두 줄 이내로 설명해주세요.
        """
        try:
            llm_explanation = call_llm(llm_prompt_for_analysis)
        except Exception as llm_err:
            print(f"LLM 분석 생성 실패: {llm_err}")
            llm_explanation = "LLM 분석을 생성하는 데 실패했습니다."

        # --- 4. LLM 분석 결과 저장 ---
        summary_params = {
            "run_id": run_id,
            "llm_explanation": llm_explanation,
            "total_distance_km": 0,
            "total_co2_g": 0,
            "total_time_min": 0,
            "saving_pct": 0
        }
        # 👇 db_handler.py에 구현되어 있어야 합니다.
        save_llm_analysis_summary(cursor, summary_params)

        # RUNS 테이블 상태 업데이트
        cursor.execute("UPDATE runs SET optimization_status = 'ANALYZED' WHERE run_id = :run_id", {"run_id": run_id})

        conn.commit() # 분석 결과 저장 및 상태 업데이트 커밋

        return jsonify({"message": "계획 저장 및 LLM 분석 완료", "run_id": run_id}), 200

    except oracledb.Error as db_err:
        if conn: conn.rollback()
        print(f"DB 오류 발생: {db_err}")
        return jsonify({"error": "데이터베이스 작업 오류", "details": str(db_err)}), 500
    except ValueError as ve:
        if conn: conn.rollback()
        return jsonify({"error": "데이터 처리 오류", "details": str(ve)}), 400
    except Exception as e:
        if conn: conn.rollback()
        print(f"계획 저장/분석 중 오류: {e}")
        return jsonify({"error": "계획 저장/분석 중 내부 서버 오류 발생", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


# --- API #3: 결과 조회 API ---
@app.route('/api/get-results/<string:run_id>', methods=['GET'])
def get_results(run_id):
    """
    주어진 run_id에 해당하는 저장된 계획 정보와 LLM 분석 결과를 DB에서 조회하여 반환합니다.
    (실제 경로 데이터 대신 분석 결과만 반환)
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
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
        
        # LOB 객체 처리
        llm_explanation_lob = summary_data.get('llm_explanation')
        llm_explanation_str = "" 
        if llm_explanation_lob and hasattr(llm_explanation_lob, 'read'):
            llm_explanation_str = llm_explanation_lob.read()
        elif isinstance(llm_explanation_lob, str):
            llm_explanation_str = llm_explanation_lob
            
        # ASSIGNMENTS 조회 (빈 경로 데이터 처리)
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
                "total_distance_km": summary_data.get('total_distance_km', 0) or 0,
                "total_co2_kg": (summary_data.get('total_co2_g', 0) or 0) / 1000.0,
                "total_time_min": summary_data.get('total_time_min', 0) or 0,
                "saving_percent": summary_data.get('saving_pct', 0) or 0
            },
            "llm_explanation": llm_explanation_str,
            "routes": group_assignments_by_vehicle(assignments_data)
        }

        return jsonify(results), 200

    except ConnectionError as ce: 
        print(f"DB 연결 오류: {ce}")
        return jsonify({"error": "데이터베이스 연결 실패", "details": str(ce)}), 500
    except Exception as e:
        print(f"결과 조회 중 오류 (run_id: {run_id}): {e}")
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
    (실제 경로 최적화가 없으므로 임시 로직을 포함합니다.)
    """
    routes_dict = {}

    # assignments 데이터를 순회하며 차량별로 그룹화하고 RouteStep 생성
    for assign in assignments_data:
        vehicle_id = assign.get('vehicle_id')
        if not vehicle_id:
            continue

        if vehicle_id not in routes_dict:
            routes_dict[vehicle_id] = {
                "vehicle_id": vehicle_id,
                "steps": [],
                "total_distance_km": 0.0,
                "total_co2_kg": 0.0,
                "total_time_min": 0,
                "polyline": []
            }

        # RouteStep 객체 생성
        step = {
            "sector_id": assign.get('end_job_id'), # 임시로 end_job_id 사용
            "arrival_time": "09:00", # 임시값
            "departure_time": "10:00", # 임시값
            "distance_km": assign.get('distance_km', 0.0) or 0.0,
            "co2_kg": (assign.get('co2_g', 0.0) or 0.0) / 1000.0,
        }
        routes_dict[vehicle_id]["steps"].append(step)

        # 각 Route의 합계 업데이트
        routes_dict[vehicle_id]["total_distance_km"] += step["distance_km"] 
        routes_dict[vehicle_id]["total_co2_kg"] += step["co2_kg"] 
        routes_dict[vehicle_id]["total_time_min"] += assign.get('time_min', 0) or 0 

    # total 값들 소수점 정리
    for route in routes_dict.values():
        route["total_distance_km"] = round(route["total_distance_km"], 2)
        route["total_co2_kg"] = round(route["total_co2_kg"], 3)

    return list(routes_dict.values())


# --- Flask 앱 실행 ---
if __name__ == '__main__':
    # config 파일에서 포트 가져오기 (없으면 5000 기본값)
    # config.py에 FLASK_PORT 설정이 없다면 5000을 사용합니다.
    port = getattr(config, 'FLASK_PORT', 5000)

    app.run(debug=True, port=port)
