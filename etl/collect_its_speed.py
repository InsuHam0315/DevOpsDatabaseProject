import os, requests, oracledb
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

DB_USER=os.getenv("DB_USER"); DB_PASSWORD=os.getenv("DB_PASSWORD"); DB_DSN=os.getenv("DB_DSN")
ITS_API_KEY=os.getenv("ITS_API_KEY"); ITS_API_BASE=os.getenv("ITS_API_BASE")

def fetch_its_speed(link_ids:list, when:datetime)->list[dict]:
    # 엔드포인트/파라미터는 포털 스펙에 맞춰 채우기
    headers={"Accept":"application/json"}
    params={"key": ITS_API_KEY, "links": ",".join(link_ids), "ts": when.strftime("%Y%m%d%H%M")}
    r=requests.get(f"{ITS_API_BASE}/speed", headers=headers, params=params, timeout=30)
    r.raise_for_status()
    data=r.json()
    rows=[]
    for item in data.get("items", []):
        rows.append({
            "LINK_ID": item["linkId"],
            "OBS_TS": when,  # or parse from item
            "SPEED_KMH": item.get("speed"),
            "VOLUME": item.get("volume"),
            "OCCUPANCY": item.get("occ"),
        })
    return rows

def load_rows(rows:list[dict]):
    with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO ITS_TRAFFIC (ID, LINK_ID, OBS_TS, SPEED_KMH, VOLUME, OCCUPANCY)
                VALUES (ITS_TRAFFIC_SEQ.NEXTVAL, :LINK_ID, :OBS_TS, :SPEED_KMH, :VOLUME, :OCCUPANCY)
            """, rows)
        conn.commit()

if __name__=="__main__":
    KST=timezone(timedelta(hours=9))
    now=datetime.now(KST).replace(second=0, microsecond=0)
    rows=fetch_its_speed(link_ids=["L1","L2"], when=now)
    if rows: load_rows(rows); print(f"ITS rows: {len(rows)} inserted")
