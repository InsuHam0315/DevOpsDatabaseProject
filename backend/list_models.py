import requests, os

API_KEY = os.getenv("GOOGLE_API_KEY") or "AIzaSyC-pRLAZYYpcTN4xnemni7j_aPHryA1c7k"

url = "https://generativelanguage.googleapis.com/v1/models"
headers = {"x-goog-api-key": API_KEY}

r = requests.get(url, headers=headers)
print(r.status_code)
print(r.text)
