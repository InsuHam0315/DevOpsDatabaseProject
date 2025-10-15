from flask import Flask, request, jsonify
# config.py에서 객체가 아닌, 필요한 변수들을 직접 불러옵니다.
from flask_cors import CORS
import config
# db_handler.py 에서 만든 테스트 함수를 불러옵니다.
from services.db_handler import test_db_connection
import requests
import json
import oracledb

app = Flask(__name__)
CORS(app)
# 설정값이 잘 로드되었는지 터미널에 출력해서 확인해봅니다.
# config.DB_USER 형태로 사용합니다.
print(f"DB User from config: {config.DB_USER}")
print(f"DB DSN from config: {config.DB_DSN}")


# '/' 기본 주소는 서버가 켜져 있는지 확인하는 용도로 그대로 둡니다.
@app.route('/')
def index():
    """서버가 살아있는지 확인하는 기본 엔드포인트"""
    return jsonify({"status": "ok", "message": "Eco Logistics Optimizer API is running!"})

# '/test-db' 라는 새로운 주소를 만듭니다.
@app.route('/test-db')
def db_connection_test_endpoint():
    """DB 연결을 테스트하는 API 엔드포인트"""
    result = test_db_connection()
    
    if result["status"] == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
#---------------------------------------------------------------------------------------------------------------------LLM Part
# 💡 1. LLM 호출 함수 추가
def call_llm(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"} # 💡 config 파일에서 API 키를 가져옵니다.
    payload = {"model": "google/gemini-2.0-flash-exp:free", "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(config.OPENROUTER_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"API 호출 오류: {e}"

# 💡 2. API #1 추가: "파싱 시뮬레이트" 버튼용 (자연어 -> JSON -> DB 저장)
@app.route('/api/parse-and-save', methods=['POST'])
def parse_and_save():
    user_input = request.json.get('natural_input')
    if not user_input: return jsonify({"error": "natural_input is required"}), 400

    prompt = f"""
    당신은 물류 계획 전문가의 자연어 요청을 VRP(Vehicle Routing Problem)용 JSON 데이터로 변환하는 AI입니다.
    아래 사용자 요청에서 다음 구조에 맞춰 정보를 추출하여 JSON 형식으로만 응답해주세요. 다른 설명은 절대 추가하지 마세요.
    - "run_date": YYYY-MM-DD, - "vehicles": 차량 ID 배열, - "jobs": 작업 객체 배열 (sector_id, demand_kg, tw_start, tw_end, priority, lat, lon 포함)
    사용자 요청: "{user_input}"
    """
    json_response = call_llm(prompt)

    conn = None
    try:
        clean_json_str = json_response[json_response.find('{'):json_response.rfind('}') + 1]
        parsed_data = json.loads(clean_json_str)
        
        # '인수님'의 DB 연결 함수를 사용합니다.
        db_info = test_db_connection()
        if db_info['status'] != 'success':
            raise Exception("DB 연결 실패")
        conn = db_info['connection']
        cursor = conn.cursor()

        new_id_var = cursor.var(oracledb.NUMBER)
        cursor.execute("""
            INSERT INTO plans (run_date, vehicles, jobs) 
            VALUES (:run_date, :vehicles, :jobs)
            RETURNING id INTO :new_id
        """, {
            "run_date": parsed_data.get('run_date'),
            "vehicles": json.dumps(parsed_data.get('vehicles')),
            "jobs": json.dumps(parsed_data.get('jobs')),
            "new_id": new_id_var
        })
        new_id = new_id_var.getvalue()[0]
        conn.commit()
        
        cursor.execute("SELECT * FROM plans WHERE id = :id", {"id": new_id})
        new_plan_row = cursor.fetchone()
        columns = [col[0].lower() for col in cursor.description]
        new_plan = dict(zip(columns, new_plan_row))

        return jsonify(new_plan), 201

    except Exception as e:
        return jsonify({"error": "LLM 응답 처리 또는 DB 저장 실패", "details": str(e), "raw_response": json_response}), 500
    finally:
        if conn:
            conn.close()

# 💡 3. API #2 추가: "최적화 실행" 버튼용 (DB 조회 -> LLM 분석)
@app.route('/api/analyze-plan/<int:plan_id>', methods=['GET'])
def analyze_plan(plan_id):
    conn = None
    try:
        db_info = test_db_connection()
        if db_info['status'] != 'success':
            raise Exception("DB 연결 실패")
        conn = db_info['connection']
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM plans WHERE id = :id", {"id": plan_id})
        plan_data_row = cursor.fetchone()
        
        if plan_data_row is None:
            return jsonify({"error": f"ID {plan_id}에 해당하는 계획을 찾을 수 없습니다."}), 404
        
        columns = [col[0].lower() for col in cursor.description]
        plan_data = dict(zip(columns, plan_data_row))
        plan_data['vehicles'] = json.loads(plan_data['vehicles'])
        plan_data['jobs'] = json.loads(plan_data['jobs'])

        prompt = f"""
        당신은 최첨단 물류 최적화 AI 전문가입니다. 아래의 데이터베이스에서 조회된 계획 데이터를 바탕으로 전문적인 분석 보고서를 작성해주세요.
        [계획 데이터 (ID: {plan_data.get('id')})]
        ... (이하 분석 프롬프트 내용은 이전과 동일)
        """
        analysis_report = call_llm(prompt)
        return jsonify({"analysis": analysis_report}), 200

    except Exception as e:
        return jsonify({"error": "최적화 분석 중 오류 발생", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- 앱 실행 (기존과 동일) ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)