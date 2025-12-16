# 상태 관리 설계 (Zustand)

이 문서는 `frontend/lib/store.ts` 중심의 상태 관리 구조를 설명합니다.

## 상태 구조 개요

`AppStore` (개념)에는 다음과 같은 상태가 포함됩니다.

- `vehicles`: 차량 목록.
- `sectors`: 섹터/권역 목록.
- `jobs`: 배송 작업 목록.
- `routes`: 최적화 결과 경로.
- `vehicleRoutes`: 차량별 경로 구조.
- `kpis`: 현재 실행에 대한 KPI.
- `runHistory`: 과거 실행 이력.
- `chartData`: 대시보드용 차트 데이터.
- `batchResults`: LLM/최적화 batch 실행 결과.
- `dashboardKpis`: 대시보드 KPI 요약.

## 주요 액션

- `runOptimization`
  - 현재 입력 상태를 기반으로 백엔드 `/api/optimize` 호출.
  - 응답을 `routes`, `kpis`, `runHistory` 등에 반영.
- `setBatchResults`
  - batch 형태의 LLM/최적화 결과를 저장.
- `setDashboardData`
  - 대시보드 API 응답을 상태에 반영.
- `addVehicle`, `updateVehicle` 등
  - 차량 정보 관리.

## 유틸 함수

- `parseDistanceKm(route)`.
- `parseCo2Kg(route)`.
- `toPolylinePoints(route)`.
- `buildVehicleRoutes(routes, vehicles)`.
- `collectVehicleRouteCandidatesFromBatch(results)`.
- `parseKpisFromExplanation(expl)`.

이 함수들은 API 응답/LLM 결과를 프론트에서 사용하기 쉬운 형태로 변환하는 데 사용됩니다.

