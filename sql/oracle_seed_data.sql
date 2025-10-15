
-- #######################################################
-- 1. 초기 데이터 INSERT (DML)
-- #######################################################

-- 1. EMISSION_FACTORS (배출 계수 마스터) 데이터 초기화
INSERT INTO EMISSION_FACTORS(VEHICLE_TYPE, WEIGHT_CLASS, FUEL_TYPE, CO2_GPKM, IDLE_GPS, NOTE)
VALUES('truck', '25t', 'diesel', 1200.000, 11.000, '환경부/교통안전공단 고시값');
INSERT INTO EMISSION_FACTORS(VEHICLE_TYPE, WEIGHT_CLASS, FUEL_TYPE, CO2_GPKM, IDLE_GPS, NOTE)
VALUES('van', '1t', 'EV', 50.000, 5.000, '친환경차 표준 계수');
INSERT INTO EMISSION_FACTORS(VEHICLE_TYPE, WEIGHT_CLASS, FUEL_TYPE, CO2_GPKM, IDLE_GPS, NOTE)
VALUES('van', '1.5t', 'hybrid', 150.000, 7.500, '하이브리드 표준 계수');

-- 2. VEHICLES (차량 마스터) 데이터 초기화
INSERT INTO VEHICLES (VEHICLE_ID, FACTOR_ID, VEHICLE_TYPE, MODEL_NAME, CAPACITY_KG) VALUES
('TRK01', 2, 'EV', 'EV 1t', 1000.00);
INSERT INTO VEHICLES (VEHICLE_ID, FACTOR_ID, VEHICLE_TYPE, MODEL_NAME, CAPACITY_KG) VALUES
('TRK02', 1, 'DIESEL', 'DIESEL 25t', 25000.00);
INSERT INTO VEHICLES (VEHICLE_ID, FACTOR_ID, VEHICLE_TYPE, MODEL_NAME, CAPACITY_KG) VALUES
('TRK03', 3, 'HYBRID', 'HYBRID 1.5t', 1500.00);

-- 3. RUNS (최적화 실행 요청) 데이터 초기화
INSERT INTO RUNS (RUN_ID, RUN_DATE, DEPOT_LAT, DEPOT_LON, OPTIMIZATION_STATUS) VALUES
('RUN_20241009_001', TO_DATE('2024-10-09', 'YYYY-MM-DD'), 35.940000, 126.680000, 'COMPLETED');

-- 4. JOBS (배송 작업 상세) 데이터 초기화
INSERT INTO JOBS (RUN_ID, SECTOR_ID, ADDRESS, LATITUDE, LONGITUDE, DEMAND_KG) VALUES
('RUN_20241009_001', 'GUNSAN-A', '군산 산업단지 A구역', 35.950000, 126.690000, 500.00);
INSERT INTO JOBS (RUN_ID, SECTOR_ID, ADDRESS, LATITUDE, LONGITUDE, DEMAND_KG) VALUES
('RUN_20241009_001', 'GUNSAN-B', '군산시청 물류 창고', 35.945000, 126.675000, 200.00);

-- 5. RUN_SUMMARY (결과 요약) 데이터 초기화
INSERT INTO RUN_SUMMARY (RUN_ID, TOTAL_DISTANCE_KM, TOTAL_CO2_G, TOTAL_TIME_MIN, SAVING_PCT) VALUES
('RUN_20241009_001', 36.20, 3080.000, 180, 23.50);

-- #######################################################
-- 2. SETTINGS (가중치/상수) 초기화 (팀장님 예시 준수)
-- #######################################################

-- (키가 존재하지 않을 때만 초기값을 INSERT하고, 기존 값은 보존함)
MERGE INTO SETTINGS s USING dual ON (s.key = 'alpha_load')
WHEN NOT MATCHED THEN INSERT (key, value) VALUES ('alpha_load','0.10');

MERGE INTO SETTINGS s USING dual ON (s.key = 'beta_grade')
WHEN NOT MATCHED THEN INSERT (key, value) VALUES ('beta_grade','0.03');

MERGE INTO SETTINGS s USING dual ON (s.key = 'speed_idle_threshold')
WHEN NOT MATCHED THEN INSERT (key, value) VALUES ('speed_idle_threshold','15');

MERGE INTO SETTINGS s USING dual ON (s.key = 'grade_cap')
WHEN NOT MATCHED THEN INSERT (key, value) VALUES ('grade_cap','0.30');

-- #######################################################
-- 3. CONGESTION_INDEX 초기 데이터 주입 (Flask 테스트용 - 추가됨)
-- #######################################################
INSERT INTO CONGESTION_INDEX (COMPUTED_AT, HOUR_OF_DAY, TIME_FACTOR, IDLE_FACTOR) VALUES
(SYSTIMESTAMP, 9, 1.25, 0.08); -- 오전 9시: 시간 25% 가중, 공회전 8% 가중
INSERT INTO CONGESTION_INDEX (COMPUTED_AT, HOUR_OF_DAY, TIME_FACTOR, IDLE_FACTOR) VALUES
(SYSTIMESTAMP, 14, 1.05, 0.02); -- 오후 2시: 시간 5% 가중, 공회전 2% 가중

COMMIT;