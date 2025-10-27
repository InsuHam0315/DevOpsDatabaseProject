# backend/app.py
import os
from flask import Flask, jsonify
from flask_cors import CORS

# 환경변수 로드
import config  # module-level 변수 사용(DB_USER 등)

# 서비스/엔진
from services.db_handler import test_db_connection
from services.call_llm import llm_bp  # Blueprint만 가져옴

def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    # Blueprint 등록
    app.register_blueprint(llm_bp, url_prefix="/llm")

    # 헬스체크
    @app.get("/health")
    def health():
        return jsonify(status="ok")

    # 루트
    @app.get("/")
    def index():
        return jsonify({"status": "ok",
                        "message": "Eco Logistics Optimizer API is running!"})

    # DB 연결 테스트
    @app.get("/test-db")
    def db_connection_test_endpoint():
        result = test_db_connection()  # {"status": "...", "message": "..."}
        code = 200 if result.get("status") == "success" else 500
        return jsonify(result), code

    return app


if __name__ == "__main__":
    # 설정 출력(확인용)
    print(f"DB User from config: {config.DB_USER}")
    print(f"DB DSN from config: {config.DB_DSN}")

    app = create_app()
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
