# 시스템 아키텍처 개요

이 문서는 Eco Logistics Optimizer 전체 시스템 구조와 주요 구성 요소 간 관계를 설명합니다.

## 전체 구성요소

- **Frontend (Next.js 13, TypeScript)**
  - 사용자가 경로 계획, 결과 조회, 대시보드 확인, 관리자 기능을 이용하는 웹 UI입니다.
  - 백엔드의 REST API를 호출하여 데이터 조회/저장/최적화 요청을 수행합니다.

- **Backend (Flask, Python)**
  - 비즈니스 로직의 중심입니다.
  - LLM 호출, 최적화 엔진 실행, Oracle DB 연동, XAI 설명 생성 등을 담당합니다.
  - 주요 엔드포인트(개념):
    - `GET /` (헬스체크)
    - `GET /test-db` (DB 연결 테스트)
    - `POST /optimize`, `POST /api/optimize` (경로 최적화)
    - `GET /api/dashboard` (대시보드 요약)
    - `GET /api/dashboard/weekly-co2`
    - `GET /api/dashboard/vehicle-distance`

- **Database (Oracle)**
  - 경로 최적화 결과, 배차 이력, 설정값 등을 저장합니다.
  - `sql/oracle_ddl_complete.sql` 및 관련 DML 스크립트로 스키마/초기 데이터를 관리합니다.

- **외부 서비스**
  - Kakao Map / Local API: 주소 → 좌표(위경도) 변환, 길찾기 등.
  - LLM(Google Generative AI / OpenRouter 등): 텍스트 기반 계획/설명 생성, JSON 계획 구조 생성.

## 디렉터리별 역할

### frontend/

- `app/`
  - Next.js App Router 기반 페이지 디렉터리입니다.
  - `plan/`, `routes/`, `dashboard/`, `admin/`, `login/`, `signup/` 등 페이지가 위치합니다.
- `components/`
  - 공통 UI 컴포넌트 및 레이아웃 컴포넌트가 모여 있습니다.
- `lib/`
  - `store.ts`: Zustand 기반 전역 상태 관리.
  - `types.ts`: 타입 정의.
  - `utils.ts`, `mock-data.ts`: 유틸 함수와 목업 데이터.

### backend/

- `app.py`
  - Flask 서버 엔트리포인트입니다.
  - 라우팅 및 요청/응답 흐름을 정의합니다.
- `config.py`
  - 환경 변수 로딩 및 설정값을 관리합니다.
- `LLM/`
  - `llm_call.py`, `llm_db_save.py`, `lat_lon_kakao.py` 등 LLM/지오코딩 관련 모듈이 위치합니다.
- `optimizer/`
  - `engine.py` 등 Google OR-Tools 기반 경로 최적화 로직이 위치합니다.
- `services/`
  - `db_handler.py`: DB 연결 및 쿼리/삽입/업데이트.
  - `co2_calculator.py`: CO2 계산.
  - `data_collector.py`: 대시보드/리포트용 데이터 수집.
  - `llm_adapter.py`: LLM JSON 포맷 어댑터.
  - `xai.py`: XAI 설명 생성.

### sql/

- `oracle_ddl_complete.sql`
  - 주요 테이블, 시퀀스, 제약조건, 인덱스를 정의합니다.
- `oracle_dml_fixed.sql`
  - 기본 데이터/예시 데이터를 삽입합니다.
- `oracle_dml_its_weather_seed.sql`
  - ITS/날씨 관련 Seed 데이터를 삽입합니다.

## 데이터 흐름 (개요)

1. **사용자 입력**
   - 프론트에서 차량, 섹터, 작업(Job) 등의 정보를 입력하거나 조회합니다.

2. **LLM/최적화 요청**
   - 프론트 → 백엔드 `/api/optimize` 로 JSON 요청을 전송합니다.

3. **LLM 및 최적화 엔진 실행**
   - 백엔드에서 LLM을 호출해 보조적인 계획/설명을 얻을 수 있습니다.
   - `optimizer.engine.run_optimization` 호출로 최적 경로를 계산합니다.

4. **DB 저장**
   - 최적화 결과, KPI, 실행 이력 등을 Oracle DB에 저장합니다.

5. **결과 조회**
   - 프론트가 `/api/dashboard` 및 관련 API를 통해 결과, KPI, 차트 데이터를 조회합니다.

## 계층적 책임

- **표현 계층 (Frontend)**
  - UX/UI, 상태 관리, 차트 렌더링, 지도/맵 렌더링.
- **애플리케이션 계층 (Backend)**
  - REST API, 입력 유효성 검사, LLM/최적화 호출, DB 트랜잭션 관리.
- **도메인/인프라 계층**
  - 최적화 엔진(OR-Tools), Oracle DB 스키마 및 쿼리, Kakao/LLM API 연동.

## 향후 확장 포인트

- 멀티 테넌트 지원(고객사별 데이터 분리).
- 추가 KPI 및 제약 조건(예: 운행 비용, 운전자 근무 시간 규정).
- 다양한 LLM 백엔드(OpenAI, Azure 등)를 위한 어댑터 확장.

