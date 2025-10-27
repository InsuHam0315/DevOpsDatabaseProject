# backend/optimizer/run_pipeline.py
import datetime as dt
from services.db_handler import get_settings_from_db
from services.route_builder import build_segments_with_ors
from services.slope_from_dem import fill_segment_slopes_from_dem
from services.congestion import compute_tf_and_idle_f
from services.emission_factor import ef_gpkm_from_speed
from services.vehicle_factory import make_vehicle_from_settings
from optimizer.co2_calculator import co2_for_route
from models import Segment, VehicleEF

def run_co2_pipeline(origin, dest, dem_path, vehicle_type="truck",
                     fixed_ef_gpkm=1200.0, capacity_kg=25000, load_kg=20000):
    """
    전체 CO₂ 계산 파이프라인:
    1. ORS로 경로 → 세그먼트 생성
    2. DEM으로 경사 채우기
    3. 혼잡도 계산 (관측속도 기반)
    4. 차량 생성 및 배출계수 계산
    5. CO₂ 계산기 호출
    """
    # 1) SETTINGS
    rows = get_settings_from_db() or []
    s = {k: float(v) if str(v).replace('.', '', 1).isdigit() else v for k, v in rows}
    s.setdefault("ef_mode", "speed_based_nier")
    s.setdefault("freeflow_speed_strategy", "ORS")
    s.setdefault("speed_idle_threshold", 15)

    # 2) 경로 세그먼트 생성
    segments, coords = build_segments_with_ors(origin, dest, load_plan_kg=load_kg)

    # 3) DEM으로 경사 채우기
    segments = fill_segment_slopes_from_dem(segments, coords, dem_path, uphill_only=True)

    # 4) 혼잡도 계산 (실측속도 API 연동 가능)
    total_km = sum(sg.distance_km for sg in segments)
    total_h = sum(sg.base_time_sec for sg in segments) / 3600.0
    v_ff = max(1.0, total_km / total_h)
    observed_speeds = [v_ff * 0.7 for _ in segments]  # 임시로 70% 가정
    cong = compute_tf_and_idle_f(observed_speeds, v_ff, float(s["speed_idle_threshold"]))

    # 5) Vehicle 생성
    v = make_vehicle_from_settings(vehicle_type, s, fixed_ef_gpkm=fixed_ef_gpkm, capacity_kg=capacity_kg)

    # 6) CO₂ 계산 실행
    result = co2_for_route(segments, v)
    return result
