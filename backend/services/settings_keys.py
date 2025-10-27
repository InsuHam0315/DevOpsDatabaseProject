# services/settings_keys.py
# SETTINGS
DEFAULT_SETTINGS = {
    "alpha_load": 0.10,
    "beta_grade": 0.03,
    "speed_idle_threshold": 15,
    "grade_cap": 0.30,
    "ef_mode": "speed_based_nier",
    "freeflow_speed_strategy": "ORS",
    "idle_fuel_gal_per_hr": 0.8,
    "diesel_kgCO2_per_gal": 10.19,
    # 예시 계수(임시 0). 실제 NIER 회귀계수로 갱신
    "nier_coef_truck_a": 0.0,
    "nier_coef_truck_b": 0.0,
    "nier_coef_truck_c": 0.0,
}
