from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import datetime as dt
import math

# [핵심] DB 직접 접근 함수를 모두 제거하고, 상수 로드 함수만 유지합니다.
from services.db_handler import (
    get_settings_from_db,
    get_congestion_factors_from_db, 
    get_weather_factors,            
)


# --- 데이터 구조 정의 (Data Classes) ---

@dataclass
class VehicleEF:
    """차량의 CO2 배출계수 및 용량 정보"""
    ef_gpkm: float      
    idle_gps: float     
    capacity_kg: float  

@dataclass
class Segment:
    """한 경로 구간(node to node)의 물리적 정보"""
    distance_km: float      
    link_id: Optional[str] = None 
    base_time_sec: float = 0.0 
    slope_pct: float = 0.0  
    load_kg: float = 0.0    

# --- DB 상수 로드 (engine.py에서 1회 호출용) ---
# 이 함수들은 DB에 접근하지만, OR-Tools Solve 전에 단 1회만 호출됩니다.

def get_settings() -> Dict[str, float]:
    """engine.py에서 1회 호출하여 모든 설정값을 가져옵니다."""
    rows_dict = get_settings_from_db() 
    s = {
        "alpha_load": 0.10, "beta_grade": 0.03, 
        "speed_idle_threshold": 15.0, "grade_cap": 0.30,
        "weather_penalty": 0.05, "max_free_flow_speed": 90.0,
        'ECO_CO2_WEIGHT': 0.8, 'ECO_TIME_WEIGHT': 0.2
    }
    for k, v in rows_dict.items():
        try: s[k] = float(v)
        except: continue
    return s

def get_congestion_factors(now: dt.datetime) -> Dict[str, float]:
    """engine.py에서 1회 호출하여 혼잡도 계수를 가져옵니다."""
    try:
        row = get_congestion_factors_from_db(now.hour)
        if row and len(row) >= 2:
            tf = float(row[0])
            idle_f = float(row[1])
            return {"tf": tf, "idle_f": idle_f}
    except Exception:
        pass 
    return {"tf": 1.0, "idle_f": 0.0}

def get_weather_penalty_value(start_time: dt.datetime, s: Dict[str, float]) -> float:
    """engine.py에서 1회 호출하여 날씨 페널티 값을 가져옵니다."""
    penalty = 1.0
    try:
        weather_data_list = get_weather_factors(start_time)
        for data in weather_data_list:
            category = data.get('category')
            value = data.get('fcst_value')
            try: fcst_value = float(value)
            except: continue
            if (category == 'RN1' and fcst_value > 0): penalty += s["weather_penalty"]
            elif (category == 'SN1' and fcst_value > 0): penalty += s["weather_penalty"] * 1.5
    except Exception:
        pass 
    return penalty


# --- 메인 CO2 계산 함수 (Callback에서 사용) ---

def co2_for_route(segments: List[Segment], v: VehicleEF, start_time: dt.datetime, 
                  congestion_factors: Dict[str, float], settings: Dict[str, float], 
                  weather_penalty_value: float) -> Dict[str, float]:
    """
    [핵심] 모든 필수 상수(혼잡도, 설정값, 날씨 페널티)를 인자로 받아, DB 접근 없이 계산합니다.
    """
    s = settings
    total_drive_co2 = 0.0
    total_idle_co2 = 0.0
    total_time_sec = 0.0
    
    cong = congestion_factors 
    weather_penalty = weather_penalty_value
    
    for seg in segments:
        if seg.distance_km <= 0: continue

        # 1. 속도 및 시간 계산 (Link ID 및 ITS DB 조회는 완전히 회피)
        base_avg_speed_kmh = (seg.distance_km / (seg.base_time_sec / 3600)) if seg.base_time_sec > 0 else s["max_free_flow_speed"]
        
        # 최종 예상 속도 및 시간 계산: Base 속도에 시간 혼잡 계수(tf) 역적용
        final_speed_kmh = base_avg_speed_kmh / cong["tf"]
        t_drive = (seg.distance_km / final_speed_kmh) * 3600 

        # 2. CO2 가중치 계산 (적재, 경사)
        load_ratio = 0.0 if v.capacity_kg <= 0 else min(1.0, seg.load_kg / v.capacity_kg)
        load_w = 1.0 + s["alpha_load"] * load_ratio
        grade_w = 1.0 + min(s["grade_cap"], s["beta_grade"] * max(0.0, seg.slope_pct))
        
        # 3. 주행 CO2 계산: 적재, 경사, 날씨 페널티 모두 반영
        drive_co2 = seg.distance_km * v.ef_gpkm * load_w * grade_w * weather_penalty
        total_drive_co2 += drive_co2

        # 4. 저속/공회전 CO2 계산: 저속 비율, 시간대별 IDLE_FACTOR 반영
        idle_factor = max(0.0, (s["speed_idle_threshold"] - final_speed_kmh) / s["speed_idle_threshold"])
        idle_co2 = t_drive * v.idle_gps * (idle_factor + cong["idle_f"])
        total_idle_co2 += idle_co2
        
        total_time_sec += t_drive

    return {
        "co2_drive_g": round(total_drive_co2, 2),
        "co2_idle_g": round(total_idle_co2, 2),
        "co2_total_g": round(total_drive_co2 + total_idle_co2, 2),
        "total_time_sec": round(total_time_sec, 2)
    }

# -------------------------------------------------------------------
# 🧪 테스트 코드 
# -------------------------------------------------------------------
if __name__ == '__main__':
    # NOTE: 이 테스트는 DB 연결에 의존하지만, OR-Tools 최적화 로직과 독립적으로 실행됩니다.
    import random
    
    print("--- CO2 계산기 단독 테스트 시작 ---")
    
    try:
        # 1. DB에서 상수 로드 (OR-Tools가 하는 것처럼)
        SETTINGS = get_settings()
        CONG_FACTORS = get_congestion_factors(dt.datetime(2025, 10, 30, 8, 0, 0)) # 8시 혼잡도
        WEATHER_PENALTY = get_weather_penalty_value(dt.datetime(2025, 10, 30, 8, 0, 0), SETTINGS)
        
        # 2. 테스트 입력 데이터 구성 (DML 기반)
        test_vehicle = VehicleEF(ef_gpkm=1250.5, idle_gps=11.2, capacity_kg=25000.0)
        test_segment = Segment(
            distance_km=10.0, 
            link_id='110000123', # 이 값은 이제 사용되지 않음 (DB 병목 제거)
            base_time_sec=720,   # 12분 (50 km/h)
            load_kg=22000.0,      
            slope_pct=0.5         
        )
        test_start_time = dt.datetime(2025, 10, 15, 8, 0, 0) # 아침 8시 (혼잡 시간)

        # 3. 계산 실행 (인자로 상수 전달)
        results = co2_for_route(segments=[test_segment], v=test_vehicle, start_time=test_start_time,
                                CONG_FACTORS=CONG_FACTORS, SETTINGS=SETTINGS, WEATHER_PENALTY_VALUE=WEATHER_PENALTY)
        
        # 4. 결과 분석
        print(f"\n[입력 조건] ---------------------------------")
        print(f"출발 시각: {test_start_time.strftime('%H:%M')}")
        print(f"혼잡 계수 (TF): {CONG_FACTORS['tf']:.2f}")
        print(f"날씨 페널티: {WEATHER_PENALTY:.2f}")
        
        print(f"\n[계산 결과] ---------------------------------")
        print(f"✅ 총 이동 시간: {results['total_time_sec'] / 60:.2f} 분")
        print(f"✅ 총합 CO2: {results['co2_total_g']:.2f} g")
        print("---------------------------------------------")

    except ConnectionError:
        print("\n❌ DB 연결 실패: config.py 설정을 확인하세요. (상수 로드 불가)")
    except Exception as e:
        print(f"\n❌ 테스트 중 예상치 못한 오류 발생: {e}")