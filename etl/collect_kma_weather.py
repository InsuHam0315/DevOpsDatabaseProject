import os, requests, oracledb
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

DB_USER=os.getenv("DB_USER"); DB_PASSWORD=os.getenv("DB_PASSWORD"); DB_DSN=os.getenv("DB_DSN")
KMA_API_KEY=os.getenv("KMA_API_KEY"); KMA_API_BASE=os.getenv("KMA_API_BASE")

def fetch_ultra_now(nx:int, ny:int, base_dt:datetime)->list[dict]:
    params = {
        "serviceKey": KMA_API_KEY,
        "pageNo": 1, "numOfRows": 1000,
        "dataType": "JSON",
        # 아래 파라미터명은 API 문서대로 맞추기 (예: base_date, base_time, nx, ny)
        "base_date": base_dt.strftime("%Y%m%d"),
        "base_time": base_dt.strftime("%H%M"),
        "nx": nx, "ny": ny
    }
    r = requests.get(f"{KMA_API_BASE}/getUltraSrtNcst", params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    # 문서 스펙의 items→item 구조를 파싱하여 dict로 정규화
    items = j.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    out = {"NX": nx, "NY": ny, "BASE_TS": base_dt}
    for it in items:
        cat = it.get("category")
        val = it.get("obsrValue")
        # 필요한 항목만 매핑 (예:T1H/RN1/REH/UUU/VVV/PTY)
        if cat in ("T1H","RN1","REH","UUU","VVV","PTY"):
            out[cat] = float(val) if val not in (None, "") else None
    return [out]

def load_weather(rows:list[dict]):
    with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO WEATHER_OBS (ID, BASE_TS, NX, NY, T1H, RN1, UUU, VVV, REH, PTY)
                VALUES (WEATHER_OBS_SEQ.NEXTVAL, :BASE_TS, :NX, :NY, :T1H, :RN1, :UUU, :VVV, :REH, :PTY)
            """, rows)
        conn.commit()

if __name__=="__main__":
    KST=timezone(timedelta(hours=9))
    base_dt=datetime.now(KST).replace(minute=0, second=0, microsecond=0)
    rows=fetch_ultra_now(nx=56, ny=68, base_dt=base_dt)  # (예: 군산 격자값은 따로 계산/테이블화)
    load_weather(rows)
    print("KMA rows inserted:", len(rows))
