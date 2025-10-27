# services/slope_from_dem.py
# DEM으로 각 세그먼트의 경사 채우기
from typing import List, Tuple
import numpy as np
import rasterio

def sample_elevations(coords: List[Tuple[float,float]], dem_path: str) -> List[float]:
    """
    coords: [ [lon,lat,(opt elev)], ... ]
    반환: 각 포인트의 DEM 표고(m)
    """
    lons = [c[0] for c in coords]; lats = [c[1] for c in coords]
    with rasterio.open(dem_path) as dem:
        xs, ys = dem.index(lons, lats)
        vals = dem.read(1)[ys, xs]
        # NoData 처리
        nodata = dem.nodata if dem.nodata is not None else -9999
        vals = np.where(np.isfinite(vals), vals, np.nan)
        vals = np.where(vals==nodata, np.nan, vals)
    # 선형 보간/최근접 대체
    # 간단히 NaN을 직전 유효값으로 대체(실전은 보간 권장)
    out=[]; last=None
    for v in vals:
        if np.isnan(v):
            out.append(last if last is not None else 0.0)
        else:
            out.append(float(v)); last=float(v)
    return out

def fill_segment_slopes_from_dem(segments, coords, dem_path: str, uphill_only=True):
    """
    segments: 1단계에서 만든 Segment 리스트
    coords  : 각 segment의 끝점을 공유하는 polyline 좌표
    """
    elevs = sample_elevations(coords, dem_path)
    # coords i -> i+1 이 segments[i]에 대응
    for i, seg in enumerate(segments):
        dz = elevs[i+1]-elevs[i]
        dist_m = seg.distance_km*1000
        if dist_m < 1e-3:
            slope = 0.0
        else:
            if uphill_only:
                dz = max(0.0, dz)
            slope = 100.0 * (dz/dist_m)
        seg.slope_pct = round(float(slope), 3)
    return segments
