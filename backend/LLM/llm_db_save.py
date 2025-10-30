import oracledb
# --------------------------------LLM 저장 파트----------------------------------------
# --- 2. RUNS 테이블 저장 함수 ---
def save_run(cursor: oracledb.Cursor, run_params: dict):
    try:
        sql = """
            INSERT INTO RUNS (
                RUN_ID, RUN_DATE, DEPOT_LAT, DEPOT_LON, OPTIMIZATION_STATUS, NATURAL_LANGUAGE_INPUT
            ) VALUES (
                :run_id, TO_DATE(:run_date_str, 'YYYY-MM-DD'), :depot_lat, :depot_lon, :optimization_status, :natural_language_input
            )
        """
        cursor.execute(sql, run_params)
        print(f"RUNS 테이블 저장 성공 (run_id: {run_params.get('run_id')})")
    except Exception as e:
        print(f"❌ RUNS 테이블 저장 실패: {e}")
        raise # 오류 발생 시 상위 호출자에게 알림

# --- 3. JOBS 테이블 저장 함수 ---
def save_job(cursor: oracledb.Cursor, job_params: dict) -> int:
    try:
        # JOB_ID를 반환받기 위한 변수 설정
        new_job_id_var = cursor.var(oracledb.NUMBER)
        job_params['new_job_id'] = new_job_id_var # 바인드 변수에 추가

        # 시간 문자열과 날짜 문자열을 결합하여 TIMESTAMP로 변환하는 SQL 사용
        # (주의: 시간 형식이 'HH24:MI'가 아닐 경우 형식 문자열 수정 필요)
        sql = """
            INSERT INTO JOBS (
                RUN_ID, SECTOR_ID, ADDRESS, LATITUDE, LONGITUDE, DEMAND_KG
            ) VALUES (
                :run_id, :sector_id, :address, :lat, :lon, :demand_kg
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