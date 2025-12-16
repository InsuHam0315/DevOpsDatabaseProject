# Backend API 명세

이 문서는 Flask 백엔드가 제공하는 주요 REST API를 정리합니다.

## 공통 사항

- Base URL (개발): `http://localhost:5000`
- 모든 응답은 JSON 형식을 사용합니다.

## GET /

- 설명: 서버 상태 확인용 간단 엔드포인트.
- 응답 예시:

```json
{ "status": "ok" }
```

## GET /test-db

- 설명: Oracle DB 연결 상태 체크.
- 응답:
  - `200 OK`: DB 연결 성공.
  - 실패 시 에러 메시지 및 HTTP 5xx 코드.

## POST /api/optimize (alias: /optimize)

- 설명: 경로 최적화 및 KPI 계산.
- 요청 Body 예시(개념):

```json
{
  "vehicles": [
    { "id": "V1", "capacity": 1000, "co2_per_km": 120 },
    { "id": "V2", "capacity": 800, "co2_per_km": 100 }
  ],
  "sectors": [
    { "id": "S1", "name": "서울 서부", "center_lat": 37.5, "center_lng": 126.9 }
  ],
  "jobs": [
    { "id": "J1", "sector_id": "S1", "demand": 100, "lat": 37.51, "lng": 126.95 }
  ],
  "constraints": {
    "max_distance_km": 300
  }
}
```

- 응답 예시(개념):

```json
{
  "routes": [
    {
      "vehicle_id": "V1",
      "stops": [
        { "job_id": "J1", "sequence": 1, "distance_km": 10.5, "co2_kg": 1.2 }
      ]
    }
  ],
  "kpis": {
    "total_distance_km": 10.5,
    "total_co2_kg": 1.2,
    "total_time_min": 30
  },
  "run_history_entry": {
    "run_id": 123,
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

## GET /api/dashboard

- 설명: 대시보드 요약 데이터.
- 응답 예시(개념):

```json
{
  "kpis": {
    "weekly_total_distance_km": 1200,
    "weekly_total_co2_kg": 140,
    "average_load_factor": 0.75
  },
  "recent_runs": [
    { "run_id": 120, "created_at": "...", "total_distance_km": 100, "total_co2_kg": 11 },
    { "run_id": 121, "created_at": "...", "total_distance_km": 90, "total_co2_kg": 10 }
  ]
}
```

## GET /api/dashboard/weekly-co2

- 설명: 주간 CO2 추이 데이터.
- 응답 예시(개념):

```json
{
  "series": [
    { "week": "2025-W10", "co2_kg": 130 },
    { "week": "2025-W11", "co2_kg": 125 }
  ]
}
```

## GET /api/dashboard/vehicle-distance

- 설명: 차량별 주행 거리 통계.
- 응답 예시(개념):

```json
{
  "vehicles": [
    { "vehicle_id": "V1", "total_distance_km": 500 },
    { "vehicle_id": "V2", "total_distance_km": 700 }
  ]
}
```

