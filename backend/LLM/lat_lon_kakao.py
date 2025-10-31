import config
import requests

def refine_address_for_search(raw_address: str) -> str:
    """
    LLM이 추출한 주소를 Kakao API에 최적화된 형식으로 정제
    """
    # 지역명 추가 (도시 + 구/동)
    address_mapping = {
        "대전 신세계백화점": "대전 서구 둔산로 123 신세계백화점",
        "서울 현대백화점": "서울 강남구 압구정로 343 현대백화점",
        "서울 롯데월드": "서울 송파구 올림픽로 240 롯데월드",
        "부산 해운대": "부산 해운대구 해운대해변로 264",
        # 추가 매핑 가능
    }
    
    # 매핑된 주소가 있으면 사용
    if raw_address in address_mapping:
        return address_mapping[raw_address]
    
    # 기본 정제 규칙
    refined = raw_address
    
    # "서울" → "서울특별시" 변환
    if refined.startswith("서울 "):
        refined = refined.replace("서울 ", "서울특별시 ")
    elif refined.startswith("부산 "):
        refined = refined.replace("부산 ", "부산광역시 ")
    elif refined.startswith("대전 "):
        refined = refined.replace("대전 ", "대전광역시 ")
    elif refined.startswith("대구 "):
        refined = refined.replace("대구 ", "대구광역시 ")
    elif refined.startswith("인천 "):
        refined = refined.replace("인천 ", "인천광역시 ")
    elif refined.startswith("광주 "):
        refined = refined.replace("광주 ", "광주광역시 ")
    elif refined.startswith("울산 "):
        refined = refined.replace("울산 ", "울산광역시 ")
    
    return refined

def get_coordinates_from_address_enhanced(address: str) -> dict:
    """
    개선된 좌표 검색 - 여러 전략 시도
    """
    if not address or not getattr(config, 'KAKAOMAP_REST_API', None):
        return {"lat": None, "lon": None, "error": "Kakao API 키 없음"}
    
    # 1. 주소 정제
    refined_address = refine_address_for_search(address)
    
    headers = {"Authorization": f"KakaoAK {config.KAKAOMAP_REST_API}"}
    
    # 2. 여러 검색 전략 시도
    search_strategies = [
        # 전략 1: 주소 검색 (가장 정확)
        {"url": "https://dapi.kakao.com/v2/local/search/address.json", "query": refined_address},
        # 전략 2: 키워드 검색 (장소명)
        {"url": "https://dapi.kakao.com/v2/local/search/keyword.json", "query": refined_address},
        # 전략 3: 원본 주소로 재시도
        {"url": "https://dapi.kakao.com/v2/local/search/keyword.json", "query": address},
    ]
    
    for i, strategy in enumerate(search_strategies):
        try:
            params = {"query": strategy['query'], "size": 1}
            response = requests.get(strategy['url'], headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("documents") and len(data["documents"]) > 0:
                result = data["documents"][0]
                coords = {
                    "lat": float(result["y"]),
                    "lon": float(result["x"]),
                    "address_name": result.get("address_name", result.get("place_name", address)),
                    "search_strategy": f"strategy_{i+1}"
                }
                return coords
                
        except Exception as e:
            print(f"  ⚠️ 전략 {i+1} 실패: {e}")
            continue
    
    # 모든 전략 실패
    print(f"❌ 모든 좌표 검색 전략 실패: '{address}'")
    return {"lat": None, "lon": None, "error": "모든 검색 전략 실패"}

def enhance_parsed_data_with_geocoding(parsed_data: dict) -> dict:
    """
    개선된 주소 좌표 변환 기능 - 이미 좌표가 있는 주소는 건너뛰기
    """
    if not parsed_data.get('runs'):
        return parsed_data
    
    geocoding_stats = {
        "total_depots": 0,
        "success_depots": 0,
        "total_jobs": 0,
        "success_jobs": 0,
        "failed_addresses": []
    }
    
    # 1. 출발지(depot) 좌표 변환
    runs = parsed_data.get('runs', [])
    for run in runs:
        # 1. 출발지(depot) 좌표 변환
        depot_address = run.get('depot_address')

        if run.get('depot_lat') is not None and run.get('depot_lon') is not None:
            print(f"  ✅ 출발지 좌표 이미 있음: {depot_address}")
            # continue (이 continue는 job 처리를 건너뛰므로 제거)
        elif depot_address:
            geocoding_stats["total_depots"] += 1
            coords = get_coordinates_from_address_enhanced(depot_address)
            
            if coords.get('lat') and coords.get('lon'):
                run['depot_lat'] = coords['lat']
                run['depot_lon'] = coords['lon']
                run['resolved_depot_address'] = coords.get('address_name', depot_address)
                geocoding_stats["success_depots"] += 1
            else:
                geocoding_stats["failed_addresses"].append(f"출발지: {depot_address}")
    
    # 2. 도착지(jobs) 좌표 변환
    jobs = run.get('jobs', []) # ⬅️ 해당 run에 속한 jobs를 가져옴
    for job in jobs:
        address = job.get('address')

        if job.get('lat') is not None and job.get('lon') is not None:
            print(f"  ✅ 도착지 좌표 이미 있음: {address}")
            continue
            
        if address:
            geocoding_stats["total_jobs"] += 1
                
            coords = get_coordinates_from_address_enhanced(address)
                
            if coords.get('lat') and coords.get('lon'):
                job['lat'] = coords['lat']
                job['lon'] = coords['lon']
                job['resolved_address'] = coords.get('address_name', address)
                geocoding_stats["success_jobs"] += 1
            else:
                geocoding_stats["failed_addresses"].append(f"도착지: {address}")
    
    parsed_data['_geocoding_stats'] = geocoding_stats
    
    return parsed_data