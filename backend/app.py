from flask import Flask, jsonify
# config.py에서 객체가 아닌, 필요한 변수들을 직접 불러옵니다.
import config
# db_handler.py 에서 만든 테스트 함수를 불러옵니다.
from services.db_handler import test_db_connection

app = Flask(__name__)

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