from typing import Dict, List, Any


def explain_routes(assignments: List[Dict[str, Any]], settings: Dict[str, float]) -> Dict[str, Any]:
    """
    매우 단순한 기여도/설명 생성:
    - 현재는 거리 기반 비용만 존재한다고 가정하고 distance 기여도=1.0, 나머지 0.0
    - 향후 혼잡/경사/적재 가중치 반영 시 비율 계산 확장
    """
    total_distance = sum(a.get("distance_km", 0.0) or 0.0 for a in assignments)
    global_contrib = {
        "distance": 1.0 if total_distance > 0 else 0.0,
        "time": 0.0,
        "congestion": 0.0,
        "grade": 0.0,
        "load": 0.0,
    }

    per_vehicle: Dict[str, Dict[str, Any]] = {}
    for a in assignments:
        vid = a.get("vehicle_id", "unknown")
        per_vehicle.setdefault(vid, {"vehicle_id": vid, "distance_km": 0.0, "co2_kg": 0.0, "steps": 0})
        per_vehicle[vid]["distance_km"] += a.get("distance_km", 0.0) or 0.0
        per_vehicle[vid]["co2_kg"] += (a.get("co2_g", 0.0) or 0.0) / 1000.0
        per_vehicle[vid]["steps"] += 1

    per_step = []
    for a in assignments:
        per_step.append({
            "vehicle_id": a.get("vehicle_id"),
            "end_job_id": a.get("end_job_id"),
            "reason": "거리가 짧은 순으로 연결한 MVP 경로입니다.",
            "distance_km": a.get("distance_km", 0.0) or 0.0,
            "co2_kg": (a.get("co2_g", 0.0) or 0.0) / 1000.0,
        })

    return {
        "global": global_contrib,
        "per_vehicle": list(per_vehicle.values()),
        "per_step": per_step,
    }


