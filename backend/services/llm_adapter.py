from typing import Any, Dict, List

from services.db_handler import get_vehicle_ef_from_db


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _normalize_vehicle(v: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLMpart 예상 포맷을 수용해 표준 차량 스키마로 변환.
    우선순위 키: id/type/capacity_kg/count, ef_gpkm은 DB에서 타입으로 보강.
    """
    vehicle_type = v.get("type") or v.get("vehicle_type") or "GENERIC"
    ef_info = get_vehicle_ef_from_db(vehicle_type) or {}
    capacity_kg = v.get("capacity_kg")
    if capacity_kg is None and v.get("capacity") is not None:
        # capacity 톤 단위를 kg로 변환 가정
        capacity = _to_float(v.get("capacity"), 0.0)
        capacity_kg = capacity * 1000.0 if capacity > 0 else 0.0

    return {
        "id": v.get("id") or v.get("vehicle_id") or vehicle_type,
        "type": vehicle_type,
        "capacity_kg": _to_float(capacity_kg, 0.0),
        "count": int(v.get("count") or 1),
        "ef_gpkm": ef_info.get("ef_gpkm"),
        "idle_gps": ef_info.get("idle_gps"),
        "fuel": ef_info.get("fuel_type"),
    }


def _normalize_job(j: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLMpart 예상 포맷을 수용해 표준 작업 스키마로 변환.
    필드: sector_id/address/lat/lon/demand_kg/tw_start/tw_end/priority
    """
    lat = j.get("lat") if j.get("lat") is not None else j.get("latitude")
    lon = j.get("lon") if j.get("lon") is not None else j.get("longitude")
    weight = j.get("weight") if j.get("weight") is not None else j.get("demand_kg")
    demand_kg = _to_float(weight, 0.0)
    # weight가 톤 단위로 들어오면 간단히 톤→kg 변환 시도
    if demand_kg > 0 and demand_kg < 500:
        demand_kg = demand_kg * 1000.0

    sector_id = (
        j.get("sector_id")
        or j.get("to")
        or j.get("from")
        or j.get("address")
        or "SECTOR_UNKNOWN"
    )

    return {
        "sector_id": sector_id,
        "address": j.get("address") or f"{j.get('from', '')}→{j.get('to', '')}",
        "lat": _to_float(lat, 0.0),
        "lon": _to_float(lon, 0.0),
        "demand_kg": demand_kg,
        "tw_start": j.get("tw_start") or j.get("time_window_start") or "09:00",
        "tw_end": j.get("tw_end") or j.get("time_window_end") or "17:00",
        "priority": int(j.get("priority") or 2),
    }


def adapt_llmpart_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLMpart 브랜치의 JSON을 표준 구조로 변환.
    반환: {
      run_date: str, vehicles: List[dict], jobs: List[dict], depot_lat, depot_lon
    }
    """
    run_date = data.get("run_date") or data.get("date")
    depot_lat = _to_float(data.get("depot_lat") or data.get("origin_lat"), 0.0)
    depot_lon = _to_float(data.get("depot_lon") or data.get("origin_lon"), 0.0)

    vehicles_in = data.get("vehicles") or []
    jobs_in = data.get("jobs") or []

    vehicles = [_normalize_vehicle(v) for v in vehicles_in]
    jobs = [_normalize_job(j) for j in jobs_in]

    return {
        "run_date": run_date,
        "depot_lat": depot_lat,
        "depot_lon": depot_lon,
        "vehicles": vehicles,
        "jobs": jobs,
        "natural_input": data.get("natural_input"),
    }


