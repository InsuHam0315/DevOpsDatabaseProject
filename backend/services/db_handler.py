import oracledb
import config # DB 접속 정보를 담고 있는 config 모듈

# --- 1. DB 연결 함수 ---
def test_db_connection():
    try:
        conn = oracledb.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dsn=config.DB_DSN
        )
        print("✅ 데이터베이스 연결 성공!")
        # 👇 성공 시 연결 객체(conn) 자체를 반환해야 합니다.
        return conn
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        # 👇 실패 시 None을 반환하거나 예외를 발생시킵니다.
        # return None
        raise ConnectionError(f"DB 연결 실패: {e}") # 예외 발생이 더 명확할 수 있음