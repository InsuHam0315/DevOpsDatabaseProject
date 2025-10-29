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


# --- API #4: 차량 관리 API ---
@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    """모든 차량 목록을 조회합니다."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # VEHICLES와 EMISSION_FACTORS를 JOIN하여 프론트엔드 형식에 맞게 변환
        cursor.execute("""
            SELECT 
                v.VEHICLE_ID as id,
                v.VEHICLE_TYPE || '_' || v.CAPACITY_KG/1000 || 't' as type,
                v.CAPACITY_KG as capacity_kg,
                ef.FUEL_TYPE as fuel,
                ef.CO2_GPKM as ef_gpkm,
                ef.IDLE_GPS as idle_gps
            FROM VEHICLES v
            JOIN EMISSION_FACTORS ef ON v.FACTOR_ID = ef.FACTOR_ID
            ORDER BY v.VEHICLE_ID
        """)
        
        rows = cursor.fetchall()
        cols = [col[0].lower() for col in cursor.description]
        vehicles = [dict(zip(cols, row)) for row in rows]
        
        return jsonify(vehicles), 200
    except Exception as e:
        print(f"차량 목록 조회 오류: {e}")
        return jsonify({"error": "차량 목록 조회 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/vehicles', methods=['POST'])
def create_vehicle():
    """새 차량을 등록합니다."""
    conn = None
    try:
        data = request.json
        if not data or not all(k in data for k in ['id', 'type', 'capacity_kg', 'fuel', 'ef_gpkm', 'idle_gps']):
            return jsonify({"error": "필수 필드가 누락되었습니다."}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # EMISSION_FACTORS에 먼저 삽입 또는 조회
        cursor.execute("""
            SELECT FACTOR_ID FROM EMISSION_FACTORS 
            WHERE LOWER(VEHICLE_TYPE) = LOWER(:vtype) 
            AND LOWER(FUEL_TYPE) = LOWER(:fuel)
            FETCH FIRST 1 ROWS ONLY
        """, {"vtype": data['type'], "fuel": data['fuel']})
        
        factor_row = cursor.fetchone()
        if factor_row:
            factor_id = factor_row[0]
            # 기존 배출계수 업데이트
            cursor.execute("""
                UPDATE EMISSION_FACTORS 
                SET CO2_GPKM = :ef_gpkm, IDLE_GPS = :idle_gps
                WHERE FACTOR_ID = :factor_id
            """, {"ef_gpkm": data['ef_gpkm'], "idle_gps": data['idle_gps'], "factor_id": factor_id})
        else:
            # 새로운 배출계수 생성
            factor_id_var = cursor.var(oracledb.NUMBER)
            cursor.execute("""
                INSERT INTO EMISSION_FACTORS (FACTOR_ID, VEHICLE_TYPE, FUEL_TYPE, CO2_GPKM, IDLE_GPS)
                VALUES (EMISSION_FACTORS_SEQ.NEXTVAL, :vtype, :fuel, :ef_gpkm, :idle_gps)
                RETURNING FACTOR_ID INTO :factor_id
            """, {"vtype": data['type'], "fuel": data['fuel'], 
                  "ef_gpkm": data['ef_gpkm'], "idle_gps": data['idle_gps'],
                  "factor_id": factor_id_var})
            factor_id = factor_id_var.getvalue()[0]
        
        # VEHICLES에 삽입
        cursor.execute("""
            INSERT INTO VEHICLES (VEHICLE_ID, FACTOR_ID, CAPACITY_KG, VEHICLE_TYPE)
            VALUES (:vehicle_id, :factor_id, :capacity_kg, :vehicle_type)
        """, {"vehicle_id": data['id'], "factor_id": factor_id, 
              "capacity_kg": data['capacity_kg'], "vehicle_type": data['type']})
        
        conn.commit()
        return jsonify({"message": "차량이 성공적으로 등록되었습니다.", "id": data['id']}), 201
        
    except oracledb.Error as db_err:
        if conn: conn.rollback()
        return jsonify({"error": "데이터베이스 오류", "details": str(db_err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"차량 등록 오류: {e}")
        return jsonify({"error": "차량 등록 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/vehicles/<string:vehicle_id>', methods=['PUT'])
def update_vehicle(vehicle_id):
    """차량 정보를 수정합니다."""
    conn = None
    try:
        data = request.json
        if not data:
            return jsonify({"error": "수정할 데이터가 없습니다."}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 차량 존재 확인
        cursor.execute("SELECT FACTOR_ID FROM VEHICLES WHERE VEHICLE_ID = :vehicle_id", 
                      {"vehicle_id": vehicle_id})
        vehicle_row = cursor.fetchone()
        if not vehicle_row:
            return jsonify({"error": "차량을 찾을 수 없습니다."}), 404
        
        factor_id = vehicle_row[0]
        
        # 배출계수 업데이트
        if 'ef_gpkm' in data or 'idle_gps' in data or 'fuel' in data:
            cursor.execute("""
                UPDATE EMISSION_FACTORS 
                SET CO2_GPKM = COALESCE(:ef_gpkm, CO2_GPKM),
                    IDLE_GPS = COALESCE(:idle_gps, IDLE_GPS),
                    FUEL_TYPE = COALESCE(:fuel, FUEL_TYPE)
                WHERE FACTOR_ID = :factor_id
            """, {"ef_gpkm": data.get('ef_gpkm'), "idle_gps": data.get('idle_gps'),
                  "fuel": data.get('fuel'), "factor_id": factor_id})
        
        # 차량 정보 업데이트
        cursor.execute("""
            UPDATE VEHICLES 
            SET CAPACITY_KG = COALESCE(:capacity_kg, CAPACITY_KG),
                VEHICLE_TYPE = COALESCE(:vehicle_type, VEHICLE_TYPE)
            WHERE VEHICLE_ID = :vehicle_id
        """, {"capacity_kg": data.get('capacity_kg'), 
              "vehicle_type": data.get('type'), "vehicle_id": vehicle_id})
        
        conn.commit()
        return jsonify({"message": "차량 정보가 수정되었습니다."}), 200
        
    except oracledb.Error as db_err:
        if conn: conn.rollback()
        return jsonify({"error": "데이터베이스 오류", "details": str(db_err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"차량 수정 오류: {e}")
        return jsonify({"error": "차량 수정 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/vehicles/<string:vehicle_id>', methods=['DELETE'])
def delete_vehicle(vehicle_id):
    """차량을 삭제합니다."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 차량 존재 확인
        cursor.execute("SELECT FACTOR_ID FROM VEHICLES WHERE VEHICLE_ID = :vehicle_id", 
                      {"vehicle_id": vehicle_id})
        vehicle_row = cursor.fetchone()
        if not vehicle_row:
            return jsonify({"error": "차량을 찾을 수 없습니다."}), 404
        
        # 차량 삭제 (외래키 참조 제약조건에 따라 순서 중요)
        cursor.execute("DELETE FROM VEHICLES WHERE VEHICLE_ID = :vehicle_id", 
                      {"vehicle_id": vehicle_id})
        
        conn.commit()
        return jsonify({"message": "차량이 삭제되었습니다."}), 200
        
    except oracledb.Error as db_err:
        if conn: conn.rollback()
        return jsonify({"error": "데이터베이스 오류", "details": str(db_err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"차량 삭제 오류: {e}")
        return jsonify({"error": "차량 삭제 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


# --- API #5: 섹터 관리 API ---
@app.route('/api/sectors', methods=['GET'])
def get_sectors():
    """모든 섹터 목록을 조회합니다."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # SECTORS 테이블이 있다고 가정 (없다면 JOBS에서 중복 제거)
        try:
            cursor.execute("""
                SELECT 
                    SECTOR_ID as id,
                    SECTOR_NAME as name,
                    LATITUDE as lat,
                    LONGITUDE as lon,
                    TO_CHAR(TW_START, 'HH24:MI') as tw_start,
                    TO_CHAR(TW_END, 'HH24:MI') as tw_end,
                    PRIORITY as priority
                FROM SECTORS
                ORDER BY SECTOR_ID
            """)
        except:
            # SECTORS 테이블이 없으면 JOBS에서 추출
            cursor.execute("""
                SELECT DISTINCT
                    SECTOR_ID as id,
                    SECTOR_ID as name,
                    LATITUDE as lat,
                    LONGITUDE as lon,
                    '09:00' as tw_start,
                    '17:00' as tw_end,
                    2 as priority
                FROM JOBS
                WHERE SECTOR_ID IS NOT NULL
                ORDER BY SECTOR_ID
            """)
        
        rows = cursor.fetchall()
        if not rows:
            return jsonify([]), 200
        
        cols = [col[0].lower() for col in cursor.description]
        sectors = [dict(zip(cols, row)) for row in rows]
        
        return jsonify(sectors), 200
    except Exception as e:
        print(f"섹터 목록 조회 오류: {e}")
        return jsonify({"error": "섹터 목록 조회 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sectors', methods=['POST'])
def create_sector():
    """새 섹터를 등록합니다."""
    conn = None
    try:
        data = request.json
        if not data or not all(k in data for k in ['id', 'name', 'lat', 'lon']):
            return jsonify({"error": "필수 필드가 누락되었습니다."}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # SECTORS 테이블이 있다고 가정
        try:
            cursor.execute("""
                INSERT INTO SECTORS (SECTOR_ID, SECTOR_NAME, LATITUDE, LONGITUDE, 
                                   TW_START, TW_END, PRIORITY)
                VALUES (:id, :name, :lat, :lon,
                        TO_TIMESTAMP('2000-01-01 ' || :tw_start, 'YYYY-MM-DD HH24:MI'),
                        TO_TIMESTAMP('2000-01-01 ' || :tw_end, 'YYYY-MM-DD HH24:MI'),
                        :priority)
            """, {
                "id": data['id'],
                "name": data['name'],
                "lat": data['lat'],
                "lon": data['lon'],
                "tw_start": data.get('tw_start', '09:00'),
                "tw_end": data.get('tw_end', '17:00'),
                "priority": data.get('priority', 2)
            })
        except:
            # SECTORS 테이블이 없으면 JOBS에 더미 작업 삽입 (임시 방법)
            return jsonify({"error": "SECTORS 테이블이 존재하지 않습니다. 먼저 테이블을 생성해주세요."}), 500
        
        conn.commit()
        return jsonify({"message": "섹터가 성공적으로 등록되었습니다.", "id": data['id']}), 201
        
    except oracledb.Error as db_err:
        if conn: conn.rollback()
        return jsonify({"error": "데이터베이스 오류", "details": str(db_err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"섹터 등록 오류: {e}")
        return jsonify({"error": "섹터 등록 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sectors/<string:sector_id>', methods=['PUT'])
def update_sector(sector_id):
    """섹터 정보를 수정합니다."""
    conn = None
    try:
        data = request.json
        if not data:
            return jsonify({"error": "수정할 데이터가 없습니다."}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE SECTORS 
                SET SECTOR_NAME = COALESCE(:name, SECTOR_NAME),
                    LATITUDE = COALESCE(:lat, LATITUDE),
                    LONGITUDE = COALESCE(:lon, LONGITUDE),
                    TW_START = CASE WHEN :tw_start IS NOT NULL 
                                   THEN TO_TIMESTAMP('2000-01-01 ' || :tw_start, 'YYYY-MM-DD HH24:MI')
                                   ELSE TW_START END,
                    TW_END = CASE WHEN :tw_end IS NOT NULL 
                                 THEN TO_TIMESTAMP('2000-01-01 ' || :tw_end, 'YYYY-MM-DD HH24:MI')
                                 ELSE TW_END END,
                    PRIORITY = COALESCE(:priority, PRIORITY)
                WHERE SECTOR_ID = :sector_id
            """, {
                "name": data.get('name'),
                "lat": data.get('lat'),
                "lon": data.get('lon'),
                "tw_start": data.get('tw_start'),
                "tw_end": data.get('tw_end'),
                "priority": data.get('priority'),
                "sector_id": sector_id
            })
        except:
            return jsonify({"error": "SECTORS 테이블이 존재하지 않습니다."}), 500
        
        if cursor.rowcount == 0:
            return jsonify({"error": "섹터를 찾을 수 없습니다."}), 404
        
        conn.commit()
        return jsonify({"message": "섹터 정보가 수정되었습니다."}), 200
        
    except oracledb.Error as db_err:
        if conn: conn.rollback()
        return jsonify({"error": "데이터베이스 오류", "details": str(db_err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"섹터 수정 오류: {e}")
        return jsonify({"error": "섹터 수정 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sectors/<string:sector_id>', methods=['DELETE'])
def delete_sector(sector_id):
    """섹터를 삭제합니다."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM SECTORS WHERE SECTOR_ID = :sector_id", 
                          {"sector_id": sector_id})
        except:
            return jsonify({"error": "SECTORS 테이블이 존재하지 않습니다."}), 500
        
        if cursor.rowcount == 0:
            return jsonify({"error": "섹터를 찾을 수 없습니다."}), 404
        
        conn.commit()
        return jsonify({"message": "섹터가 삭제되었습니다."}), 200
        
    except oracledb.Error as db_err:
        if conn: conn.rollback()
        return jsonify({"error": "데이터베이스 오류", "details": str(db_err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"섹터 삭제 오류: {e}")
        return jsonify({"error": "섹터 삭제 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


# --- API #6: 작업 관리 API ---
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """모든 작업 목록을 조회합니다."""
    conn = None
    try:
        date = request.args.get('date')
        sector_id = request.args.get('sector_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT 
                JOB_ID,
                RUN_ID,
                SECTOR_ID as sector_id,
                TO_CHAR(TO_DATE(TO_CHAR(TW_START, 'YYYY-MM-DD'), 'YYYY-MM-DD'), 'YYYY-MM-DD') as date,
                DEMAND_KG as demand_kg,
                TO_CHAR(TW_START, 'HH24:MI') as tw_start,
                TO_CHAR(TW_END, 'HH24:MI') as tw_end,
                PRIORITY as priority,
                LATITUDE as lat,
                LONGITUDE as lon
            FROM JOBS
            WHERE 1=1
        """
        params = {}
        
        if date:
            sql += " AND TRUNC(TW_START) = TO_DATE(:date, 'YYYY-MM-DD')"
            params['date'] = date
        
        if sector_id:
            sql += " AND SECTOR_ID = :sector_id"
            params['sector_id'] = sector_id
        
        sql += " ORDER BY JOB_ID"
        
        cursor.execute(sql, params)
        
        rows = cursor.fetchall()
        cols = [col[0].lower() for col in cursor.description]
        jobs = [dict(zip(cols, row)) for row in rows]
        
        return jsonify(jobs), 200
    except Exception as e:
        print(f"작업 목록 조회 오류: {e}")
        return jsonify({"error": "작업 목록 조회 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/jobs', methods=['POST'])
def create_job():
    """새 작업을 등록합니다."""
    conn = None
    try:
        data = request.json
        if not data or not all(k in data for k in ['sector_id', 'date', 'demand_kg']):
            return jsonify({"error": "필수 필드가 누락되었습니다."}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # RUN_ID 생성 (임시로 더미 값 사용)
        run_id = data.get('run_id', f"TEMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        cursor.execute("""
            INSERT INTO JOBS (
                RUN_ID, SECTOR_ID, ADDRESS, LATITUDE, LONGITUDE, 
                DEMAND_KG, TW_START, TW_END, PRIORITY
            ) VALUES (
                :run_id, :sector_id, 
                COALESCE(:address, :sector_id),
                :lat, :lon,
                :demand_kg,
                TO_TIMESTAMP(:date || ' ' || :tw_start, 'YYYY-MM-DD HH24:MI'),
                TO_TIMESTAMP(:date || ' ' || :tw_end, 'YYYY-MM-DD HH24:MI'),
                :priority
            )
            RETURNING JOB_ID INTO :job_id
        """, {
            "run_id": run_id,
            "sector_id": data['sector_id'],
            "address": data.get('address', data['sector_id']),
            "lat": data.get('lat', 0),
            "lon": data.get('lon', 0),
            "demand_kg": data['demand_kg'],
            "date": data['date'],
            "tw_start": data.get('tw_start', '09:00'),
            "tw_end": data.get('tw_end', '17:00'),
            "priority": data.get('priority', 2),
            "job_id": cursor.var(oracledb.NUMBER)
        })
        
        job_id_val = cursor.var(oracledb.NUMBER).getvalue()
        # JOB_ID는 트리거로 자동 생성되므로 조회
        cursor.execute("""
            SELECT JOB_ID FROM JOBS 
            WHERE RUN_ID = :run_id AND SECTOR_ID = :sector_id
            ORDER BY JOB_ID DESC FETCH FIRST 1 ROWS ONLY
        """, {"run_id": run_id, "sector_id": data['sector_id']})
        job_row = cursor.fetchone()
        job_id_val = job_row[0] if job_row else None
        
        conn.commit()
        return jsonify({"message": "작업이 성공적으로 등록되었습니다.", "job_id": job_id_val}), 201
        
    except oracledb.Error as db_err:
        if conn: conn.rollback()
        return jsonify({"error": "데이터베이스 오류", "details": str(db_err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"작업 등록 오류: {e}")
        return jsonify({"error": "작업 등록 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    """작업 정보를 수정합니다."""
    conn = None
    try:
        data = request.json
        if not data:
            return jsonify({"error": "수정할 데이터가 없습니다."}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 작업 존재 확인
        cursor.execute("SELECT RUN_ID, SECTOR_ID FROM JOBS WHERE JOB_ID = :job_id", 
                      {"job_id": job_id})
        job_row = cursor.fetchone()
        if not job_row:
            return jsonify({"error": "작업을 찾을 수 없습니다."}), 404
        
        run_id, sector_id_orig = job_row
        
        # 날짜 가져오기
        date = data.get('date')
        if not date:
            cursor.execute("SELECT TO_CHAR(TW_START, 'YYYY-MM-DD') FROM JOBS WHERE JOB_ID = :job_id",
                          {"job_id": job_id})
            date_row = cursor.fetchone()
            date = date_row[0] if date_row else datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("""
            UPDATE JOBS 
            SET SECTOR_ID = COALESCE(:sector_id, SECTOR_ID),
                ADDRESS = COALESCE(:address, ADDRESS),
                LATITUDE = COALESCE(:lat, LATITUDE),
                LONGITUDE = COALESCE(:lon, LONGITUDE),
                DEMAND_KG = COALESCE(:demand_kg, DEMAND_KG),
                TW_START = CASE WHEN :tw_start IS NOT NULL 
                               THEN TO_TIMESTAMP(:date || ' ' || :tw_start, 'YYYY-MM-DD HH24:MI')
                               ELSE TW_START END,
                TW_END = CASE WHEN :tw_end IS NOT NULL 
                             THEN TO_TIMESTAMP(:date || ' ' || :tw_end, 'YYYY-MM-DD HH24:MI')
                             ELSE TW_END END,
                PRIORITY = COALESCE(:priority, PRIORITY)
            WHERE JOB_ID = :job_id
        """, {
            "sector_id": data.get('sector_id'),
            "address": data.get('address'),
            "lat": data.get('lat'),
            "lon": data.get('lon'),
            "demand_kg": data.get('demand_kg'),
            "date": date,
            "tw_start": data.get('tw_start'),
            "tw_end": data.get('tw_end'),
            "priority": data.get('priority'),
            "job_id": job_id
        })
        
        conn.commit()
        return jsonify({"message": "작업 정보가 수정되었습니다."}), 200
        
    except oracledb.Error as db_err:
        if conn: conn.rollback()
        return jsonify({"error": "데이터베이스 오류", "details": str(db_err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"작업 수정 오류: {e}")
        return jsonify({"error": "작업 수정 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    """작업을 삭제합니다."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM JOBS WHERE JOB_ID = :job_id", {"job_id": job_id})
        
        if cursor.rowcount == 0:
            return jsonify({"error": "작업을 찾을 수 없습니다."}), 404
        
        conn.commit()
        return jsonify({"message": "작업이 삭제되었습니다."}), 200
        
    except oracledb.Error as db_err:
        if conn: conn.rollback()
        return jsonify({"error": "데이터베이스 오류", "details": str(db_err)}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"작업 삭제 오류: {e}")
        return jsonify({"error": "작업 삭제 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


# --- API #7: 대시보드 API ---
@app.route('/api/dashboard/run-history', methods=['GET'])
def get_run_history():
    """실행 이력을 조회합니다."""
    conn = None
    try:
        date_range = request.args.get('dateRange', 'week')
        vehicle_id = request.args.get('vehicleId', 'all')
        sector_id = request.args.get('sectorId', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 날짜 범위 계산
        date_filter = ""
        if date_range == 'day':
            date_filter = "AND TRUNC(r.RUN_DATE) = TRUNC(SYSDATE)"
        elif date_range == 'week':
            date_filter = "AND r.RUN_DATE >= TRUNC(SYSDATE) - 7"
        elif date_range == 'month':
            date_filter = "AND r.RUN_DATE >= TRUNC(SYSDATE) - 30"
        elif date_range == 'quarter':
            date_filter = "AND r.RUN_DATE >= TRUNC(SYSDATE) - 90"
        
        sql = """
            SELECT 
                r.RUN_ID as run_id,
                TO_CHAR(r.RUN_DATE, 'YYYY-MM-DD') as date,
                COALESCE(rs.TOTAL_DISTANCE_KM, 0) as total_distance,
                COALESCE(rs.TOTAL_CO2_G / 1000.0, 0) as total_co2,
                (SELECT COUNT(*) FROM JOBS j WHERE j.RUN_ID = r.RUN_ID) as served_jobs
            FROM RUNS r
            LEFT JOIN RUN_SUMMARY rs ON r.RUN_ID = rs.RUN_ID
            WHERE 1=1
        """ + date_filter + """
            ORDER BY r.RUN_DATE DESC
            FETCH FIRST 50 ROWS ONLY
        """
        
        cursor.execute(sql)
        
        rows = cursor.fetchall()
        cols = [col[0].lower() for col in cursor.description]
        history = [dict(zip(cols, row)) for row in rows]
        
        return jsonify(history), 200
    except Exception as e:
        print(f"실행 이력 조회 오류: {e}")
        return jsonify({"error": "실행 이력 조회 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/dashboard/charts', methods=['GET'])
def get_dashboard_charts():
    """대시보드 차트 데이터를 조회합니다."""
    conn = None
    try:
        date_range = request.args.get('dateRange', 'week')
        vehicle_id = request.args.get('vehicleId', 'all')
        sector_id = request.args.get('sectorId', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 날짜 범위 계산
        date_filter = ""
        if date_range == 'day':
            date_filter = "AND TRUNC(r.RUN_DATE) = TRUNC(SYSDATE)"
        elif date_range == 'week':
            date_filter = "AND r.RUN_DATE >= TRUNC(SYSDATE) - 7"
        elif date_range == 'month':
            date_filter = "AND r.RUN_DATE >= TRUNC(SYSDATE) - 30"
        elif date_range == 'quarter':
            date_filter = "AND r.RUN_DATE >= TRUNC(SYSDATE) - 90"
        
        # 주간 CO2 추이
        cursor.execute("""
            SELECT 
                TO_CHAR(r.RUN_DATE, 'YYYY-MM-DD') as date,
                COALESCE(SUM(rs.TOTAL_CO2_G / 1000.0), 0) as co2
            FROM RUNS r
            LEFT JOIN RUN_SUMMARY rs ON r.RUN_ID = rs.RUN_ID
            WHERE 1=1
        """ + date_filter + """
            GROUP BY r.RUN_DATE
            ORDER BY r.RUN_DATE
        """)
        
        weekly_co2_rows = cursor.fetchall()
        weekly_co2 = [{"date": row[0], "co2": float(row[1])} for row in weekly_co2_rows]
        
        # 차량별 주행거리
        vehicle_filter = ""
        if date_range == 'week':
            vehicle_filter = "AND r.RUN_DATE >= TRUNC(SYSDATE) - 7"
        if vehicle_id != 'all':
            vehicle_filter += f" AND v.VEHICLE_ID = :vehicle_id"
        
        vehicle_sql = """
            SELECT 
                v.VEHICLE_ID as vehicle,
                COALESCE(SUM(rs.TOTAL_DISTANCE_KM), 0) as distance
            FROM VEHICLES v
            LEFT JOIN RUNS r ON v.VEHICLE_ID = r.VEHICLE_ID
            LEFT JOIN RUN_SUMMARY rs ON r.RUN_ID = rs.RUN_ID
            WHERE 1=1
        """ + vehicle_filter + """
            GROUP BY v.VEHICLE_ID
            ORDER BY v.VEHICLE_ID
        """
        vehicle_params = {}
        if vehicle_id != 'all':
            vehicle_params['vehicle_id'] = vehicle_id
        cursor.execute(vehicle_sql, vehicle_params)
        
        vehicle_dist_rows = cursor.fetchall()
        vehicle_distances = [{"vehicle": row[0], "distance": float(row[1])} for row in vehicle_dist_rows]
        
        # 섹터별 수요량
        sector_filter = date_filter
        sector_params = {}
        if sector_id != 'all':
            sector_filter += " AND j.SECTOR_ID = :sector_id"
            sector_params['sector_id'] = sector_id
        
        cursor.execute("""
            SELECT 
                j.SECTOR_ID as sector,
                COALESCE(SUM(j.DEMAND_KG), 0) as demand
            FROM JOBS j
            JOIN RUNS r ON j.RUN_ID = r.RUN_ID
            WHERE 1=1
        """ + sector_filter + """
            GROUP BY j.SECTOR_ID
            ORDER BY j.SECTOR_ID
        """, sector_params)
        
        sector_demands_rows = cursor.fetchall()
        sector_demands = [{"sector": row[0], "demand": float(row[1])} for row in sector_demands_rows]
        
        return jsonify({
            "weekly_co2": weekly_co2,
            "vehicle_distances": vehicle_distances,
            "sector_demands": sector_demands
        }), 200
        
    except Exception as e:
        print(f"차트 데이터 조회 오류: {e}")
        return jsonify({"error": "차트 데이터 조회 실패", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()


# --- Flask 앱 실행 ---
if __name__ == '__main__':
    # config 파일에서 포트 가져오기 (없으면 5000 기본값)
    # config.py에 FLASK_PORT 설정이 없다면 5000을 사용합니다.
    port = getattr(config, 'FLASK_PORT', 5000)

    app.run(debug=True, port=port)
