# services/emission_factor.py
# 속도기반 배출계수 함수 
from typing import Dict

def ef_gpkm_from_speed(speed_kmh: float, vehicle_type: str, settings: Dict[str, float]) -> float:
    """
    speed_kmh: 세그 평균속도
    vehicle_type: "truck" 등 (키 접두어 결정)
    settings: get_settings() 결과
    """
    v = max(0.0, speed_kmh)
    prefix = f"nier_coef_{vehicle_type}_"
    a = float(settings.get(prefix+"a", 0.0))
    b = float(settings.get(prefix+"b", 0.0))
    c = float(settings.get(prefix+"c", 0.0))
    ef = a + b*v + c*(v**2)  # g/km
    return max(0.0, float(ef))
