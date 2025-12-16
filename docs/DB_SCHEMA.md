# DB 스키마 개요

이 문서는 `sql/oracle_ddl_complete.sql`에 정의된 스키마의 개념적 구조를 설명합니다.

## 주요 테이블 (개념 요약)

- `RUN_SUMMARY`
  - 각 최적화 실행(run)에 대한 요약.
  - 예: `RUN_ID`, `CREATED_AT`, `TOTAL_DISTANCE_KM`, `TOTAL_CO2_KG`, `STATUS`.

- `ASSIGNMENTS`
  - 작업(Job) → 차량(Vehicle) 할당 정보.
  - 예: `ASSIGNMENT_ID`, `RUN_ID`, `VEHICLE_ID`, `JOB_ID`, `SEQUENCE`.

- `SETTINGS`
  - 시스템 설정값.
  - 예: CO2 계수, 기본 제약 조건 값 등.

기타 테이블/컬럼의 상세 내용은 실제 DDL 파일을 참고합니다.

## 관계 (개념)

- `RUN_SUMMARY.RUN_ID` ↔ `ASSIGNMENTS.RUN_ID`.
- `SETTINGS`는 별도의 참조 관계를 가질 수도 있고, 애플리케이션에서 키/값 형태로 사용될 수 있습니다.

