import os
import requests

API_KEY = os.getenv("GOOGLE_API_KEY") or "AIzaSyC-pRLAZYYpcTN4xnemni7j_aPHryA1c7k"

# ✅ 정확한 모델명 사용
url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"

headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": API_KEY,
}

data = {
    "contents": [
        {"parts": [{"text": "안녕! 지금 Gemini 2.5 Flash 연결 테스트 중이야."}]}
    ]
}

response = requests.post(url, headers=headers, json=data, timeout=30)
print(response.status_code)
print(response.text)
