import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 변수를 직접 export합니다.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DSN = os.getenv('DB_DSN')

FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))