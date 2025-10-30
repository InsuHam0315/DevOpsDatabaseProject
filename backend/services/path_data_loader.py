# -*- coding: utf-8 -*-
import requests
from typing import Dict, List, Tuple, Any, Optional
import math
import requests.exceptions # 예외 처리 import 추가

# [필수 설정] config 파일에서 REST API 키를 가져옵니다.
try:
    import config
    # config.py에 정의된 KAKAOMAP_REST_API 변수를 사용합니다.
    KAKAO_API_KEY = config.KAKAOMAP_REST_API 
except ImportError:
    print("⚠️ WARNING: config.py를 찾을 수 없습니다. API 키를 설정해 주세요.")
    KAKAO_API_KEY = "YOUR_KAKAOMAP_REST_API" # 폴백 키

# --- Kakao API URL ---
KAKAO_DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"

# --------------------------------------------------------------------------
# 1. 단일 경로 조회 함수 (Single Route Lookup)
# --------------------------------------------------------------------------

def get_kakao_route(origin_coord: Tuple[float, float], destination_coord: Tuple[float, float], car_type: int = 6) -> Optional[Dict]:
    """
    카카오 모빌리티 길찾기 API를 호출하여 단일 경로 정보를 반환합니다.
    """
    if not KAKAO_API_KEY or KAKAO_API_KEY == "YOUR_KAKAOMAP_REST_API":
         return None

    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}",
        "Content-Type": "application/json"
    }

    # 카카오 API는 경도(lon), 위도(lat) 순서로 요구합니다.
    params = {
        "origin": f"{origin_coord[0]},{origin_coord[1]}",
        "destination": f"{destination_coord[0]},{destination_coord[1]}",
        "car_type": car_type, 
        "priority": "RECOMMEND",
        "road_details": "true"   # Link ID를 포함하는 상세 도로 정보를 요청
    }

    try:
        # [핵심 수정] 타임아웃을 20초로 증가시켜 연결 종료 오류 방지
        response = requests.get(KAKAO_DIRECTIONS_URL, headers=headers, params=params, timeout=20) 
        response.raise_for_status() # HTTP 오류 발생 시 예외 처리
        data = response.json()
        
        if not data.get('routes'):
            return None
            
        route = data['routes'][0]
        
        total_distance_km = route['summary']['distance'] / 1000.0
        total_time_sec = route['summary']['duration']

        # 경로 Segment 정보 추출 (Link ID와 기본 시간 포함)
        segments = []
        if total_distance_km > 0:
            for section in route['sections']:
                for road in section['roads']:
                    segment_distance = road['distance'] / 1000.0
                    
                    if route['summary']['distance'] > 0:
                        segment_time_sec = (road['distance'] / route['summary']['distance']) * total_time_sec
                    else:
                        segment_time_sec = 0.0

                    # Link ID가 없을 경우 None을 허용하도록 road.get() 사용
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
# 2. OR-Tools 행렬 생성 함수 (Matrix Generation)
# --------------------------------------------------------------------------

def create_kakao_route_matrices(locations: List[Dict]) -> Tuple[List[List[float]], List[List[float]], Dict[Tuple[int, int], List[Dict]]]:
    """
    모든 위치 쌍에 대해 카카오 API를 호출하여 거리 행렬, 시간 행렬 및 Segment 맵을 생성합니다.
    """
    num_locations = len(locations)
    distance_matrix_km = [[math.inf] * num_locations for _ in range(num_locations)]
    time_matrix_sec = [[math.inf] * num_locations for _ in range(num_locations)]
    segment_data_map = {} # 키: (i, j) 인덱스, 값: Segment 리스트
    
    CAR_TYPE = 6 # DML 기반 25톤 트랙터 차량 가정
    
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
            # else: 무한대(inf) 유지


    print(f"   ✅ 카카오 API 기반 경로 행렬 생성 완료 (총 {len(segment_data_map)}개 링크 데이터 포함).")
    return distance_matrix_km, time_matrix_sec, segment_data_map

if __name__ == '__main__':
    # 이 테스트는 config.py에 KAKAOMAP_REST_API가 설정되어 있어야 합니다.
    print("--- Path Data Loader 단독 테스트 시작 (실제 API 호출) ---")
    
    # DML: DEPOT (35.9400, 126.6800), JOB (35.0931, 128.8239)
    test_locations = [
        {'longitude': 126.6800, 'latitude': 35.9400}, # 0: 차고지 (군산)
        {'longitude': 128.8239, 'latitude': 35.0931}  # 1: 목적지 (부산신항)
    ]
    
    try:
        # 단일 호출 테스트 (0 -> 1)
        origin_coord = (test_locations[0]['longitude'], test_locations[0]['latitude'])
        dest_coord = (test_locations[1]['longitude'], test_locations[1]['latitude'])
        
        # 1. 단일 경로 정보 가져오기
        single_route = get_kakao_route(origin_coord, dest_coord)
        
        if single_route:
            print(f"\n[단일 경로 조회 성공]")
            print(f"  거리: {single_route['total_distance_km']:.2f} km")
            print(f"  시간: {single_route['total_time_sec']:.0f} sec")
            print(f"  Segment 개수: {len(single_route['segments'])}")
        else:
            print(f"\n[단일 경로 조회 실패] - API 키/서비스 활성화/네트워크 확인 필요.")

        # 2. 행렬 생성 테스트 (왕복)
        dist_mat, time_mat, seg_map = create_kakao_route_matrices(test_locations)
        
        print("\n[행렬 생성 결과]")
        print(f"  거리 [0->1]: {dist_mat[0][1]:.2f} km")
        print(f"  시간 [1->0]: {time_mat[1][0]:.0f} sec")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
