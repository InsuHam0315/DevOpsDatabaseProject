import oracledb
import config
from typing import List, Dict, Tuple, Any
# --------------------------------------------------------------------------
# DB 연결 헬퍼 함수
# --------------------------------------------------------------------------
def get_db_connection():
    """Oracle DB 연결 객체를 생성하고 반환합니다."""
    try:
        conn = oracledb.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dsn=config.DB_DSN
        )
        return conn
    except Exception as e:
        print(f"❌ 데이터베이스 연결 생성 실패: {e}")
        raise e

# --------------------------------------------------------------------------
# 데이터 조회 함수들
# --------------------------------------------------------------------------

def test_db_connection() -> Dict:
    """DB 연결을 테스트하고, 성공 시 버전 정보를 반환하는 함수"""
    try:
        conn = get_db_connection()
        db_version = conn.version
        print(f"✅ 데이터베이스 연결 성공! Oracle DB Version: {db_version}")
        conn.close()
        return {"status": "success", "db_version": db_version}
    except Exception as e:
        print(f"❌ 데이터베이스 연결 테스트 실패: {e}")
        return {"status": "failed", "error": str(e)}

def get_settings_from_db() -> Dict:
    """SETTINGS 테이블에서 모든 키-값 쌍을 조회하여 딕셔너리로 반환합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()
    settings = {}
    try:
        cursor.execute("SELECT key, value FROM SETTINGS")
        rows = cursor.fetchall()
        settings = {row[0]: row[1] for row in rows}
        return settings
    finally:
        cursor.close()
        conn.close()

def get_congestion_factors_from_db(hour: int) -> Tuple[Any, ...]:
    """CONGESTION_INDEX 테이블에서 현재 시간에 맞는 혼잡도 계수를 조회합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT time_factor, idle_factor
            FROM CONGESTION_INDEX
            WHERE computed_at=(SELECT MAX(computed_at) FROM CONGESTION_INDEX)
              AND hour_of_day=:h
        """, {"h": hour})
        row = cursor.fetchone()
        return row
    finally:
        cursor.close()
        conn.close()

# --- ⭐ 최적화 엔진용 데이터 조회 함수 (디버깅 코드 추가됨) ⭐ ---
def get_optimizer_input_data(run_id: str, vehicle_ids: List[str]) -> Dict:
    """
    최적화 계산에 필요한 모든 입력 데이터를 DB에서 조회하여 구조화된 딕셔너리로 반환합니다.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    result = {"depot": None, "jobs": [], "vehicles": []}

    try:
        # 1. RUNS 테이블에서 차고지(Depot) 좌표 조회
        cursor.execute("""
            SELECT DEPOT_LAT, DEPOT_LON
            FROM RUNS
            WHERE RUN_ID = :run_id
        """, {'run_id': run_id})
        depot_row_tuple = cursor.fetchone()
        if depot_row_tuple and len(depot_row_tuple) == 2:
            result["depot"] = {"latitude": depot_row_tuple[0], "longitude": depot_row_tuple[1]}
        else:
            if not depot_row_tuple:
                raise ValueError(f"Run ID '{run_id}'를 찾을 수 없습니다.")
            else:
                raise ValueError(f"Run ID '{run_id}'의 차고지 좌표 조회 결과가 예상과 다릅니다: {depot_row_tuple}")

        # 2. JOBS 테이블에서 해당 RUN_ID의 배송 작업 목록 조회 (딕셔너리로 변환)
        cursor.execute("""
            SELECT JOB_ID, LATITUDE, LONGITUDE, DEMAND_KG, TW_START, TW_END
            FROM JOBS WHERE RUN_ID = :run_id ORDER BY JOB_ID
        """, {'run_id': run_id})
        job_columns = [d[0].lower() for d in cursor.description] # 컬럼 이름 가져오기
        job_rows_tuples = cursor.fetchall() # 튜플 리스트로 가져오기
        # --- ↓↓↓ 디버깅 코드 추가 ↓↓↓ ---
        print(f"   DEBUG: Fetched job rows (tuples): {job_rows_tuples}")
        # --- ↑↑↑ 디버깅 코드 추가 ↑↑↑ ---
        result["jobs"] = [dict(zip(job_columns, row)) for row in job_rows_tuples]
        # --- ↓↓↓ 디버깅 코드 추가 ↓↓↓ ---
        print(f"   DEBUG: Converted jobs list (dict): {result['jobs']}")
        # --- ↑↑↑ 디버깅 코드 추가 ↑↑↑ ---

        # 3. VEHICLES와 EMISSION_FACTORS 조인하여 차량 정보 조회 (딕셔너리로 변환)
        bind_vars = {f"vid{i}": vid for i, vid in enumerate(vehicle_ids)}
        vehicle_query = f"""
            SELECT v.VEHICLE_ID, v.CAPACITY_KG, ef.CO2_GPKM, ef.IDLE_GPS
            FROM VEHICLES v JOIN EMISSION_FACTORS ef ON v.FACTOR_ID = ef.FACTOR_ID
            WHERE v.VEHICLE_ID IN ({','.join(':' + name for name in bind_vars)})
        """
        cursor.execute(vehicle_query, bind_vars)
        vehicle_columns = [d[0].lower() for d in cursor.description] # 컬럼 이름 가져오기
        vehicle_rows_tuples = cursor.fetchall() # 튜플 리스트로 가져오기
        # --- ↓↓↓ 디버깅 코드 추가 ↓↓↓ ---
        print(f"   DEBUG: Fetched vehicle rows (tuples): {vehicle_rows_tuples}")
        # --- ↑↑↑ 디버깅 코드 추가 ↑↑↑ ---
        result["vehicles"] = [dict(zip(vehicle_columns, row)) for row in vehicle_rows_tuples]
        # --- ↓↓↓ 디버깅 코드 추가 ↓↓↓ ---
        print(f"   DEBUG: Converted vehicles list (dict): {result['vehicles']}")
        # --- ↑↑↑ 디버깅 코드 추가 ↑↑↑ ---

        # 최종 데이터 유효성 검사 (추가)
        if not result["jobs"]:
             print("⚠️ WARNING: JOBS 데이터가 조회되지 않았습니다.")
             # 필요하다면 여기서 에러를 발생시킬 수도 있습니다.
             # raise ValueError(f"Run ID '{run_id}'에 해당하는 JOBS 데이터가 없습니다.")
        if not result["vehicles"]:
             print("⚠️ WARNING: VEHICLES 데이터가 조회되지 않았습니다.")
             # raise ValueError(f"Vehicle IDs '{vehicle_ids}'에 해당하는 VEHICLES 데이터가 없습니다.")


        print(f"✅ 최적화 입력 데이터 조회 완료 (Jobs: {len(result['jobs'])}, Vehicles: {len(result['vehicles'])})")
        return result

    finally:
        cursor.close()
        conn.close()

# --------------------------------------------------------------------------
# 데이터 저장 함수들 (이전 코드와 동일)
# --------------------------------------------------------------------------
def save_optimization_results(run_id: str, summary_data: Dict, assignments_data: List[Dict]):
    """최적화 결과를 RUN_SUMMARY와 ASSIGNMENTS 테이블에 저장하고 RUNS 상태를 업데이트합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # --- 1. RUN_SUMMARY 테이블에 결과 요약 저장 ---
        cursor.execute("""
            DELETE FROM RUN_SUMMARY
            WHERE RUN_ID = :run_id AND ROUTE_OPTION_NAME = :route_option_name
        """, {
            'run_id': run_id,
            'route_option_name': summary_data['route_option_name']
        })

        cursor.execute("""
            INSERT INTO RUN_SUMMARY (
                RUN_ID, ROUTE_OPTION_NAME, TOTAL_DISTANCE_KM, TOTAL_CO2_G, TOTAL_TIME_MIN
            ) VALUES (
                :run_id, :route_option_name, :total_distance_km, :total_co2_g, :total_time_min
            )
        """, summary_data)

        # --- 2. ASSIGNMENTS 테이블에 개별 경로 저장 ---
        cursor.execute("""
            DELETE FROM ASSIGNMENTS
            WHERE RUN_ID = :run_id AND ROUTE_OPTION_NAME = :route_option_name
        """, {
            'run_id': run_id,
            'route_option_name': summary_data['route_option_name']
        })

        assignment_tuples = [
            (
                a['run_id'], a['route_option_name'], a['vehicle_id'], a['step_order'],
                a['start_job_id'], a['end_job_id'], a['distance_km'], a['co2_g'],
                a['load_kg'], a['time_min'], a['avg_gradient_pct'], a['congestion_factor']
            )
            for a in assignments_data
        ]

        if assignment_tuples:
            cursor.executemany("""
                INSERT INTO ASSIGNMENTS (
                    RUN_ID, ROUTE_OPTION_NAME, VEHICLE_ID, STEP_ORDER,
                    START_JOB_ID, END_JOB_ID, DISTANCE_KM, CO2_G,
                    LOAD_KG, TIME_MIN, AVG_GRADIENT_PCT, CONGESTION_FACTOR
                ) VALUES (
                    :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12
                )
            """, assignment_tuples)

        # --- 3. RUNS 테이블 상태 업데이트 ---
        cursor.execute("""
            UPDATE RUNS SET OPTIMIZATION_STATUS = 'COMPLETED'
            WHERE RUN_ID = :run_id
        """, {'run_id': run_id})

        conn.commit()
        print(f"✅ Run ID {run_id} ('{summary_data['route_option_name']}') 결과 DB 저장 완료.")

    except Exception as e:
        conn.rollback()
        print(f"❌ DB 저장 중 오류 발생: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()