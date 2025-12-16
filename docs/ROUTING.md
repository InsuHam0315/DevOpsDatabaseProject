# Frontend 라우팅 구조

이 문서는 Next.js App Router 기반의 주요 페이지 경로와 역할을 정리합니다.

## 주요 페이지

- `/`
  - 랜딩 또는 대시보드/로그인으로 리다이렉트하는 역할 (구현에 따라 상이).

- `/plan`
  - 배송 계획 수립 UI.
  - 차량/섹터/작업(Job) 입력.
  - LLM/최적화 요청 전송.

- `/routes`
  - 최적화 결과(경로)를 시각화.
  - 각 차량별 경로, CO2, 거리, 시간 등 확인.

- `/dashboard`
  - KPI 및 차트 모음.
  - 주간 CO2, 차량별 거리, 최근 실행 이력 등.

- `/admin`
  - 시스템 관리 UI.
  - 차량/센터/계정 관리 등.

- `/login`, `/signup`
  - 인증 관련 페이지 (현 상태/계획에 따라 구현).

## 라우팅과 API 매핑

- `/plan`
  - 백엔드: `POST /api/optimize`.
- `/routes`
  - 백엔드: `POST /api/optimize` 결과를 상태로부터 읽어 렌더링.
- `/dashboard`
  - 백엔드:
    - `GET /api/dashboard`.
    - `GET /api/dashboard/weekly-co2`.
    - `GET /api/dashboard/vehicle-distance`.

