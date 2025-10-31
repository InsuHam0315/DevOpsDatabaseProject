from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import sys

# --------------------------------------------------------------------------
# ⭐ [다른 팀원 작업] LLM 관련 모듈 임포트 유지
# --------------------------------------------------------------------------
# LLM 모듈이 존재하지 않을 경우를 대비하여 ImportError를 무시하고 진행
try:
    from LLM.llm_call import llm_bp # ⬅️ 이제 이 경로는 (BASE_DIR + /LLM/llm_call.py)를 찾습니다.
    LLM_BLUEPRINT_AVAILABLE = True
except ImportError as e: # ⬅️ [수정] 오류가 뜬다면 여기서 e를 출력하게 합니다.
    print(f"❌ LLM 블루프린트 임포트 실패: {e}") # ⬅️ 디버깅을 위해 e를 출력
    LLM_BLUEPRINT_AVAILABLE = False

# --------------------------------------------------------------------------
# ⭐ [우리 팀 작업] 서비스 및 최적화 모듈 임포트
# --------------------------------------------------------------------------
try:
    from services.db_handler import test_db_connection
    from optimizer.engine import run_optimization
except ImportError as e:
    print(f"❌ FATAL ERROR: 필수 모듈 임포트 실패: {e}. 'backend' 폴더에서 실행 중인지 확인하세요.")
    sys.exit(1)


# 플라스크 앱(서버)을 생성합니다.
app = Flask(__name__)
CORS(app)

# LLM 블루프린트가 사용 가능할 경우에만 등록 (다른 팀원 작업 유지)
if LLM_BLUEPRINT_AVAILABLE:
    app.register_blueprint(llm_bp)
    print("✅ LLM 블루프린트가 성공적으로 등록되었습니다.")
else:
    print("❌ LLM 블루프린트 등록 스킵.")


# --- 기본 및 테스트 엔드포인트 ---

@app.route('/')
def index():
    """서버 상태 확인용 기본 엔드포인트"""
    return jsonify({"status": "ok", "message": "Eco Logistics Optimizer API is running!"})

@app.route('/test-db')
def db_connection_test_endpoint():
    """DB 연결 테스트용 엔드포인트 (기존 코드 유지)"""
    try:
        result = test_db_connection()
        status_code = 200 if result.get("status") == "success" else 500
        return jsonify(result), status_code
    except Exception as e:
        print(f"❌ /test-db 처리 중 오류: {traceback.format_exc()}")
        return jsonify({"status": "failed", "error": f"DB 테스트 중 서버 오류: {e}"}), 500


# --- ⭐ 메인 최적화 API 엔드포인트 (우리 팀의 핵심 성과) ⭐ ---

@app.route('/optimize', methods=['POST'])
def handle_optimization_request():
    """
    최적화 요청(run_id, vehicle_ids)을 받아 engine을 실행하고 결과를 반환합니다.
    """
    print("Received optimization request...")
    try:
        # 1. 요청 데이터 받기 및 검증
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError("요청 본문이 유효한 JSON 객체가 아닙니다.")
        if 'run_id' not in data or 'vehicle_ids' not in data:
            raise ValueError("요청 본문에 'run_id'와 'vehicle_ids'가 필요합니다.")

        run_id = data['run_id']
        vehicle_ids = data['vehicle_ids']
        if not isinstance(vehicle_ids, list):
            raise ValueError("'vehicle_ids'는 리스트 형태여야 합니다.")

        print(f"   Run ID: {run_id}, Vehicles: {vehicle_ids}")

        # 2. 최적화 엔진 실행 (engine.py는 인자 2개만 받음)
        # 이 함수 내에서 Kakao API 호출, OR-Tools 최적화, CO2 계산 및 DB 저장이 모두 수행됩니다.
        optimization_result = run_optimization(run_id, vehicle_ids)

        # 3. 최적화 결과 반환
        if isinstance(optimization_result, dict):
            status = optimization_result.get("status", "unknown")
            if status == "success":
                print("   Optimization successful, returning results.")
                return jsonify(optimization_result), 200
            elif status == "warning":
                print("   Optimization succeeded with warnings (DB Save Fail, etc.).")
                return jsonify(optimization_result), 206
            else:
                return jsonify(optimization_result), 500
        else:
            return jsonify({"status": "failed", "message": "최적화 결과 처리 중 예상치 못한 오류 발생"}), 500

    except ValueError as ve: 
        return jsonify({"status": "failed", "message": f"잘못된 요청: {ve}"}), 400
    except Exception as e: 
        error_details = traceback.format_exc()
        print(f"   Internal server error during /optimize handling:\n{error_details}")
        return jsonify({"status": "failed", "message": f"서버 내부 오류 발생: {e}"}), 500




# --- 서버 실행 ---
if __name__ == '__main__':
    # Flask 서버는 app.py가 실행된 환경에 따라 OCI DB와 Kakao API 키를 사용합니다.
    print("\nStarting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
