from dataclasses import dataclass
from typing import List, Dict
import datetime as dt

# [수정사항 1] 'from db import execute' 대신, 우리 DB 전문가를 불러옵니다.
from services.db_handler import get_congestion_factors_from_db, get_settings_from_db

# --- 데이터 구조 정의 (Data Classes) ---

@dataclass
class VehicleEF:
    """차량의 CO2 배출계수 및 용량 정보"""
    ef_gpkm: float      # 주행 배출계수 (g/km)
    idle_gps: float     # 공회전 배출계수 (g/sec)
    capacity_kg: float  # 최대 적재용량 (kg)

@dataclass
class Segment:
    """한 경로 구간(node to node)의 물리적 정보"""
    distance_km: float      # 구간 거리 (km)
    base_time_sec: float    # 기본 이동 시간 (초)
    slope_pct: float = 0.0  # 도로 경사도 (%)
    load_kg: float = 0.0    # 해당 구간에서의 적재량 (kg)


# --- DB 의존 함수들 ---

def get_congestion_factors(now: dt.datetime) -> Dict[str, float]:
    """현재 시간의 혼잡도 계수를 DB에서 가져옵니다."""
    # [수정사항 2] DB 쿼리를 직접 실행하는 대신, db_handler의 함수를 호출합니다.
    row = get_congestion_factors_from_db(now.hour)
    
    # DB에 해당 시간의 데이터가 없을 경우 기본값(1.0)을 사용합니다.
    if not row:
        return {"tf": 1.0, "idle_f": 0.0}
    
    tf, idle_f = map(float, row)
    return {"tf": tf, "idle_f": idle_f}

def get_settings() -> Dict[str, float]:
    """계산에 필요한 가중치들을 SETTINGS 테이블에서 가져옵니다."""
    # [수정사항 3] DB 쿼리를 직접 실행하는 대신, db_handler의 함수를 호출합니다.
    rows = get_settings_from_db()
    
    # DB에 값이 없을 경우를 대비한 기본값 설정
    s = {
        "alpha_load": 0.10,         # 적재율 100%일 때 추가 배출률 (+10%)
        "beta_grade": 0.03,         # 경사 1% 당 추가 배출률 (+3%)
        "speed_idle_threshold": 15, # 이 속도(km/h) 이하일 때 저속/공회전으로 간주
        "grade_cap": 0.30           # 경사로 인한 추가 배출의 최대 한도 (+30%)
    }
    
    # DB에서 가져온 값으로 기본값을 덮어씁니다.
    for k, v in rows or []:
        try:
            s[k] = float(v)
        except (ValueError, TypeError):
            s[k] = v
    return s


# --- 메인 계산 함수 (이 함수는 수정할 필요가 없습니다) ---

def co2_for_route(segments: List[Segment], v: VehicleEF) -> Dict[str, float]:
    """경로(segment 리스트)와 차량 정보를 받아 총 CO2 배출량을 계산합니다."""
    now = dt.datetime.now()
    cong = get_congestion_factors(now)
    s = get_settings()

    total_drive = 0.0
    total_idle = 0.0

    for seg in segments:
        # 1) 시간 보정 (교통 혼잡도 반영)
        t = seg.base_time_sec * cong["tf"]

        # 2) 적재율 가중치 계산
        load_ratio = 0.0 if v.capacity_kg <= 0 else min(1.0, seg.load_kg / v.capacity_kg)
        load_w = 1.0 + s["alpha_load"] * load_ratio

        # 3) 경사 가중치 계산
        grade_w = 1.0 + min(s["grade_cap"], s["beta_grade"] * max(0.0, seg.slope_pct))

        # 4) 주행 CO2 계산
        drive = seg.distance_km * v.ef_gpkm * load_w * grade_w
        total_drive += drive

        # 5) 저속/공회전 CO2 계산
        avg_speed = (seg.distance_km / (t / 3600)) if t > 0 else 999
        idle_factor = max(0.0, (s["speed_idle_threshold"] - avg_speed) / s["speed_idle_threshold"])
        idle = t * v.idle_gps * (idle_factor + cong["idle_f"])
        total_idle += idle

    return {
        "co2_drive_g": round(total_drive, 2),
        "co2_idle_g": round(total_idle, 2),
        "co2_total_g": round(total_drive + total_idle, 2)
    }