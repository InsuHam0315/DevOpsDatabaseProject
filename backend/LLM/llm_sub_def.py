from services.db_handler import get_db_connection # 함수 이름 변경 및 추가


def get_sector_coordinates(SECTOR_NAME: str) -> dict:
    """SECTOR 테이블에서 sector_name에 해당하는 좌표를 조회 - 디버깅 강화"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cleaned_name = SECTOR_NAME.strip()
        #print(f"🔍 SECTOR 테이블 조회: '{cleaned_name}'")
        
        # 1. 먼저 SECTOR 테이블에 어떤 데이터가 있는지 전체 조회
        cursor.execute("SELECT SECTOR_NAME, LATITUDE, LONGITUDE FROM SECTORS")
        all_sectors = cursor.fetchall()
        #print(f"📋 SECTOR 테이블 전체 데이터: {all_sectors}")
        
        # 2. 정확한 매칭 시도
        cursor.execute("""
            SELECT SECTOR_ID, LATITUDE, LONGITUDE FROM SECTORS WHERE SECTOR_NAME = :SECTOR_NAME
        """, {'SECTOR_NAME': cleaned_name})
        
        result = cursor.fetchone()
        if result:
            #print(f"✅ SECTOR 테이블에서 찾음: '{cleaned_name}'")
            return {'SECTOR_ID': result[0], 'LATITUDE': result[1], 'LONGITUDE': result[2]}
        else:
            #print(f"❌ SECTOR 테이블에서 찾지 못함: '{cleaned_name}'")
            
            # 3. 유사한 데이터가 있는지 확인
            cursor.execute("""
                SELECT SECTOR_NAME, LATITUDE, LONGITUDE FROM SECTORS
                WHERE SECTOR_NAME LIKE '%' || :partial_name || '%'
            """, {'partial_name': cleaned_name})
            
            similar_results = cursor.fetchall()
            if similar_results:
                print(f"🔍 유사한 SECTOR 데이터: {similar_results}")
                
            return None
    except Exception as e:
        print(f"SECTOR 테이블 조회 오류: {e}")
        return None
    finally:
        if conn:
            conn.close()

def preprocess_with_sector_data(parsed_data: dict) -> dict:
    """SECTOR 테이블을 참조하여 좌표를 미리 채움"""
    if not parsed_data.get('runs'):
        return parsed_data
    
    # 출발지(runs) 좌표 채우기
    for run in parsed_data.get('runs', []):
        # 1. 출발지(runs) 좌표 채우기
        depot_address = run.get('depot_address')
        if depot_address:
            coords = get_sector_coordinates(depot_address)
            if coords:
                run['depot_lat'] = coords['LATITUDE']
                run['depot_lon'] = coords['LONGITUDE']
                print(f"✅ SECTOR에서 출발지 좌표 채움: {depot_address}")
            else:
                print(f"ℹ️  SECTOR에 없는 출발지: {depot_address}")
    
    # 도착지(jobs) 좌표 채우기 - 주소 그대로 SECTOR 테이블에서 검색
        for job in run.get('jobs', []):
                address = job.get('address')
                if address:
                    coords = get_sector_coordinates(address)
                    if coords:
                        job['lat'] = coords['LATITUDE']
                        job['lon'] = coords['LONGITUDE']
                        job['sector_id'] = coords['SECTOR_ID']
                        print(f"✅ SECTOR에서 도착지 좌표 채움: {address}")
                    else:
                        print(f"ℹ️  SECTOR에 없는 도착지: {address}")
    
    return parsed_data
#-------------------------------------------------------------------------------------------------
