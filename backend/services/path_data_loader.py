# -*- coding: utf-8 -*-
import requests
from typing import Dict, List, Tuple, Any, Optional
import math
import requests.exceptions # 예외 처리 import 추가

# [필수 설정] config 파일에서 REST API 키를 가져옵니다.
try:
    import config
    # config.py에 정의된 KAKAOMAP_REST_API 변수를 가져와서 'KAKAO_API_KEY'에 저장합니다.
    KAKAO_API_KEY = config.KAKAOMAP_REST_API 
except ImportError:
    print("⚠️ WARNING: config.py를 찾을 수 없습니다. API 키를 설정해 주세요.")
    KAKAO_API_KEY = "YOUR_KAKAOMAP_REST_API" # 폴백 키

# --- Kakao API URL ---
KAKAO_DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"

# --------------------------------------------------------------------------
# 1. 단일 경로 조회 함수 (Single Route Lookup - VRP 행렬 생성용)
# --------------------------------------------------------------------------

def get_kakao_route(origin_coord: Tuple[float, float], destination_coord: Tuple[float, float], car_type: int = 6) -> Optional[Dict]:
    """
    카카오 모빌리티 길찾기 API를 호출하여 *단일 기본 경로* 정보를 반환합니다.
    (VRP 행렬 생성에 사용됨)
    """
    # ⭐ [오류 수정] 정의된 변수 'KAKAO_API_KEY'를 사용하도록 수정
    if not KAKAO_API_KEY or KAKAO_API_KEY == "YOUR_KAKAOMAP_REST_API":
        return None

    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}",
        "Content-Type": "application/json"
    }

    params = {
        "origin": f"{origin_coord[0]},{origin_coord[1]}",
        "destination": f"{destination_coord[0]},{destination_coord[1]}",
        "car_type": car_type, 
        "priority": "RECOMMEND",
        "road_details": "true"
    }

    try:
        response = requests.get(KAKAO_DIRECTIONS_URL, headers=headers, params=params, timeout=20) 
        response.raise_for_status() 
        data = response.json()
        
        if not data.get('routes'):
            return None
            
        route = data['routes'][0]
        
        total_distance_km = route['summary']['distance'] / 1000.0
        total_time_sec = route['summary']['duration']

        segments = []
        if total_distance_km > 0:
            for section in route['sections']:
                for road in section['roads']:
                    segment_distance = road['distance'] / 1000.0
                    
                    if route['summary']['distance'] > 0:
                        segment_time_sec = (road['distance'] / route['summary']['distance']) * total_time_sec
                    else:
                        segment_time_sec = 0.0

                    link_id_value = road.get('linkId') 
                    
                    segments.append({
                        "link_id": link_id_value, 
                        "distance_km": segment_distance,
                        "base_time_sec": segment_time_sec
                    })
        else:
            segments = []


        return {
            "total_distance_km": total_distance_km,
            "total_time_sec": total_time_sec,
            "segments": segments
        }

    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error (Network/Timeout) during Kakao API call: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ 카카오 API HTTP 오류 발생 ({e.response.status_code}): {e.response.text}")
    except Exception as e:
        print(f"❌ 카카오 API 호출 오류: {e}")
        
    return None

# --------------------------------------------------------------------------
# 2. [신규 추가] 대안 경로 조회 함수 (P2P 시나리오용)
# --------------------------------------------------------------------------

def get_kakao_route_alternatives(origin_coord: Tuple[float, float], destination_coord: Tuple[float, float], car_type: int = 6) -> Optional[List[Dict]]:
    """
    카카오 모빌리티 길찾기 API를 호출하여 *모든 대안 경로* 리스트를 반환합니다.
    (단일 작업(P2P) 시나리오에서 사용됨)
    """
    # ⭐ [오류 수정] 정의된 변수 'KAKAO_API_KEY'를 사용하도록 수정
    if not KAKAO_API_KEY or KAKAO_API_KEY == "YOUR_KAKAOMAP_REST_API":
        return None

    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}",
        "Content-Type": "application/json"
    }

    params = {
        "origin": f"{origin_coord[0]},{origin_coord[1]}",
        "destination": f"{destination_coord[0]},{destination_coord[1]}",
        "car_type": car_type, 
        "priority": "RECOMMEND",
        "alternatives": "true",   # [핵심] 대안 경로 모두 요청
        "road_details": "true"
    }
    
    all_routes = []

    try:
        response = requests.get(KAKAO_DIRECTIONS_URL, headers=headers, params=params, timeout=20) 
        response.raise_for_status()
        data = response.json()
        
        if not data.get('routes'):
            return None
        
        for route in data['routes']:
            total_distance_km = route['summary']['distance'] / 1000.0
            total_time_sec = route['summary']['duration']
            route_name = route['summary'].get('priority', 'UNKNOWN')

            segments = []
            if total_distance_km > 0:
                for section in route['sections']:
                    for road in section['roads']:
                        segment_distance = road['distance'] / 1000.0
                        
                        if route['summary']['distance'] > 0:
                            segment_time_sec = (road['distance'] / route['summary']['distance']) * total_time_sec
                        else:
                            segment_time_sec = 0.0

                        link_id_value = road.get('linkId') 
                        
                        segments.append({
                            "link_id": link_id_value, 
                            "distance_km": segment_distance,
                            "base_time_sec": segment_time_sec
                        })
            else:
                segments = []

            all_routes.append({
                "route_name": route_name,
                "total_distance_km": total_distance_km,
                "total_time_sec": total_time_sec,
                "segments": segments
            })
            
        return all_routes

    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error (Network/Timeout) during Kakao Alternatives call: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ 카카오 (Alternatives) API HTTP 오류 발생 ({e.response.status_code}): {e.response.text}")
    except Exception as e:
        print(f"❌ 카카오 (Alternatives) API 호출 오류: {e}")
        
    return None

# --------------------------------------------------------------------------
# 3. OR-Tools 행렬 생성 함수 (Matrix Generation - VRP 시나리오용)
# --------------------------------------------------------------------------

def create_kakao_route_matrices(locations: List[Dict]) -> Tuple[List[List[float]], List[List[float]], Dict[Tuple[int, int], List[Dict]]]:
    """
    모든 위치 쌍에 대해 카카오 API를 호출하여 거리 행렬, 시간 행렬 및 Segment 맵을 생성합니다.
    (get_kakao_route를 사용)
    """
    num_locations = len(locations)
    distance_matrix_km = [[math.inf] * num_locations for _ in range(num_locations)]
    time_matrix_sec = [[math.inf] * num_locations for _ in range(num_locations)]
    segment_data_map = {}
    
    CAR_TYPE = 6
    
    print("   🧭 카카오 모빌리티 API를 사용하여 경로 행렬 생성 시작...")
    
    for i in range(num_locations):
        for j in range(num_locations):
            if i == j:
                distance_matrix_km[i][j] = 0.0
                time_matrix_sec[i][j] = 0.0
                continue

            origin = (locations[i]['longitude'], locations[i]['latitude'])
            destination = (locations[j]['longitude'], locations[j]['latitude']) 

            route_info = get_kakao_route(origin, destination, CAR_TYPE)
            
            if route_info:
                distance_matrix_km[i][j] = route_info['total_distance_km']
                time_matrix_sec[i][j] = route_info['total_time_sec']
                segment_data_map[(i, j)] = route_info['segments']

    print(f" -------------------------------")
    return distance_matrix_km, time_matrix_sec, segment_data_map

# --------------------------------------------------------------------------
# 4. 테스트 코드
# --------------------------------------------------------------------------
if __name__ == '__main__':
    print("--- Path Data Loader 단독 테스트 시작 (실제 API 호출) ---")
    
    test_locations = [
        {'longitude': 126.6800, 'latitude': 35.9400}, # 0: 차고지 (군산)
        {'longitude': 128.8239, 'latitude': 35.0931}  # 1: 목적지 (부산신항)
    ]
    
    try:
        origin_coord = (test_locations[0]['longitude'], test_locations[0]['latitude'])
        dest_coord = (test_locations[1]['longitude'], test_locations[1]['latitude'])
        
        # 1. 단일 경로 정보 가져오기 (VRP용)
        single_route = get_kakao_route(origin_coord, dest_coord)
        
        if single_route:
            print(f"\n[1. VRP용 단일 경로 조회 성공]")
            print(f"  거리: {single_route['total_distance_km']:.2f} km")
            print(f"  시간: {single_route['total_time_sec']:.0f} sec")
        else:
            print(f"\n[1. VRP용 단일 경로 조회 실패]")

        # 2. P2P용 대안 경로 테스트
        alternative_routes = get_kakao_route_alternatives(origin_coord, dest_coord)
        
        if alternative_routes:
            print(f"\n[2. P2P용 대안 경로 조회 성공] (총 {len(alternative_routes)}개 경로)")
            for i, route in enumerate(alternative_routes):
                print(f" -------------------------------")

        else:
            print(f"\n[2. P2P용 대안 경로 조회 실패] - API 키/서비스 활성화/네트워크 확인 필요.")

        # 3. 행렬 생성 테스트 (VRP용)
        dist_mat, time_mat, seg_map = create_kakao_route_matrices(test_locations)
        
        print("\n[3. VRP용 행렬 생성 결과]")
        print(f"  거리 [0->1]: {dist_mat[0][1]:.2f} km")
        print(f"  시간 [1->0]: {time_mat[1][0]:.0f} sec")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")