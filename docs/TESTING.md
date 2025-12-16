# 테스트 전략

이 문서는 프로젝트의 테스트 방향성과 각 레이어별 권장 테스트 방법을 설명합니다.

## 테스트 레벨

- **단위 테스트(Unit Test)**:
  - Python 서비스 함수, 최적화 엔진 로직.
  - TypeScript 유틸/상태 관리 로직.
- **통합 테스트(Integration Test)**:
  - Flask API ↔ Oracle DB 연동.
  - Frontend ↔ Backend API 통신.
- **E2E 테스트(선택)**:
  - 브라우저 환경에서 실제 사용자 플로우 테스트.

## Backend 테스트 아이디어

- `optimizer.engine.run_optimization`:
  - 간단한 차량/작업 데이터로 기대되는 경로/할당이 생성되는지 확인.
- `services/co2_calculator.py`:
  - 거리/연비 → CO2 계산 로직 검증.
- `services/db_handler.py`:
  - 트랜잭션, 에러 처리, 기본 CRUD 테스트.

## Frontend 테스트 아이디어

- `lib/store.ts`:
  - `runOptimization`, `setBatchResults`, `setDashboardData` 등 상태 전이 검증.
- UI 컴포넌트:
  - 주요 페이지(`plan`, `routes`, `dashboard`, `admin`) 렌더링 및 상호작용.

## 테스트 실행

- Backend:
  - `pytest` 또는 `unittest` 기반 테스트 스위트 구성.
- Frontend:
  - `jest`, `testing-library`, `playwright` 등 도입 가능.

## 품질 기준

- 중요한 비즈니스 로직(최적화, KPI 계산, DB 트랜잭션)은 테스트 케이스 필수.
- 버그가 발생한 경우:
  - 재현 테스트를 먼저 추가한 뒤 수정.

