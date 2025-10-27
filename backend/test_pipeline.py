from optimizer.run_pipeline import run_co2_pipeline

if __name__ == "__main__":
    origin = (126.7369, 35.9675)  # 군산시청 근처
    dest = (126.7000, 35.9500)
    dem_path = "data/dem_gunsan.tif"  # 실제 DEM 파일 경로로 바꾸기
    result = run_co2_pipeline(origin, dest, dem_path)
    print(result)
