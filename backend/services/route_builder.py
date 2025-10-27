# services/route_builder.py
# ORS로 "경로 -> 세그먼트(distance, base_time)"
import os, math, requests
from dataclasses import dataclass
from typing import List, Dict, Tuple
from models import Segment  # 네가 가진 dataclass
ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"

def haversine_km(a: Tuple[float,float], b: Tuple[float,float]) -> float:
    import math
    R=6371.0
    lat1, lon1 = math.radians(a[1]), math.radians(a[0])
    lat2, lon2 = math.radians(b[1]), math.radians(b[0])
    dlat=lat2-lat1; dlon=lon2-lon1
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(h))

def build_segments_with_ors(origin: Tuple[float,float], dest: Tuple[float,float], load_plan_kg: float) -> List[Segment]:
    """
    origin=(lon,lat), dest=(lon,lat)
    단순 버전: ORS geometry 좌표 간선별 거리 비례로 시간을 배분하여 세그먼트 생성
    """
    headers = {"Authorization": os.environ["ORS_API_KEY"], "Content-Type":"application/json"}
    body = {"coordinates":[[origin[0], origin[1]],[dest[0], dest[1]]], "instructions": False, "elevation": True}
    r = requests.post(ORS_URL, json=body, headers=headers, timeout=30)
    r.raise_for_status()
    feat = r.json()["features"][0]
    coords = feat["geometry"]["coordinates"]  # [lon,lat,(elev?)]
    total_sec = feat["properties"]["summary"]["duration"]  # 초
    # 각 링크 길이
    seg_dists = []
    for i in range(len(coords)-1):
        a=(coords[i][0], coords[i][1]); b=(coords[i+1][0], coords[i+1][1])
        seg_dists.append(haversine_km(a,b))
    total_km = sum(seg_dists) or 1e-9
    # 거리비로 시간 배분
    segs: List[Segment] = []
    for d_km in seg_dists:
        t = (d_km/total_km)*total_sec
        segs.append(Segment(distance_km=d_km, base_time_sec=t, slope_pct=0.0, load_kg=load_plan_kg))
    return segs, coords  # coords는 이후 경사계산에서 활용
