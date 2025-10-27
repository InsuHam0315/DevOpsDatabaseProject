# services/call_llm.py
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import json
from datetime import datetime
import requests

import config
from .db_handler import (
    test_db_connection, save_run, save_job, save_llm_analysis_summary
)

# Google AI Studio 직결 엔드포인트 (v1 + latest)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"


llm_bp = Blueprint("llm", __name__, url_prefix="/api")

# ── 공용 LLM 호출 함수 ─────────────────────────────────────────────
def call_llm(prompt: str) -> str:
    """
    Google AI Studio(Gemini) 직결 버전.
    - 헤더: x-goog-api-key
    - 바디: contents 구조
    """
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": config.GOOGLE_API_KEY,  # .env에서 로드됨
    }
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        resp = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # 안전하게 추출 (키 누락 대비)
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("❌ Gemini API 호출 실패:", e)
        # 디버깅용 원본 응답 출력
        try:
            print("Response:", resp.status_code, resp.text)  # resp가 없으면 except로 넘어감
        except:
            pass
        raise

# ── Health ────────────────────────────────────────────────────────
@llm_bp.get("/health")
def health():
    return jsonify(status="ok", scope="llm")

# ── API #1: 자연어 → JSON 파싱 ─────────────────────────────────────
@llm_bp.post("/parse-natural-language")
@cross_origin()
def parse_natural_language():
    data = request.get_json(silent=True) or {}
    user_input = data.get("natural_input")
    if not user_input:
        return jsonify({"error": "natural_input is required"}), 400

    try:
        current_date_str = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
        당신은 물류 계획 전문가의 자연어 요청을 VRP용 JSON 데이터로 변환하는 AI입니다.
        현재 날짜는 **{current_date_str}** 입니다. "오늘/내일/모레" 등은 YYYY-MM-DD로 변환하세요.

        아래 구조의 JSON만 출력하세요(설명 금지).
        - run_date: "YYYY-MM-DD"
        - vehicles: ["차량ID", ...]
        - jobs: [
            {{"sector_id":"섹터ID","demand_kg":숫자,"tw_start":"HH24:MI","tw_end":"HH24:MI",
              "priority":숫자,"lat":숫자 또는 null,"lon":숫자 또는 null}}
          ]
        - priority는 1,2,3,4 중 하나. 0 금지.

        사용자 요청: "{user_input}"
        """
        llm_resp = call_llm(prompt)

        # 코드블록 또는 순수 JSON 대응
        if '```json' in llm_resp:
            json_str = llm_resp.split('```json')[1].split('```')[0].strip()
        elif '{' in llm_resp and '}' in llm_resp:
            json_str = llm_resp[llm_resp.find('{'): llm_resp.rfind('}') + 1]
        else:
            raise ValueError("LLM 응답에서 JSON을 찾을 수 없습니다.")

        parsed = json.loads(json_str)
        if not all(k in parsed for k in ("run_date", "vehicles", "jobs")):
            raise ValueError("필수 키(run_date, vehicles, jobs) 누락")

        return jsonify(parsed), 200

    except ValueError as ve:
        return jsonify({"error": "LLM 응답 처리 실패", "details": str(ve)}), 500
    except requests.exceptions.RequestException as re:
        return jsonify({"error": "LLM API 호출 실패", "details": str(re)}), 502
    except Exception as e:
        print("예상치 못한 오류:", e)
        return jsonify({"error": "내부 서버 오류", "details": str(e)}), 500

# ── API #2: 계획 저장 + LLM 분석 ───────────────────────────────────
@llm_bp.post("/save-plan-and-analyze")
@cross_origin()
def save_plan_and_analyze():
    plan_data = request.get_json(silent=True) or {}
    if not plan_data:
        return jsonify({"error": "계획 데이터(JSON)가 필요합니다."}), 400

    conn = None
    try:
        conn = test_db_connection()
        cursor = conn.cursor()

        run_date_str = plan_data.get('run_date')
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        run_params = {
            "run_id": run_id,
            "run_date_str": run_date_str,
            "depot_lat": plan_data.get('depot_lat', 35.940000),
            "depot_lon": plan_data.get('depot_lon', 126.680000),
            "natural_language_input": plan_data.get('natural_input'),
            "optimization_status": "ANALYZING",
        }
        save_run(cursor, run_params)

        jobs_data = plan_data.get('jobs', [])
        saved_job_ids = []
        for job in jobs_data:
            job_params = {
                "run_id": run_id,
                "sector_id": job.get('sector_id'),
                "address": job.get('address', f"{job.get('sector_id')} 주소"),
                "latitude": job.get('lat') if job.get('lat') is not None else 0,
                "longitude": job.get('lon') if job.get('lon') is not None else 0,
                "demand_kg": job.get('demand_kg'),
                "tw_start_str": job.get('tw_start'),
                "tw_end_str": job.get('tw_end'),
                "priority": job.get('priority', 0),
                "run_date_str": run_date_str,
            }
            job_id = save_job(cursor, job_params)
            saved_job_ids.append(job_id)

        conn.commit()

        vehicle_count = len(plan_data.get('vehicles', []))
        job_count = len(jobs_data)
        total_demand = sum(job.get('demand_kg', 0) for job in jobs_data)

        llm_prompt = f"""
        [계획 ID: {run_id}]
        - 날짜: {run_date_str}
        - 차량 수: {vehicle_count}
        - 작업 수: {job_count}
        - 총 물량: {total_demand} kg
        작업 일부:
        {json.dumps(jobs_data[:3], ensure_ascii=False, indent=2)}

        아래 세 가지만 간결하게(각 2줄 이내):
        1) 차량 구성과 물량의 적절성
        2) 시간제약(TW)이 미치는 영향
        3) 친환경 측면(전기/하이브리드 고려)
        """
        try:
            llm_explanation = call_llm(llm_prompt)
        except Exception as e:
            print("LLM 분석 실패:", e)
            llm_explanation = "LLM 분석을 생성하는 데 실패했습니다."

        summary_params = {
            "run_id": run_id,
            "llm_explanation": llm_explanation,
            "total_distance_km": 0,
            "total_co2_g": 0,
            "total_time_min": 0,
            "saving_pct": 0,
        }
        save_llm_analysis_summary(cursor, summary_params)

        cursor.execute(
            "UPDATE runs SET optimization_status = 'ANALYZED' WHERE run_id = :run_id",
            {"run_id": run_id},
        )
        conn.commit()

        return jsonify({"message": "계획 저장 및 LLM 분석 완료", "run_id": run_id}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print("계획 저장/분석 중 오류:", e)
        return jsonify({"error": "내부 서버 오류", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

# ── API #3: 결과 조회 ──────────────────────────────────────────────
@llm_bp.get("/get-results/<string:run_id>")
def get_results(run_id):
    conn = None
    try:
        conn = test_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT total_distance_km, total_co2_g, total_time_min, saving_pct, llm_explanation
            FROM run_summary WHERE run_id = :run_id
        """, {"run_id": run_id})
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": f"Run '{run_id}'에 대한 분석 정보 없음"}), 404

        cols = [c[0].lower() for c in cursor.description]
        summary = dict(zip(cols, row))

        exp = summary.get("llm_explanation")
        if hasattr(exp, "read"):
            exp = exp.read()

        cursor.execute("""
            SELECT vehicle_id, step_order, start_job_id, end_job_id, distance_km, co2_g, time_min
            FROM assignments
            WHERE run_id = :run_id
            ORDER BY vehicle_id, step_order
        """, {"run_id": run_id})
        a_rows = cursor.fetchall()
        a_cols = [c[0].lower() for c in cursor.description]
        assigns = [dict(zip(a_cols, r)) for r in a_rows]

        routes = group_assignments_by_vehicle(assigns)
        res = {
            "run_id": run_id,
            "kpis": {
                "total_distance_km": summary.get("total_distance_km", 0) or 0,
                "total_co2_kg": (summary.get("total_co2_g", 0) or 0) / 1000.0,
                "total_time_min": summary.get("total_time_min", 0) or 0,
                "saving_percent": summary.get("saving_pct", 0) or 0,
            },
            "llm_explanation": exp or "",
            "routes": routes,
        }
        return jsonify(res), 200

    except Exception as e:
        print("결과 조회 오류:", e)
        return jsonify({"error": "내부 서버 오류", "details": str(e)}), 500
    finally:
        if conn:
            try: conn.close()
            except: pass

def group_assignments_by_vehicle(assignments_data: list) -> list:
    routes = {}
    for a in assignments_data:
        vid = a.get("vehicle_id")
        if not vid:
            continue
        routes.setdefault(vid, {
            "vehicle_id": vid, "steps": [],
            "total_distance_km": 0.0, "total_co2_kg": 0.0,
            "total_time_min": 0, "polyline": []
        })
        step = {
            "sector_id": f"JOB_{a.get('end_job_id')}",
            "arrival_time": "미정",
            "departure_time": "미정",
            "distance_km": a.get("distance_km", 0.0) or 0.0,
            "co2_kg": (a.get("co2_g", 0.0) or 0.0) / 1000.0,
        }
        r = routes[vid]
        r["steps"].append(step)
        r["total_distance_km"] += step["distance_km"]
        r["total_co2_kg"] += step["co2_kg"]
        r["total_time_min"] += a.get("time_min", 0) or 0

    for r in routes.values():
        r["total_distance_km"] = round(r["total_distance_km"], 2)
        r["total_co2_kg"] = round(r["total_co2_kg"], 3)
    return list(routes.values())
