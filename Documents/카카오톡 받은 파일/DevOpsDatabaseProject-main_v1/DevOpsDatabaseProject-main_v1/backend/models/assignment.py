# backend/models/assignment.py
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Stop:
    order: int
    label: str
    lat: float
    lng: float


@dataclass
class AssignmentResult:
    vehicle_id: str
    vehicle_name: str
    distance_km: float
    emission_kg: float
    stops: List[Stop]
    polyline: List[Dict[str, float]]
