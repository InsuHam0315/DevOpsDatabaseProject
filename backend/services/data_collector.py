# -*- coding: utf-8 -*-
import requests, csv, datetime as dt, json, time, math
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def _session(retry_total=3, backoff=1.5):
    s = requests.Session()
    s.headers.update({"User-Agent": "EcoLogistics/ITS-Weather (requests)"})
    r = Retry(total=retry_total, backoff_factor=backoff,
              status_forcelist=[500,502,503,504],
              allowed_methods=["GET"], raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=r))
    return s

# ----------------------------
# ITS: 교통 소통정보 → CSV 직행
# ----------------------------
def fetch_its_traffic(api_key: str,
                      bbox=(126.50, 126.95, 35.80, 36.10),
                      save_raw: bool = False) -> Path:
    """
    ITS 교통 소통정보를 받아 바로 CSV로 저장한다.
    - bbox: (minX, maxX, minY, maxY)
    - save_raw=True면 동일 디렉토리에 원본 JSON도 남김(디버깅용)
    """
    minX, maxX, minY, maxY = bbox
    base = "https://openapi.its.go.kr:9443/trafficInfo"
    params = {
        "apiKey": api_key,
        "type": "all",
        "drcType": "all",
        "minX": minX, "maxX": maxX,
        "minY": minY, "maxY": maxY,
        "getType": "json",
    }
    sess = _session()
    print("[ITS] 요청:", base, params)
    res = sess.get(base, params=params, timeout=30)
    res.raise_for_status()

    data = res.json()
    # 다양한 응답 스키마 대비 (키가 기관마다 다름)
    rows = (
        data.get("response", {}).get("data")
        or data.get("data")
        or data.get("items")
        or []
    )
    if not rows and isinstance(data, dict):
        # 백업 탐색: 딕셔너리 어디든 list[dict]를 찾아봄
        def find_list_of_dicts(obj):
            best = []
            def dfs(x):
                nonlocal best
                if isinstance(x, list) and x and isinstance(x[0], dict):
                    if len(x) > len(best): best = x
                elif isinstance(x, dict):
                    for v in x.values(): dfs(v)
            dfs(obj)
            return best
        rows = find_list_of_dicts(data)

    # CSV 저장
    out = DATA_DIR / f"its_traffic_{dt.datetime.now():%Y%m%d_%H%M}.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["linkId","roadName","speed_kmh","congestion_level","observed_at"])  # 표준화된 헤더
        for it in rows:
            w.writerow([
                it.get("linkId") or it.get("linkid"),
                it.get("roadName") or it.get("roadNm") or it.get("roadname"),
                it.get("speed") or it.get("spd"),
                it.get("congestion") or it.get("congestLevel") or it.get("congest"),
                it.get("createdDate") or it.get("time") or it.get("collectDate"),
            ])
    print(f"[ITS] ✅ {len(rows)}건 저장 → {out}")

    if save_raw:
        raw = DATA_DIR / f"its_raw_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
        raw.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"[ITS] (옵션) RAW 저장 → {raw}")

    return out

# ----------------------------
# Weather: 기상청 단기예보 → CSV 직행
# ----------------------------
def _session_retriable(total=6, backoff=1.3):
    s = requests.Session()
    s.headers.update({
        "User-Agent": "EcoLogistics/WeatherFetcher",
        "Accept-Encoding": "gzip, deflate"
    })
    r = Retry(
        total=total, connect=total, read=total,
        backoff_factor=backoff,
        status_forcelist=[500,502,503,504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=r))
    s.mount("http://",  HTTPAdapter(max_retries=r))
    return s

def _vilage_bases_to_try():
    # 현재 기준 발표시각부터 과거 3 슬롯까지 시도 (공공망 느릴 때 최신 슬롯이 자주 막힘)
    now = dt.datetime.now()
    slots = [2,5,8,11,14,17,20,23]
    # 가장 가까운 과거 슬롯 찾기
    h = max([s for s in slots if s <= now.hour] or [slots[-1]])
    # 후보 리스트 만들기: h, h-3, h-6, h-9 (필요시 하루 전으로 넘어감)
    candidates = []
    for k in [0, 3, 6, 9]:
        h2 = h - k
        d = now
        while h2 < 0:
            h2 += 24
            d = d - dt.timedelta(days=1)
        candidates.append( (d.strftime("%Y%m%d"), f"{h2:02d}00") )
    # 중복 제거
    seen = set(); uniq = []
    for bd, bt in candidates:
        key = (bd, bt)
        if key not in seen:
            seen.add(key); uniq.append(key)
    return uniq  # [(base_date, base_time), ...]

def fetch_weather(service_key: str, nx: int, ny: int, save_raw: bool=False) -> Path:
    url_https = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    url_http  = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"  # HTTPS 타임아웃 시 fallback
    sess = _session_retriable()

    def _call(_url, key, page_no, page_size, base_date, base_time):
        params = {
            "serviceKey": key,
            "pageNo": page_no,
            "numOfRows": page_size,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": nx, "ny": ny
        }
        # (연결 8초, 읽기 90초)로 여유
        return sess.get(_url, params=params, timeout=(8, 90), allow_redirects=True)

    # 키: raw → encoded 순서로 시도
    key_variants = [("raw", service_key), ("encoded", quote(service_key, safe=""))]
    # 페이지 크기를 작게 (공공망에 안전한 150~200 권장)
    PAGE = 200

    last_head = ""
    items_all = []
    used = None

    for base_date, base_time in _vilage_bases_to_try():
        for label, key in key_variants:
            for base_url in (url_https, url_http):  # https 먼저, 안 되면 http
                try:
                    # 1) totalCount 확인 (pageNo=1, numOfRows=1)
                    r0 = _call(base_url, key, 1, 1, base_date, base_time)
                except requests.exceptions.Timeout:
                    continue
                except requests.exceptions.RequestException:
                    continue

                if r0.status_code != 200:
                    last_head = r0.text[:200]
                    continue
                try:
                    d0 = r0.json()
                except ValueError:
                    last_head = r0.text[:200]
                    continue

                header = d0.get("response", {}).get("header", {})
                if header.get("resultCode") not in (None, "00"):
                    # 키 문제거나, 해당 슬롯 데이터 없음
                    last_head = json.dumps(header, ensure_ascii=False)
                    continue

                body = d0.get("response", {}).get("body", {}) or {}
                total = body.get("totalCount")
                if not isinstance(total, int):
                    # totalCount 없을 수 있음 → 그냥 1페이지부터 받아보자
                    total = PAGE

                total_pages = max(1, math.ceil(total / PAGE))
                items_all.clear()
                ok = True

                for p in range(1, total_pages+1):
                    # 지수 백오프(조금씩 간격 늘리며)
                    if p > 1:
                        time.sleep(min(2.0 * (p-1), 5.0))
                    try:
                        rp = _call(base_url, key, p, PAGE, base_date, base_time)
                    except requests.exceptions.Timeout:
                        ok = False; break
                    except requests.exceptions.RequestException:
                        ok = False; break

                    if rp.status_code != 200:
                        last_head = rp.text[:200]
                        ok = False; break

                    try:
                        dp = rp.json()
                    except ValueError:
                        last_head = rp.text[:200]
                        ok = False; break

                    h2 = dp.get("response", {}).get("header", {})
                    if h2.get("resultCode") not in (None, "00"):
                        last_head = json.dumps(h2, ensure_ascii=False)
                        ok = False; break

                    part = dp.get("response", {}).get("body", {}).get("items", {}).get("item", [])
                    items_all.extend(part)

                if ok and items_all:
                    used = (base_url, label, base_date, base_time)
                    # CSV 저장
                    out = DATA_DIR / f"weather_{base_date}_{nx}_{ny}.csv"
                    with out.open("w", newline="", encoding="utf-8-sig") as f:
                        w = csv.writer(f)
                        w.writerow(["baseDate","baseTime","category","fcstDate","fcstTime","fcstValue","nx","ny"])
                        for it in items_all:
                            w.writerow([
                                it.get("baseDate"), it.get("baseTime"),
                                it.get("category"),
                                it.get("fcstDate"), it.get("fcstTime"),
                                it.get("fcstValue"),
                                it.get("nx"), it.get("ny"),
                            ])
                    print(f"[Weather] ✅ {len(items_all)}건 저장 → {out}")
                    if save_raw:
                        raw = DATA_DIR / f"weather_raw_{base_date}_{base_time}.json"
                        raw.write_text(json.dumps({"items": items_all}, ensure_ascii=False), encoding="utf-8")
                        print(f"[Weather] (옵션) RAW 저장 → {raw}")
                    return out
                # 이 조합 실패 → 다음 키/슬롯/스킴 시도
    raise RuntimeError("Weather API 페이지네이션/재시도 후에도 실패. 마지막 응답 일부: " + last_head)