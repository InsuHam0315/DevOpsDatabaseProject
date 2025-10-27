## 1. 교통안전공단 차종별 배출계수
- 출처/접근: (URL/파일/요청 방식)
- 스키마(원본): fuel_type, vehicle_class, weight_ton, co2_g_per_km, co2_g_per_min_idle, updated_at
- 단위/정규화: km당 g, 공회전 g/min → 프로젝트 기본 단위(kg, km, min)로 변환
- 품질/누락: …
- 라이선스/제한: …
- 변환 스키마(Processed): 
  - vehicle_class (VARCHAR2(30))
  - weight_ton (NUMBER(5,2))
  - co2_gpkm (NUMBER(10,2))
  - idle_co2_gpm (NUMBER(10,2))
  - source_version (VARCHAR2(20))
- 적재 대상 테이블: VEHICLE_EMISSION_FACTORS

## 2. 한국도로공사 종단선형(경사도)
- 출처/접근: …
- 스키마(원본): route_id, seq, start_km, end_km, grade_ratio(%), direction
- 변환 스키마(Processed):
  - section_id, route_id, start_km, end_km, grade_pct, start_lat, start_lon, end_lat, end_lon
- 가정/좌표계: WGS84, 선형참조 매칭 이슈 기록
- 적재 대상 테이블: ROAD_GRADES

## 3. ITS 주행속도/교통량
- 출처/접근: …
- 스키마(원본): link_id, obs_time, speed_kmh, volume, occupancy
- 변환 스키마(Processed): link_id, obs_ts, speed_kmh, volume
- 적재 대상 테이블: ITS_TRAFFIC

## 4. 국토부 화물 O/D 통계
- …
- 적재 대상 테이블: FREIGHT_OD

## 5. 군산 산업단지(교차로/이력)
- …
- 적재 대상 테이블: GUNSAN_INDUSTRIAL_X
