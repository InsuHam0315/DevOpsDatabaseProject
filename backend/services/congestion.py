# services/congestion.py
# 혼잡도 계산
from typing import Dict, List
import math

def compute_tf_and_idle_f(segment_speeds: List[float], freeflow_speed: float, speed_idle_threshold: float) -> Dict[str,float]:
    """
    segment_speeds: 관측 구간 평균속도들(km/h) (세그먼트 가중평균을 계산해도 됨)
    freeflow_speed: 자유류 속도(km/h) (ORS 기반 또는 야간 P90)
    """
    v_obs = max(1e-3, sum(segment_speeds)/max(1, len(segment_speeds)))
    v_ff  = max(1e-3, freeflow_speed)
    tf = max(1.0, v_ff / v_obs)

    # 저속 구간 비율(가중 평균도 가능)
    cnt_low = sum(1 for v in segment_speeds if v <= speed_idle_threshold)
    idle_f = 0.0 if len(segment_speeds)==0 else cnt_low/len(segment_speeds)
    return {"tf": round(tf,4), "idle_f": round(idle_f,4)}
