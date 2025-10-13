import sqlite3
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- 1. 설정 및 상수 ---
API_KEY = "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"  # ❗ 여기에 당신의 OpenRouter 키를 입력하세요
API_URL = "https://openrouter.ai/api/v1/chat/completions"
DB_FILE = "logistics_final.db"
# ... (FUEL_CONSTANTS 등 다른 상수는 이전 버전과 동일하게 유지)

# --- 2. Flask 앱 초기화 및 DB 설정 ---
app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    with get_db_connection() as conn:
        conn.execute("DROP TABLE IF EXISTS plans")
        conn.execute("""
            CREATE TABLE plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT,
                vehicles TEXT,
                jobs TEXT, -- JSON 데이터를 문자열로 저장
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    print("✅ 최종 DB 스키마 생성 완료.")

# --- 3. 핵심 로직 함수 ---
def call_llm(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {"model": "google/gemini-2.0-flash-exp:free", "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"API 호출 오류: {e}"

# --- 4. API 엔드포인트(Endpoint) 구현 ---

# 💡 API #1: "파싱 시뮬레이트" 버튼용 API (자연어 -> JSON -> DB 저장)
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

    try:
        clean_json_str = json_response[json_response.find('{'):json_response.rfind('}') + 1]
        parsed_data = json.loads(clean_json_str)
        
        # 1. 파싱된 데이터를 DB에 저장
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO plans (run_date, vehicles, jobs) 
                VALUES (?, ?, ?)
            """, (
                parsed_data.get('run_date'),
                json.dumps(parsed_data.get('vehicles')),
                json.dumps(parsed_data.get('jobs'))
            ))
            new_id = cursor.lastrowid
            conn.commit()
            
            # 2. 방금 저장한 데이터를 다시 조회하여 반환
            new_plan = conn.execute("SELECT * FROM plans WHERE id = ?", (new_id,)).fetchone()
        
        return jsonify(dict(new_plan)), 201

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return jsonify({"error": "LLM 응답 처리 또는 DB 저장 실패", "details": str(e), "raw_response": json_response}), 500

# 💡 API #2: "최적화 실행" 버튼용 API (DB 조회 -> LLM 분석)
@app.route('/api/analyze-plan/<int:plan_id>', methods=['GET'])
def analyze_plan(plan_id):
    try:
        # 1. ID를 이용해 DB에서 계획 조회
        with get_db_connection() as conn:
            plan_data_row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        
        if plan_data_row is None:
            return jsonify({"error": f"ID {plan_id}에 해당하는 계획을 찾을 수 없습니다."}), 404
        
        plan_data = dict(plan_data_row)
        # 문자열로 저장된 JSON을 다시 파이썬 객체로 변환
        plan_data['vehicles'] = json.loads(plan_data['vehicles'])
        plan_data['jobs'] = json.loads(plan_data['jobs'])

        # 2. 조회한 데이터로 LLM 분석 요청
        prompt = f"""
        당신은 최첨단 물류 최적화 AI 전문가입니다. 아래의 데이터베이스에서 조회된 계획 데이터를 바탕으로 전문적인 분석 보고서를 작성해주세요.
        [계획 데이터 (ID: {plan_data.get('id')})]
        - 운행 날짜: {plan_data.get('run_date')}
        - 투입 차량: {', '.join(plan_data.get('vehicles', []))} ({len(plan_data.get('vehicles', []))}대)
        - 총 작업 수: {len(plan_data.get('jobs', []))}개
        - 총 배송량: {sum(job.get('demand_kg', 0) for job in plan_data.get('jobs', []))}kg
        [요청사항]
        아래 세 가지 항목에 맞춰 보고서를 작성해주세요. 각 항목 앞에 🔹, 🌱, 🎯 이모지를 꼭 붙여주세요.
        1. 🔹 최적화 분석: 이 계획을 효율적으로 수행하기 위한 핵심 고려사항은 무엇인가요?
        2. 🌱 친환경 효과: 이 계획을 전기차(EV) 위주로 수행했을 때 예상되는 CO₂ 절감 효과를 간략히 설명해주세요.
        3. 🎯 최적화 포인트: 이 계획의 성공적인 실행을 위한 가장 중요한 최적화 포인트를 한 문장으로 요약해주세요.
        """
        analysis_report = call_llm(prompt)
        return jsonify({"analysis": analysis_report}), 200

    except Exception as e:
        return jsonify({"error": "최적화 분석 중 오류 발생", "details": str(e)}), 500

# --- 5. 앱 실행 ---
if __name__ == '__main__':
    setup_database()
    app.run(debug=True, port=5001)