import pandas as pd, oracledb, os
from dotenv import load_dotenv
load_dotenv()

DB_USER=os.getenv("DB_USER"); DB_PASSWORD=os.getenv("DB_PASSWORD"); DB_DSN=os.getenv("DB_DSN")

def load_grades(csv_path:str):
    df = pd.read_csv(csv_path)  # 원본 헤더에 맞춰 컬럼 매핑
    df = df.rename(columns={
        "route_id":"ROUTE_ID","start_km":"START_KM","end_km":"END_KM","grade_pct":"GRADE_PCT",
        "start_lat":"START_LAT","start_lon":"START_LON","end_lat":"END_LAT","end_lon":"END_LON"
    })
    rows = df.to_dict(orient="records")
    with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO ROAD_GRADES
                (SECTION_ID, ROUTE_ID, START_KM, END_KM, GRADE_PCT, START_LAT, START_LON, END_LAT, END_LON)
                VALUES (ROAD_GRADES_SEQ.NEXTVAL, :ROUTE_ID, :START_KM, :END_KM, :GRADE_PCT, :START_LAT, :START_LON, :END_LAT, :END_LON)
            """, rows)
        conn.commit()

if __name__=="__main__":
    load_grades("../data/processed/road_grades/grades_gunsan.csv")
    print("ROAD_GRADES loaded.")
