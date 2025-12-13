# Backend 개요 (Flask)

이 문서는 `backend/` 디렉터리의 전반적인 구조와 주요 컴포넌트를 설명합니다.

## 주요 파일/폴더

- `app.py`
  - Flask 애플리케이션 엔트리포인트.
  - 라우트 정의 및 요청 처리.
- `config.py`
  - `.env` 로부터 환경 변수 로딩.
  - DB, API 키 등 설정 값 관리.
- `LLM/`
  - `llm_call.py`: LLM API 호출, 프롬프트 구성/응답 파싱.
  - `llm_db_save.py`: LLM 결과를 DB에 저장하는 로직.
  - `lat_lon_kakao.py`: Kakao/기타 서비스를 이용한 주소 → 좌표 변환.
- `optimizer/`
  - `engine.py`: Google OR-Tools 기반 최적화 로직.
- `services/`
  - `db_handler.py`: DB 연결/쿼리 헬퍼.
  - `co2_calculator.py`: CO2 계산 유틸.
  - `data_collector.py`: 대시보드용 데이터 수집.
  - `llm_adapter.py`: LLM JSON 포맷 변환/검증.
  - `xai.py`: XAI 설명 생성.

## 주요 엔드포인트

- `GET /`
  - 상태 체크/헬스 체크 용도.
- `GET /test-db`
  - DB 연결 테스트.
- `POST /optimize` (및 `POST /api/optimize`)
  - 경로 최적화 요청.
  - 입력: 차량/섹터/작업 등.
  - 출력: `routes`, `kpis`, `run_history_entry` 등.
- `GET /api/dashboard`
  - 대시보드 기본 데이터.
- `GET /api/dashboard/weekly-co2`
  - 주간 CO2 추이 데이터.
- `GET /api/dashboard/vehicle-distance`
  - 차량별 운행 거리 통계.

## 요청 처리 흐름 (예: /api/optimize)

1. 요청 JSON 파싱 및 기본 검증.
2. 필요시 LLM 호출(계획 생성/보정).
3. `optimizer.engine.run_optimization` 호출.
4. 실행 결과/이력(`run_history_entry`)를 DB에 저장.
5. 응답 JSON 생성 후 반환.

## 예외 처리/로깅

- DB 에러, 외부 API 에러, 최적화 실패 등은 로그로 남기고 적절한 HTTP 코드로 응답합니다.
- 운영 환경에서는 스택 트레이스를 로그에만 남기고, 클라이언트에는 요약 메시지만 반환합니다.

