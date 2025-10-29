from optimizer.engine import VehicleSpec, SolveInput, solve_vrp

dist = [
    [0, 3, 4],
    [3, 0, 2],
    [4, 2, 0],
]  # km
time = [
    [0, 180, 240],
    [180, 0, 120],
    [240, 120, 0],
]  # sec

inp = SolveInput(
    distance_km=dist,
    duration_sec=time,
    depot_index=0,
    vehicles=[VehicleSpec("T1", 999999, 1000.0, 10.0)],
    # 나머지 기본값(제약 없음)
)

res = solve_vrp(inp)
print("status:", res.status)
for r in res.routes:
    print(r.vehicle_name, r.node_sequence, r.distance_km, r.co2_total_g)
