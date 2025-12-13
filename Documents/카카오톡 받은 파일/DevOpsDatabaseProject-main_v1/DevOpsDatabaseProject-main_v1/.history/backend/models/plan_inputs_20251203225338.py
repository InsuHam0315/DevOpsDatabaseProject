# backend/models/plan_inputs.py
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobInput:
    address: str
    lat: float
    lon: float
    demand_kg: float
    tw_start: Optional[str] = None
    tw_end: Optional[str] = None


@dataclass
class RunInput:
    run_date: str                 # ISO date string
    vehicle_model: str            # 차량 식별자(번호판 등)
    depot_address: str
    depot_lat: float
    depot_lon: float
    jobs: List[JobInput] = field(default_factory=list)


@dataclass
class PlanRequest:
    runs: List[RunInput]
