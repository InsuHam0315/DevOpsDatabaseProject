---- ###############################################
-- 1. EMISSION_FACTORS 테이블
-- ###############################################
CREATE TABLE EMISSION_FACTORS (
    FACTOR_ID NUMBER PRIMARY KEY,
    VEHICLE_TYPE VARCHAR2(50) NOT NULL,
    CO2_GPKM NUMBER(10, 3) NOT NULL
);

-- ###############################################
-- 2. VEHICLES 테이블
-- ###############################################
CREATE TABLE VEHICLES (
    VEHICLE_ID VARCHAR2(50) PRIMARY KEY,
    FACTOR_ID NUMBER NOT NULL,
    CAPACITY_KG NUMBER(10, 2) NOT NULL,
    CONSTRAINT FK_VEHICLE_FACTOR FOREIGN KEY (FACTOR_ID)
        REFERENCES EMISSION_FACTORS (FACTOR_ID)
);

-- ###############################################
-- 3. RUNS 테이블
-- ###############################################
CREATE TABLE RUNS (
    RUN_ID VARCHAR2(50) PRIMARY KEY,
    VEHICLE_ID VARCHAR2(50) NOT NULL,
    RUN_DATE DATE NOT NULL,
    DIST_KM NUMBER(10, 3) NOT NULL,
    NATURAL_LANGUAGE CLOB,
    CONSTRAINT FK_RUN_VEHICLE FOREIGN KEY (VEHICLE_ID)
        REFERENCES VEHICLES (VEHICLE_ID)
);

-- ###############################################
-- 4. RUN_SUMMARY 테이블
-- ###############################################
CREATE TABLE RUN_SUMMARY (
    SUMMARY_ID NUMBER PRIMARY KEY,
    RUN_ID VARCHAR2(50) NOT NULL,
    TOTAL_DISTANCE_KM NUMBER(10, 3) NOT NULL,
    TOTAL_CO2_G NUMBER(12, 3) NOT NULL,    -- ✅ 정밀도 확장 (10,3 → 12,3)
    CONSTRAINT FK_SUMMARY_RUN FOREIGN KEY (RUN_ID)
        REFERENCES RUNS (RUN_ID)
);

-- ###############################################
-- 5. ASSIGNMENTS 테이블
-- ###############################################
CREATE TABLE ASSIGNMENTS (
    ASSIGN_ID NUMBER PRIMARY KEY,
    RUN_ID VARCHAR2(50) NOT NULL,
    VEHICLE_ID VARCHAR2(50) NOT NULL,
    DRIVER_NAME VARCHAR2(100) NOT NULL,
    CO2_G NUMBER(12, 5) NOT NULL,          -- ✅ 정밀도 확장 (10,5 → 12,5)
    CONSTRAINT FK_ASSIGN_RUN FOREIGN KEY (RUN_ID)
        REFERENCES RUNS (RUN_ID),
    CONSTRAINT FK_ASSIGN_VEHICLE FOREIGN KEY (VEHICLE_ID)
        REFERENCES VEHICLES (VEHICLE_ID)
);
