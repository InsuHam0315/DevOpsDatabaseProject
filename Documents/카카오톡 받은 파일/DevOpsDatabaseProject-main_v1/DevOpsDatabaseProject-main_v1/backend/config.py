import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일을 확실히 불러오도록 경로 지정 + override 활성화
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

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

# OpenRouteService
ORS_API_KEY = os.getenv('ORS_API_KEY')

# Flask 포트 설정
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))

#  Google Gemini LLM 설정
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
