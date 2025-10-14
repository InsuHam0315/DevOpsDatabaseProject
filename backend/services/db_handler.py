import oracledb
# 1. 'from config import config' 대신, 파일 전체를 불러오도록 수정합니다.
import config

def test_db_connection():
    """DB 연결을 테스트하고, 성공 시 버전 정보를 반환하는 함수"""
    try:
        # 2. config 객체가 아닌, 'config 모듈의 변수' 형태로 사용하도록 수정합니다.
        conn = oracledb.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dsn=config.DB_DSN
        )
        db_version = conn.version
        print(f"✅ 데이터베이스 연결 성공! Oracle DB Version: {db_version}")
        conn.close()
        return {"status": "success", "db_version": db_version}
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return {"status": "failed", "error": str(e)}