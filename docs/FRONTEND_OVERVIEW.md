# Frontend 개요 (Next.js)

이 문서는 `frontend/` 디렉터리의 구조와 주요 페이지/모듈을 설명합니다.

## 주요 기술 스택

- Next.js 13 (App Router)
- TypeScript
- TailwindCSS
- shadcn/ui
- Zustand (상태 관리)
- Recharts (차트)

## 디렉터리 구조 (요약)

- `app/`
  - `plan/`: 경로 계획/요청 페이지.
  - `routes/`: 최적화 결과 경로 확인 페이지.
  - `dashboard/`: KPI 및 차트 대시보드.
  - `admin/`: 차량/센터/사용자 관리 페이지.
  - `login/`, `signup/`: 인증 관련 페이지.
- `components/`
  - 공통 UI 컴포넌트, 레이아웃 컴포넌트.
- `lib/`
  - `store.ts`: Zustand 전역 상태.
  - `types.ts`: 도메인 타입 정의.
  - `utils.ts`: 유틸 함수.
  - `mock-data.ts`: 목업 데이터.

## 주요 역할

- 백엔드 API와 통신하여:
  - 최적화 요청.
  - 대시보드 데이터 조회.
  - 차량/섹터/작업 정보 관리.
- 사용자 인터랙션:
  - 맵/차트/폼 UI 제공.
  - 결과 해석을 돕는 시각화 제공.

