import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# DB
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DSN = os.getenv('DB_DSN')

# OCI SERVER
OCI_WALLET_DIR = os.getenv('OCI_WALLET_DIR')
OCI_WALLET_PASSWORD = os.getenv('OCI_WALLET_PASSWORD')

# KAKAO
KAKAOMAP_REST_API = os.getenv('REST_API_KEY')
KAKAOMAP_SCRIPT = os.getenv('NEXT_PUBLIC_KAKAO_MAP_API_KEY')

# Flask 포트 설정
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))

#  Google Gemini LLM 설정
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
