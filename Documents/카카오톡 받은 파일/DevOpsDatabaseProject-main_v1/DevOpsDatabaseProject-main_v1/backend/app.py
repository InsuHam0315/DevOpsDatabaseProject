from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import sys
from datetime import datetime, date

# --------------------------------------------------------------------------
# [Optional] LLM Blueprint loading
# --------------------------------------------------------------------------
try:
    # Expecting: backend/LLM/llm_call.py with Blueprint named llm_bp
    from LLM.llm_call import llm_bp
    LLM_BLUEPRINT_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] LLM blueprint not loaded: {e}")
    LLM_BLUEPRINT_AVAILABLE = False

# --------------------------------------------------------------------------
# Core services & optimizer engine imports
# --------------------------------------------------------------------------
try:
    from services.db_handler import (
        test_db_connection,
        get_dashboard_data,
        get_weekly_co2_trend,
        get_vehicle_distance_stats,
    )
    from optimizer.engine import run_optimization
except ImportError as e:
    print(
        f"[FATAL] Failed to import core services: {e}. "
        f"Make sure you are running from the 'backend' directory."
    )
    sys.exit(1)

# --------------------------------------------------------------------------
# Flask app setup
# --------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)


def _parse_iso_to_date(value: str) -> date:
    """Parse string into a date object (ISO 8601 or YYYY-MM-DD)."""
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%d").date()


def _extract_date_range_from_request():
    """Extract fromDate / toDate query parameters as date objects."""
    from_param = request.args.get("fromDate")
    to_param = request.args.get("toDate")
    if not from_param or not to_param:
        raise ValueError("Query parameters 'fromDate' and 'toDate' are required.")
    return _parse_iso_to_date(from_param), _parse_iso_to_date(to_param)


def _clean_optional_param(value: str):
    """Return None for empty/whitespace strings, otherwise trimmed value."""
    if not value:
        return None
    trimmed = value.strip()
    return trimmed or None


# Register LLM blueprint if available
if LLM_BLUEPRINT_AVAILABLE:
    app.register_blueprint(llm_bp)
    print("[INFO] LLM blueprint registered.")
else:
    print("[INFO] LLM blueprint not registered.")


# --------------------------------------------------------------------------
# Basic health-check endpoints
# --------------------------------------------------------------------------

@app.route("/")
def index():
    """Health check root endpoint."""
    return jsonify(
        {"status": "ok", "message": "Eco Logistics Optimizer API is running!"}
    )


@app.route("/test-db")
def db_connection_test_endpoint():
    """Simple DB connection test endpoint."""
    try:
        result = test_db_connection()
        status_code = 200 if result.get("status") == "success" else 500
        return jsonify(result), status_code
    except Exception as e:
        print(f"[ERROR] /test-db failed: {traceback.format_exc()}")
        return (
            jsonify(
                {
                    "status": "failed",
                    "error": f"DB connection test failed: {e}",
                }
            ),
            500,
        )


# --------------------------------------------------------------------------
# Optimization main API
# --------------------------------------------------------------------------

@app.route("/optimize", methods=["POST"])
def handle_optimization_request():
    """
    Handle optimization request from frontend and return summarized results.
    Expected JSON:
    {
        "run_id": "RUN_...",
        "vehicle_ids": ["TRK01", "TRK02", ...]
    }
    """
    print("[INFO] Received optimization request...")
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError("Request body must be a valid JSON object.")
        if "run_id" not in data or "vehicle_ids" not in data:
            raise ValueError("Fields 'run_id' and 'vehicle_ids' are required.")

        run_id = data["run_id"]
        vehicle_ids = data["vehicle_ids"]
        if not isinstance(vehicle_ids, list):
            raise ValueError("'vehicle_ids' must be a list.")

        print(f"[INFO] Run ID: {run_id}, Vehicles: {vehicle_ids}")

        # Call optimization engine (run_optimization defined in optimizer/engine.py)
        optimization_result = run_optimization(run_id, vehicle_ids)

        # Normalize response for frontend
        if isinstance(optimization_result, dict):
            status = optimization_result.get("status", "unknown")
            if status == "success":
                print("[INFO] Optimization successful, building response payload.")

                routes = []
                for r in optimization_result.get("results", []):
                    summary = r.get("summary") or {}
                    route_distance = float(summary.get("total_distance_km") or 0.0)
                    route_co2_g = float(summary.get("total_co2_g") or 0.0)
                    route_time = float(summary.get("total_time_min") or 0.0)

                    routes.append(
                        {
                            "route_name": r.get("route_name"),
                            "summary": summary,
                            "total_distance_km": route_distance,
                            "total_co2_g": route_co2_g,
                            "total_co2_kg": round(route_co2_g / 1000.0, 3),
                            "total_time_min": route_time,
                        }
                    )

                # Aggregate KPIs using normalized route entries
                total_distance = sum(route.get("total_distance_km", 0.0) for route in routes)
                total_co2_g = sum(route.get("total_co2_g", 0.0) for route in routes)
                total_time_min = sum(route.get("total_time_min", 0.0) for route in routes)

                comparison = optimization_result.get("comparison") or {}
                kpis = {
                    "total_distance_km": round(total_distance, 2),
                    "total_co2_kg": round(total_co2_g / 1000.0, 3),
                    "total_time_min": round(total_time_min, 2),
                    "saving_percent": comparison.get("co2_saving_pct", 0.0),
                }

                run_history_entry = {
                    "run_id": optimization_result.get("run_id"),
                    "timestamp": datetime.now().isoformat(),
                    "result_summary": routes[0] if routes else None,
                }

                return (
                    jsonify(
                        {
                            "status": "success",
                            "routes": routes,
                            "kpis": kpis,
                            "run_history_entry": run_history_entry,
                        }
                    ),
                    200,
                )

            elif status == "warning":
                print("[WARN] Optimization succeeded with warnings.")
                return jsonify(optimization_result), 206
            else:
                return jsonify(optimization_result), 500
        else:
            return (
                jsonify(
                    {
                        "status": "failed",
                        "message": "Unexpected optimization_result type.",
                    }
                ),
                500,
            )

    except ValueError as ve:
        return jsonify({"status": "failed", "message": f"Invalid request: {ve}"}), 400
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"[ERROR] Internal server error during /optimize:\n{error_details}")
        return (
            jsonify(
                {
                    "status": "failed",
                    "message": f"Internal server error during optimization: {e}",
                }
            ),
            500,
        )


# Alias endpoint (if frontend calls /api/optimize)
app.add_url_rule(
    "/api/optimize",
    endpoint="optimize_api",
    view_func=handle_optimization_request,
    methods=["POST"],
)


# --------------------------------------------------------------------------
# Dashboard data APIs
# --------------------------------------------------------------------------

@app.route("/api/dashboard", methods=["GET"])
def api_get_dashboard():
    try:
        data = get_dashboard_data()
        return jsonify(data), 200
    except Exception as e:
        print(f"[ERROR] /api/dashboard failed: {e}")
        return jsonify({"error": "Failed to load dashboard data"}), 500


@app.route("/api/dashboard/weekly-co2", methods=["GET"])
def api_dashboard_weekly_co2():
    try:
        from_date, to_date = _extract_date_range_from_request()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    vehicle_id = _clean_optional_param(request.args.get("vehicleId"))
    sector_id = _clean_optional_param(request.args.get("sectorId"))

    try:
        data = get_weekly_co2_trend(from_date, to_date, vehicle_id, sector_id)
        return jsonify(data), 200
    except Exception as e:
        print(f"[ERROR] /api/dashboard/weekly-co2 failed: {e}")
        return jsonify({"error": "Failed to load weekly CO2 data"}), 500


@app.route("/api/dashboard/vehicle-distance", methods=["GET"])
def api_dashboard_vehicle_distance():
    try:
        from_date, to_date = _extract_date_range_from_request()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    vehicle_id = _clean_optional_param(request.args.get("vehicleId"))
    sector_id = _clean_optional_param(request.args.get("sectorId"))

    try:
        data = get_vehicle_distance_stats(from_date, to_date, vehicle_id, sector_id)
        return jsonify(data), 200
    except Exception as e:
        print(f"[ERROR] /api/dashboard/vehicle-distance failed: {e}")
        return jsonify({"error": "Failed to load vehicle distance data"}), 500


# --------------------------------------------------------------------------
# Main entry
# --------------------------------------------------------------------------
if __name__ == "__main__":
    print("\nStarting Flask server...")
    app.run(debug=True, host="0.0.0.0", port=5000)
