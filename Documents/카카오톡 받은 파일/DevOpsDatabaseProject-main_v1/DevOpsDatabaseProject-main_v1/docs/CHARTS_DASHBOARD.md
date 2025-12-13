# 대시보드 & 차트 설계

이 문서는 Recharts 기반 대시보드 구현 방향을 설명합니다.

## 주요 차트

- 주간 CO2 추이:
  - 데이터: `/api/dashboard/weekly-co2`.
  - X축: 주(Week), Y축: CO2(kg).
- 차량별 운행 거리:
  - 데이터: `/api/dashboard/vehicle-distance`.
  - X축: 차량 ID, Y축: 거리(km).
- 최근 실행(run) 요약:
  - 데이터: `/api/dashboard`.
  - 카드 또는 막대그래프로 표시.

## 데이터 구조

- `chartData` (store 상태):
  - 위 API 응답을 차트 컴포넌트에서 바로 사용할 수 있는 형태로 전처리합니다.

## UX 고려사항

- 범례/툴팁을 통해 값/단위를 명확히 표시.
- KPI 카드와 차트의 색상/레이블 일관성 유지.

