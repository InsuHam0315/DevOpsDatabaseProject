# 데이터 시딩 가이드

이 문서는 Oracle DB에 초기/예시 데이터를 삽입하는 절차를 설명합니다.

## 사용 스크립트

- `sql/oracle_dml_fixed.sql`
  - 기본/고정 데이터 삽입.
- `sql/oracle_dml_its_weather_seed.sql`
  - ITS/날씨 관련 Seed 데이터 삽입.

## 실행 순서 (예시)

1. `oracle_ddl_complete.sql` 로 스키마 생성.
2. `oracle_dml_fixed.sql` 실행.
3. 필요 시 `oracle_dml_its_weather_seed.sql` 실행.

## 개발 vs 운영

- 개발:
  - 테스트 용도로 Seed 데이터를 거의 모두 사용.
- 운영:
  - 일부 Seed 데이터만 사용하거나, 운영에 맞게 커스터마이징 필요.

