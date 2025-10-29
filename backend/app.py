from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
from services.db_handler import test_db_connection
from optimizer.engine import run_optimization
from LLM.llm_call import llm_bp
# 서비스 모듈에서 필요한 함수들을 불러옵니다.
try:
    from services.db_handler import test_db_connection
    # 최적화 엔진 함수를 불러옵니다.
    from optimizer.engine import run_optimization
except ImportError as e:
    print(f"❌ 초기 모듈 임포트 실패: {e}. 'backend' 폴더에서 실행 중인지 확인하세요.")
    # 서버 실행을 중단하거나, 에러 상태를 표시하는 로직 추가 가능
    exit()


# 플라스크 앱(서버)을 생성합니다.
app = Flask(__name__)
CORS(app)

app.register_blueprint(llm_bp)
# --- 기본 및 테스트 엔드포인트 ---



@app.route('/')
def index():
    """서버 상태 확인용 기본 엔드포인트"""
    return jsonify({"status": "ok", "message": "Eco Logistics Optimizer API is running!"})

@app.route('/test-db')
def db_connection_test_endpoint():
    """DB 연결 테스트용 엔드포인트"""
    try:
        result = test_db_connection()
        status_code = 200 if result.get("status") == "success" else 500
        return jsonify(result), status_code
    except Exception as e:
        print(f"❌ /test-db 처리 중 오류: {traceback.format_exc()}") # 상세 오류 로그 추가
        return jsonify({"status": "failed", "error": f"DB 테스트 중 서버 오류: {e}"}), 500


# --- ⭐ 메인 최적화 API 엔드포인트 (오류 처리 강화) ⭐ ---

@app.route('/optimize', methods=['POST'])
def handle_optimization_request():
    """
    프론트엔드로부터 최적화 요청(run_id, vehicle_ids)을 받아
    optimizer.engine을 실행하고 결과를 반환하는 API.
    """
    print("Received optimization request...")
    try:
        # 1. 프론트엔드에서 보낸 JSON 데이터 받기 및 검증
        data = request.get_json()
        if not isinstance(data, dict): # data가 딕셔너리가 맞는지 확인
             raise ValueError("요청 본문이 유효한 JSON 객체가 아닙니다.")
        if 'run_id' not in data or 'vehicle_ids' not in data:
            raise ValueError("요청 본문에 'run_id'와 'vehicle_ids'가 필요합니다.")

        run_id = data['run_id']
        vehicle_ids = data['vehicle_ids']
        # vehicle_ids가 리스트 형태인지 검증 (추가)
        if not isinstance(vehicle_ids, list):
             raise ValueError("'vehicle_ids'는 리스트 형태여야 합니다.")

        route_option_name = data.get('route_option_name', 'OR-Tools Optimal')

        print(f"   Run ID: {run_id}, Vehicles: {vehicle_ids}, Option: {route_option_name}")

        # 2. 최적화 엔진 실행
        #    engine.py의 run_optimization 함수 호출 (DB 저장까지 포함됨)
        optimization_result = run_optimization(run_id, vehicle_ids, route_option_name)

        # 3. 최적화 결과 반환 (결과가 딕셔너리인지 확인)
        if isinstance(optimization_result, dict):
            status = optimization_result.get("status", "unknown")
            if status == "success":
                print("   Optimization successful, returning results.")
                return jsonify(optimization_result), 200 # 성공
            elif status == "warning":
                 print("   Optimization succeeded with warnings.")
                 return jsonify(optimization_result), 206 # 부분 성공
            else: # failed or error
                 print(f"   Optimization failed or encountered an error: {optimization_result.get('message')}")
                 return jsonify(optimization_result), 500 # 서버 내부 오류로 간주
        else:
             # engine.py가 예상치 못한 형태의 결과를 반환한 경우
             print(f"   Optimization returned unexpected result type: {type(optimization_result)}")
             return jsonify({"status": "failed", "message": "최적화 결과 처리 중 오류 발생"}), 500

    except ValueError as ve: # 잘못된 요청 형식 등 (400 Bad Request)
        print(f"   Bad request: {ve}")
        return jsonify({"status": "failed", "message": f"잘못된 요청: {ve}"}), 400
    except Exception as e: # 예상치 못한 서버 내부 오류 (500 Internal Server Error)
        # ⭐ 상세 오류 로그(Traceback) 출력 추가 ⭐
        error_details = traceback.format_exc()
        print(f"   Internal server error during /optimize handling:\n{error_details}")
        return jsonify({"status": "failed", "message": f"서버 내부 오류 발생: {e}"}), 500

# --- 서버 실행 ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)