import oracledb
import config
import datetime as dt
from typing import List, Dict, Tuple, Any, Optional

# --------------------------------------------------------------------------
# DB 연결 헬퍼 함수
# --------------------------------------------------------------------------
def get_db_connection():
    """Oracle DB 연결 객체를 생성하고 반환합니다."""
    try:
        conn = oracledb.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dsn=config.DB_DSN,
            config_dir=config.OCI_WALLET_DIR,
            wallet_location=config.OCI_WALLET_DIR,
            wallet_password=config.OCI_WALLET_PASSWORD
        )
        return conn
    except Exception as e:
        # 연결 실패 시 ConnectionError를 발생시켜 상위 로직에서 처리하도록 합니다.
        raise ConnectionError(f"DB 연결 실패: {e}")

def test_db_connection() -> Dict:
    """app.py에서 사용: DB 연결을 테스트하고, 성공 시 버전 정보를 반환하는 함수"""
    try:
        conn = oracledb.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dsn=config.DB_DSN,
            config_dir=config.OCI_WALLET_DIR,
            wallet_location=config.OCI_WALLET_DIR,
            wallet_password=config.OCI_WALLET_PASSWORD
        )
        db_version = conn.version
        conn.close()
        return {"status": "success", "db_version": db_version}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# --------------------------------------------------------------------------
# 데이터 조회 함수들 (CO2 Calculator 연동용)
# --------------------------------------------------------------------------

def get_settings_from_db() -> Dict[str, Any]:
    """SETTINGS 테이블에서 모든 키-값 쌍을 조회하여 딕셔너리로 반환합니다."""
    try:
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
    except ConnectionError:
        return {}

def get_congestion_factors_from_db(hour: int) -> Optional[Tuple[Any, ...]]:
    """CONGESTION_INDEX 테이블에서 현재 시간에 맞는 혼잡도 계수 (time_factor, idle_factor)를 조회합니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 가장 최근에 COMPUTED_AT 된 데이터를 기준으로 조회합니다.
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
    except ConnectionError:
        return None

def get_its_traffic_speed(link_id: str, forecast_time: dt.datetime) -> Optional[float]:
    """
    ITS_TRAFFIC 테이블에서 특정 LINK_ID, 예상 시간 기준의 예상/실시간 속도(km/h)를 조회합니다.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT SPEED_KMH
                FROM ITS_TRAFFIC
                WHERE LINK_ID = :lid
                ORDER BY OBSERVED_AT DESC
                FETCH NEXT 1 ROWS ONLY
            """, {'lid': link_id})
            row = cursor.fetchone()
            return float(row[0]) if row and row[0] is not None else None
        finally:
            cursor.close()
            conn.close()
    except ConnectionError:
        return None

def get_weather_factors(forecast_time: dt.datetime) -> List[Dict[str, Any]]:
    """
    WEATHER_FORECAST 테이블에서 날짜와 시간을 기반으로 날씨 데이터를 조회합니다.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        result = []
        
        # TIMESTAMP에서 날짜(YYYYMMDD)와 시간(HHMM) 문자열 추출
        fcst_date = forecast_time.strftime('%Y%m%d')
        fcst_time = forecast_time.strftime('%H%M')

        try:
            cursor.execute("""
                SELECT CATEGORY, FCST_VALUE
                FROM WEATHER_FORECAST
                WHERE FCST_DATE = :fd AND FCST_TIME = :ft
                ORDER BY INGESTED_AT DESC
            """, {'fd': fcst_date, 'ft': fcst_time})
            
            rows = cursor.fetchall()
            for row in rows:
                result.append({'category': row[0], 'fcst_value': row[1]})
            
            return result
        finally:
            cursor.close()
            conn.close()
    except ConnectionError:
        return []


# --------------------------------------------------------------------------
# ⭐ 최적화 엔진용 데이터 조회 함수 ⭐
# --------------------------------------------------------------------------
def get_optimizer_input_data(run_id: str, vehicle_ids: List[str]) -> Dict:
    """
    최적화 계산에 필요한 모든 입력 데이터(차고지, 작업, 차량)를 DB에서 조회하여 구조화된 딕셔너리로 반환합니다.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    result = {"depot": None, "jobs": [], "vehicles": [], "run_date": None} 

    try:
        # 1. RUNS 테이블에서 차고지(Depot) 좌표 및 RUN_DATE 조회
        cursor.execute("""
            SELECT DEPOT_LAT, DEPOT_LON, RUN_DATE
            FROM RUNS
            WHERE RUN_ID = :run_id
        """, {'run_id': run_id})
        depot_row_tuple = cursor.fetchone()
        if depot_row_tuple and len(depot_row_tuple) == 3:
            result["depot"] = {"latitude": depot_row_tuple[0], "longitude": depot_row_tuple[1]}
            # RUN_DATE를 datetime 객체로 변환
            run_date = depot_row_tuple[2]
            if isinstance(run_date, dt.date) and not isinstance(run_date, dt.datetime):
                result["run_date"] = dt.datetime.combine(run_date, dt.time.min)
            else:
                 result["run_date"] = run_date
        else:
            raise ValueError(f"Run ID '{run_id}'를 찾을 수 없거나 데이터가 불완전합니다.")
        
        # 2. JOBS 테이블에서 해당 RUN_ID의 배송 작업 목록 조회
        cursor.execute("""
            SELECT JOB_ID, LATITUDE, LONGITUDE, DEMAND_KG, TW_START, TW_END
            FROM JOBS WHERE RUN_ID = :run_id ORDER BY JOB_ID
        """, {'run_id': run_id})
        job_columns = [d[0].lower() for d in cursor.description]
        job_rows_tuples = cursor.fetchall()
        result["jobs"] = [dict(zip(job_columns, row)) for row in job_rows_tuples]

        # 3. VEHICLES와 EMISSION_FACTORS 조인하여 차량 정보 조회
        bind_vars = {f"vid{i}": vid for i, vid in enumerate(vehicle_ids)}
        vehicle_query = f"""
            SELECT v.VEHICLE_ID, v.CAPACITY_KG, ef.CO2_GPKM, ef.IDLE_GPS
            FROM VEHICLES v JOIN EMISSION_FACTORS ef ON v.FACTOR_ID = ef.FACTOR_ID
            WHERE v.VEHICLE_ID IN ({','.join(':' + name for name in bind_vars)})
        """
        cursor.execute(vehicle_query, bind_vars)
        vehicle_columns = [d[0].lower() for d in cursor.description]
        vehicle_rows_tuples = cursor.fetchall()
        result["vehicles"] = [dict(zip(vehicle_columns, row)) for row in vehicle_rows_tuples]

        return result

    finally:
        cursor.close()
        conn.close()

# --------------------------------------------------------------------------
# 데이터 저장 함수들
# --------------------------------------------------------------------------
def save_optimization_results(run_id: str, summary_data: Dict, assignments_data: List[Dict]):
    """최적화 결과를 RUN_SUMMARY와 ASSIGNMENTS 테이블에 저장하고 RUNS 상태를 업데이트합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. RUN_SUMMARY 테이블에 결과 요약 저장 (기존 데이터 삭제 후 INSERT)
        cursor.execute("""
            DELETE FROM RUN_SUMMARY
            WHERE RUN_ID = :run_id AND ROUTE_OPTION_NAME = :route_option_name
        """, {'run_id': run_id, 'route_option_name': summary_data['route_option_name']})

        cursor.execute("""
            INSERT INTO RUN_SUMMARY (
                RUN_ID, ROUTE_OPTION_NAME, TOTAL_DISTANCE_KM, TOTAL_CO2_G, TOTAL_TIME_MIN
            ) VALUES (
                :run_id, :route_option_name, :total_distance_km, :total_co2_g, :total_time_min
            )
        """, summary_data)

        # 2. ASSIGNMENTS 테이블에 개별 경로 저장 (기존 데이터 삭제 후 INSERT MANY)
        cursor.execute("""
            DELETE FROM ASSIGNMENTS
            WHERE RUN_ID = :run_id AND ROUTE_OPTION_NAME = :route_option_name
        """, {'run_id': run_id, 'route_option_name': summary_data['route_option_name']})

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

        # 3. RUNS 테이블 상태 업데이트
        cursor.execute("""
            UPDATE RUNS SET OPTIMIZATION_STATUS = 'COMPLETED'
            WHERE RUN_ID = :run_id
        """, {'run_id': run_id})

        conn.commit()
        # print(f"✅ Run ID {run_id} ('{summary_data['route_option_name']}') 결과 DB 저장 완료.")

    except Exception as e:
        conn.rollback()
        print(f"❌ DB 저장 중 오류 발생: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

# --------------------------------------------------------------------------
# 🧪 OCI 연결 기반 테스트 코드 (main 블록) 
# --------------------------------------------------------------------------
if __name__ == '__main__':
    # 이 테스트는 config.py가 올바르게 설정되어 있고 DB가 실행 중임을 가정합니다.
    print("\n--- DB Handler 테스트 시작 ---")
    
    try:
        # 0. 연결 테스트
        conn_test_result = test_db_connection()
        print(f"✅ 0. OCI 연결 상태: {conn_test_result['status']}")

        if conn_test_result['status'] == 'success':
            # 1. SETTINGS 조회 테스트
            settings = get_settings_from_db()
            print(f"✅ 1. SETTINGS 조회 성공. 총 {len(settings)}개 항목.")
            
            # 2. RUN 데이터 조회 테스트 (DML 기반)
            test_run_id = 'RUN_20251015_001'
            test_vehicle_ids = ['부산82가1234', '인천88사5678']
            input_data = get_optimizer_input_data(test_run_id, test_vehicle_ids)
            print(f"✅ 2. 입력 데이터 조회 성공. Jobs: {len(input_data['jobs'])}개, Vehicles: {len(input_data['vehicles'])}개")

        else:
            print("❌ DB 연결 실패로 상세 조회를 건너뜝니다.")

    except ConnectionError:
        print("\n❌ DB 연결 실패: config.py의 OCI 설정 정보를 확인하세요.")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생 (DB 데이터/스키마 오류 가능성): {e}")