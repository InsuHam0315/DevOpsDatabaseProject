# DB 연동 설계 문서

이 문서는 Oracle DB와의 연동 구조 및 주요 모듈을 설명합니다.

## 관련 모듈

- `backend/services/db_handler.py`
  - DB 연결 생성/관리.
  - 쿼리 실행 헬퍼 함수.
- `backend/services/data_collector.py`
  - 대시보드/리포트용 데이터 조회.
- `backend/services/co2_calculator.py`
  - CO2 계산 시 DB 저장/조회와의 관계.
- `backend/LLM/llm_db_save.py`
  - LLM 결과를 DB에 기록.

## 연결 설정

- `config.py` 에서 다음 환경 변수를 로딩합니다.
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_DSN`
  - (필요 시) `OCI_WALLET_DIR`, `OCI_WALLET_PASSWORD`

- `oracledb` 라이브러리를 사용하여 연결합니다.

## 트랜잭션 전략

- 하나의 최적화 실행(run)에 대한 DB 작업은 하나의 트랜잭션 단위로 처리하는 것을 권장합니다.
- 실패 시 롤백, 성공 시 커밋.

## 주요 테이블 (개념)

- `RUN_SUMMARY`
  - 각 최적화 실행(run)에 대한 요약 정보.
- `ASSIGNMENTS`
  - 작업(Job) → 차량(Vehicle) 할당 정보.
- `SETTINGS`
  - CO2 계수 등 설정 값.

자세한 스키마는 `docs/DB_SCHEMA.md` 를 참고합니다.

