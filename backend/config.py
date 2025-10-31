import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 변수를 직접 export합니다.
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DSN = os.getenv('DB_DSN')

# OpenRouter API 설정
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_API_URL = os.getenv('OPENROUTER_API_URL')

# Flask 포트 설정
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))

# Google Gemini LLM 설정
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
