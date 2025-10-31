from typing import Dict, List, Any, Tuple
from math import radians, sin, cos, asin, sqrt


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return 0.0
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


def _co2_g(distance_km: float, ef_gpkm: float) -> float:
    if ef_gpkm is None:
        return 0.0
    return float(distance_km) * float(ef_gpkm)


def optimize_plan(
    run_id: str,
    run_date: str,
    vehicles: List[Dict[str, Any]],
    jobs: List[Dict[str, Any]],
    settings: Dict[str, float],
    depot: Tuple[float, float] = (0.0, 0.0),
) -> Dict[str, Any]:
    """
    간단한 MVP 최적화:
    - 모든 작업을 첫 번째 차량에 순서대로 할당
    - 인접 점 간 Haversine 거리 합산
    - CO2는 차량 타입별 고정 EF를 입력으로 받는다고 가정(없으면 0)
    반환 키:
      assignments: List[dict]
      summary: dict
      gradients: List[dict]
    """
    if not jobs:
        return {"assignments": [], "summary": {"route_option_name": "MVP", "total_distance_km": 0, "total_time_min": 0, "total_co2_g": 0, "saving_pct": 0}, "gradients": []}

    # 차량 선택 (MVP: 첫 차량)
    vehicle_id = vehicles[0].get("id") if vehicles else "VEHICLE_1"
    vehicle_type = vehicles[0].get("type") if vehicles else "GENERIC"
    ef_gpkm = vehicles[0].get("ef_gpkm") if vehicles else None

    # 경로 구성: depot -> job1 -> job2 -> ...
    prev_lat, prev_lon = depot
    total_distance = 0.0
    total_time_min = 0.0  # 속도 정보를 모르면 0
    total_co2_g = 0.0

    assignments: List[Dict[str, Any]] = []
    step_order = 1
    load_kg_running = 0.0

    for job in jobs:
        lat = float(job.get("latitude") or job.get("lat") or 0)
        lon = float(job.get("longitude") or job.get("lon") or 0)
        demand_kg = float(job.get("demand_kg") or job.get("weight") or 0) * (1000.0 if job.get("weight") and job.get("weight") < 500 else 1.0)

        dist = _haversine_km(prev_lat, prev_lon, lat, lon)
        total_distance += dist
        seg_co2 = _co2_g(dist, ef_gpkm)
        total_co2_g += seg_co2
        load_kg_running += demand_kg

        assignments.append({
            "run_id": run_id,
            "route_option_name": "MVP",
            "vehicle_id": vehicle_id,
            "step_order": step_order,
            "start_job_id": None,
            "end_job_id": job.get("job_id") or job.get("id"),
            "distance_km": round(dist, 3),
            "co2_g": round(seg_co2, 3),
            "load_kg": round(load_kg_running, 2),
            "time_min": 0.0,
            "avg_gradient_pct": 0.0,
            "congestion_factor": 1.0,
        })

        step_order += 1
        prev_lat, prev_lon = lat, lon

    summary = {
        "route_option_name": "MVP",
        "total_distance_km": round(total_distance, 3),
        "total_time_min": round(total_time_min, 2),
        "total_co2_g": round(total_co2_g, 3),
        "saving_pct": 0.0,
    }

    return {"assignments": assignments, "summary": summary, "gradients": []}


