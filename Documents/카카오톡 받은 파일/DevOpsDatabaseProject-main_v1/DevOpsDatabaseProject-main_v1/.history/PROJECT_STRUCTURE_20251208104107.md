# Project Structure & Key Variables

이 문서는 현재 워크스페이스의 폴더 구조 요약과 주요 설정 변수 및 소스 파일에서 발견한 핵심 변수/함수들을 정리합니다.

---

**작업 경로**: `c:\Users\Insu Ham\Documents\카카오톡 받은 파일\DevOpsDatabaseProject-main_v1\DevOpsDatabaseProject-main_v1`

## 주요 폴더

- `backend/`
  - `app.py` - Flask 서버 엔트리포인트. 주요 API 엔드포인트: `/`, `/test-db`, `/optimize` (alias `/api/optimize`), `/api/dashboard`, `/api/dashboard/weekly-co2`, `/api/dashboard/vehicle-distance`.
  - `config.py` - 환경변수 로드 및 상수 정의 (아래 참조).
  - `LLM/` - LLM 관련 모듈 (예: `llm_call.py`, `lat_lon_kakao.py`, `llm_db_save.py`, 등).
  - `optimizer/` - 최적화 엔진 (예: `engine.py`).
  - `services/` - DB 핸들러, 데이터 수집, XAI 등 서비스 계층 (예: `db_handler.py`, `co2_calculator.py`, `data_collector.py`, `llm_adapter.py`).
  - `requirements.txt` - Python 의존성.

- `frontend/` (Next.js + TypeScript)
  - `app/` - Next.js app router 기반 페이지들 (`plan`, `dashboard`, `login`, `signup`, 등).
  - `components/` - UI 컴포넌트 모음.
  - `lib/` - 유틸/스토어: `store.ts`, `types.ts`, `utils.ts`, `mock-data.ts`.
  - `package.json`, `next.config.js`, `tailwind.config.ts` 등 프론트엔드 설정.

- `sql/` - Oracle DDL/DML 스크립트 및 시드 데이터.

---

## backend/config.py에서 로드되는 주요 환경 변수

- `DB_USER` - Oracle DB 사용자
- `DB_PASSWORD` - Oracle DB 비밀번호
- `DB_DSN` - Oracle 데이터 소스 네임 (TNS 등)
- `OCI_WALLET_DIR` - OCI(Oracle Cloud) Wallet 디렉터리
- `OCI_WALLET_PASSWORD` - Wallet 비밀번호
- `REST_API_KEY` (코드 내부명: `KAKAOMAP_REST_API`) - Kakao REST API Key (Kakao Local/Direction 호출에 사용)
- `NEXT_PUBLIC_KAKAO_MAP_API_KEY` (코드 내부명: `KAKAOMAP_SCRIPT`) - 프런트엔드에서 사용하는 Kakao JS Key
- `FLASK_PORT` - Flask 실행 포트 (기본 5000)
- `GOOGLE_API_KEY` - Google Generative AI (Gemini) API Key

> 위치: `backend/config.py` (dotenv로 `.env` 파일에서 로드)

---

## backend/app.py — 주요 엔드포인트 요약

- `/` (GET): 헬스체크
- `/test-db` (GET): DB 연결 테스트 (`test_db_connection()` 호출)
- `/optimize` (POST): 최적화 요청 수신 및 `optimizer.engine.run_optimization` 호출 — 응답으로 `routes`, `kpis`, `run_history_entry` 반환
- `/api/optimize` (POST): `/optimize`의 alias
- `/api/dashboard` (GET): 대시보드 데이터 (`get_dashboard_data()` 호출)
- `/api/dashboard/weekly-co2` (GET): 기간별 CO2 트렌드 (`get_weekly_co2_trend` 호출)
- `/api/dashboard/vehicle-distance` (GET): 차량 거리 통계 (`get_vehicle_distance_stats` 호출)

참고: LLM 블루프린트(`LLM/llm_call.py`)는 ImportError 발생 시 등록되지 않도록 방어 코드를 포함.

---

## frontend `lib/store.ts` — 주요 변수·함수

- 상수/기본값
  - `DEFAULT_KPIS` - KPI 기본값 객체

- 유틸 함수
  - `ensureKpis(value?)` - KPI 객체를 보장
  - `toNumber(value, divider?)` - 숫자 파싱 보조

- 라우트/결과 파싱 관련
  - `parseDistanceKm(route)` - 다양한 필드명에서 거리(km) 추출
  - `parseCo2Kg(route)` - 다양한 필드명에서 CO2(kg) 추출 (g->kg 변환 포함)
  - `toPolylinePoints(route)` - 여러 포맷의 polyline/points/steps를 표준 {lat,lng} 배열로 변환
  - `buildVehicleRoutes(routes, vehicles)` - 차량별 요약 `VehicleRoute` 생성
  - `collectVehicleRouteCandidatesFromBatch(results)` - batch 결과에서 후보 라우트 수집
  - `parseKpisFromExplanation(expl)` - LLM 설명(텍스트)에서 KPI(거리, CO2, 시간)를 정규식으로 추출

- 스토어 구조 (`AppStore` 인터페이스)
  - 상태: `vehicles`, `sectors`, `jobs`, `routes`, `vehicleRoutes`, `kpis`, `runHistory`, `chartData`, `batchResults`, `dashboardKpis` 등
  - 액션: `setBatchResults`, `setDashboardData`, `runOptimization`, `addVehicle`/`updateVehicle` 등

특히 `setBatchResults`는 백엔드에서 오는 다양한 포맷을 허용하도록 방어적으로 작성되어 있으며, `batchResults[].optimization_result` 내에서 `results`, `vehicle_routes`, `assignments` 등을 찾아 KPI 및 runHistory를 구성합니다.

---

## LLM / Geocoding 관련 파일

- `backend/LLM/lat_lon_kakao.py` — Kakao Local(주소/키워드 검색) 우선, 실패 시 OpenStreetMap Nominatim 폴백을 시도하도록 구현되어 있음. (최근 수정 기록 존재)
- `backend/services/llm_adapter.py`, `backend/LLM/llm_call.py` — LLM 호출과 LLM에서 생성한 설명을 DB에 저장하는 로직 포함

문제점/관찰:
- 특정 주소(예: `군산 국제여객터미널`)를 Kakao에서 바로 찾지 못해 Nominatim 폴백이 사용되도록 매핑/정제 로직이 추가되어 있음. 그러나 미등록 주소/매핑 누락 시 geocoding 실패로 인해 최적화 실행이 중단될 수 있음.

---

## 권장 확인 항목 (빠른 디버깅 체크리스트)

1. `.env`에 `REST_API_KEY`(Kakao REST key) 및 `GOOGLE_API_KEY`, DB 접속(`DB_USER`, `DB_PASSWORD`, `DB_DSN`) 값이 있는지 확인
2. `backend/LLM/lat_lon_kakao.py`의 매핑(`address_mapping`)에 실패하는 지명을 추가(예: `군산 국제여객터미널` → `군산 연안여객터미널`)하거나, 입력 주소를 전처리해서 검색 품질을 높이기
3. Kakao API 호출이 실패하면 콘솔 로그(또는 서버 로그)에 어떤 전략(strategy_1/2/3)이 시도되었는지, Nominatim 폴백 동작 여부를 확인
4. 백엔드 실행 전 `python -m py_compile backend/LLM/lat_lon_kakao.py`로 문법 오류 확인

---

## 다음 단계 제안

- 원하시면 저는 다음을 자동으로 해 드리겠습니다:
  - `backend/LLM/lat_lon_kakao.py`에서 실패한 주소 목록(최근 `_geocoding_stats`)을 찾아 자동 매핑 후보를 제안
  - `.env` 예시 템플릿(`backend/.env.example`) 생성
  - `PROJECT_STRUCTURE.md`에 더 많은 세부(각 모듈의 함수/변수 목록) 추가 — 원하시면 코드 기반 전체를 스캔해 수집 가능합니다.

---

파일 생성 시간: 자동 생성
