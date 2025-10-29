import oracledb
import config # DB 접속 정보를 담고 있는 config 모듈
from datetime import datetime

# --- 1. DB 연결 함수 ---
def get_db_connection():
    """실제 DB 작업을 위한 새 Oracle 연결 객체를 반환합니다."""
    try:
        conn = oracledb.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dsn=config.DB_DSN
        )
        return conn # ⬅️ 중요: dict가 아닌 conn 객체 자체를 반환
    except Exception as e:
        print(f"❌ DB 연결 생성 실패: {e}")
        raise # ⬅️ 오류가 나면 앱이 알 수 있도록 예외를 다시 발생시킴

def test_db_connection():
    try:
        conn = oracledb.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dsn=config.DB_DSN
        )
        print("✅ 데이터베이스 연결 성공!")
        # 👇 성공 시 연결 객체(conn) 자체를 반환해야 합니다.
        return conn
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        # 👇 실패 시 None을 반환하거나 예외를 발생시킵니다.
        # return None
        raise ConnectionError(f"DB 연결 실패: {e}") # 예외 발생이 더 명확할 수 있음

# --------------------------------LLM 저장 파트----------------------------------------
# --- 2. RUNS 테이블 저장 함수 ---
def save_run(cursor: oracledb.Cursor, run_params: dict):
    """
    RUNS 테이블에 새로운 실행 정보를 저장합니다.
    run_params 딕셔너리는 'run_id', 'run_date_str', 'depot_lat', 'depot_lon',
                           'natural_language_input', 'optimization_status' 키를 포함해야 합니다.
    """
    try:
        sql = """
            INSERT INTO RUNS (
                RUN_ID, RUN_DATE, DEPOT_LAT, DEPOT_LON,
                NATURAL_LANGUAGE_INPUT, OPTIMIZATION_STATUS, CREATED_AT
            ) VALUES (
                :run_id, TO_DATE(:run_date_str, 'YYYY-MM-DD'), :depot_lat, :depot_lon,
                :natural_language_input, :optimization_status, SYSTIMESTAMP
            )
        """
        cursor.execute(sql, run_params)
        print(f"RUNS 테이블 저장 성공 (run_id: {run_params.get('run_id')})")
    except Exception as e:
        print(f"❌ RUNS 테이블 저장 실패: {e}")
        raise # 오류 발생 시 상위 호출자에게 알림

# --- 3. JOBS 테이블 저장 함수 ---
def save_job(cursor: oracledb.Cursor, job_params: dict) -> int:
    """
    JOBS 테이블에 새로운 작업 정보를 저장하고, 생성된 JOB_ID를 반환합니다.
    job_params 딕셔너리는 'run_id', 'sector_id', 'address', 'latitude', 'longitude',
                           'demand_kg', 'tw_start_str', 'tw_end_str', 'priority', 'run_date_str' 키를 포함해야 합니다.
    """
    try:
        # JOB_ID를 반환받기 위한 변수 설정
        new_job_id_var = cursor.var(oracledb.NUMBER)
        job_params['new_job_id'] = new_job_id_var # 바인드 변수에 추가

        # 시간 문자열과 날짜 문자열을 결합하여 TIMESTAMP로 변환하는 SQL 사용
        # (주의: 시간 형식이 'HH24:MI'가 아닐 경우 형식 문자열 수정 필요)
        sql = """
            INSERT INTO JOBS (
                RUN_ID, SECTOR_ID, ADDRESS, LATITUDE, LONGITUDE, DEMAND_KG,
                TW_START, TW_END, PRIORITY
                -- JOB_ID는 트리거에 의해 자동 생성됨
            ) VALUES (
                :run_id, :sector_id, :address, :latitude, :longitude, :demand_kg,
                TO_TIMESTAMP(:run_date_str || ' ' || :tw_start_str, 'YYYY-MM-DD HH24:MI'),
                TO_TIMESTAMP(:run_date_str || ' ' || :tw_end_str, 'YYYY-MM-DD HH24:MI'),
                :priority
            )
            RETURNING JOB_ID INTO :new_job_id
        """
        cursor.execute(sql, job_params)
        generated_job_id = new_job_id_var.getvalue()[0] # NUMBER 값을 가져옴
        print(f"JOBS 테이블 저장 성공 (job_id: {generated_job_id})")
        return generated_job_id
    except Exception as e:
        print(f"❌ JOBS 테이블 저장 실패: {e}")
        raise

# --- 4. RUN_SUMMARY 테이블 저장 함수 (LLM 분석 결과) ---
def save_llm_analysis_summary(cursor: oracledb.Cursor, summary_params: dict):
    """
    RUN_SUMMARY 테이블에 LLM 분석 결과와 임시 KPI 값을 저장합니다.
    summary_params 딕셔너리는 'run_id', 'llm_explanation', 'total_distance_km',
                              'total_co2_g', 'total_time_min', 'saving_pct' 키를 포함해야 합니다.
    """
    try:
        # SUMMARY_ID는 트리거로 자동 생성됨
        sql = """
            INSERT INTO RUN_SUMMARY (
                RUN_ID, LLM_EXPLANATION,
                TOTAL_DISTANCE_KM, TOTAL_CO2_G, TOTAL_TIME_MIN, SAVING_PCT
            ) VALUES (
                :run_id, :llm_explanation,
                :total_distance_km, :total_co2_g, :total_time_min, :saving_pct
            )
        """
        # CLOB 데이터 바인딩 설정 (LLM 설명이 길 경우)
        # 만약 llm_explanation이 매우 길다면 별도 처리가 필요할 수 있습니다.
        # oracledb 문서 참고: https://python-oracledb.readthedocs.io/en/latest/user_guide/lob_data.html
        if summary_params.get('llm_explanation'):
            cursor.setinputsizes(llm_explanation=oracledb.DB_TYPE_CLOB)

        cursor.execute(sql, summary_params)
        print(f"RUN_SUMMARY 테이블 저장 성공 (run_id: {summary_params.get('run_id')})")
    except Exception as e:
        print(f"❌ RUN_SUMMARY 테이블 저장 실패: {e}")
        raise
# --------------------------------------------------------------------------------------------
# --- 읽기 전용 헬퍼 추가 ------------------------------------
def _connect():
    return oracledb.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        dsn=config.DB_DSN
    )

def get_settings_from_db():
    """
    SETTINGS 테이블에서 (KEY, VALUE) 전체를 반환.
    예: [("alpha_load","0.1"), ("beta_grade","0.03"), ...]
    """
    sql = "SELECT KEY, VALUE FROM SETTINGS"
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return rows  # List[Tuple[str, str]]

def get_congestion_factors_from_db(hour: int):
    """
    CONGESTION_INDEX에서 주어진 시각(hour)의 (TF, IDLE_F)을 반환한다.
    실제 컬럼명은 TIME_FACTOR / IDLE_FACTOR 이므로 매핑해서 리턴.
    """
    sql = """
        SELECT TIME_FACTOR, IDLE_FACTOR
          FROM CONGESTION_INDEX
         WHERE HOUR_OF_DAY = :h
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, h=hour)
            row = cur.fetchone()   # (time_factor, idle_factor) or None
            if not row:
                return None
            time_factor, idle_factor = row
            # co2_calculator가 기대하는 (tf, idle_f) 형태로 변환
            return (float(time_factor), float(idle_factor))

def get_vehicle_ef_from_db(vehicle_type: str):
    """
    EMISSION_FACTORS에서 차량 타입별 고정 배출계수/공회전 계수 가져오기.
    반환: {'ef_gpkm': float, 'idle_gps': float, 'fuel_type': str} 또는 None
    """
    sql = """
        SELECT CO2_GPKM, IDLE_GPS, FUEL_TYPE
          FROM EMISSION_FACTORS
         WHERE LOWER(VEHICLE_TYPE) = LOWER(:vtype)
         FETCH FIRST 1 ROWS ONLY
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, vtype=vehicle_type)
            row = cur.fetchone()
            if not row:
                return None
            co2_gpkm, idle_gps, fuel_type = row
            return {
                "ef_gpkm": float(co2_gpkm) if co2_gpkm is not None else None,
                "idle_gps": float(idle_gps) if idle_gps is not None else None,
                "fuel_type": fuel_type
            }
