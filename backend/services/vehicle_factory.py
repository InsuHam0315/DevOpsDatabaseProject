# services/vehicle_factory.py
# 공회전 배출계수 계산
from typing import Dict
from models import VehicleEF

def make_vehicle_from_settings(vehicle_type: str, settings: Dict[str,float], fixed_ef_gpkm: float, capacity_kg: float) -> VehicleEF:
    # idle g/s 계산
    kg_per_gal = float(settings.get("diesel_kgCO2_per_gal", 10.19))
    gal_per_hr = float(settings.get("idle_fuel_gal_per_hr", 0.8))
    idle_gps = (kg_per_gal*1000.0*gal_per_hr)/3600.0  # g/s

    return VehicleEF(
        ef_gpkm=fixed_ef_gpkm,
        idle_gps=idle_gps,
        capacity_kg=capacity_kg
    )
