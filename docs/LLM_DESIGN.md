# LLM 설계 문서

이 문서는 백엔드의 LLM 관련 모듈 구조와 프롬프트/응답 설계 방향을 설명합니다.

## 관련 모듈

- `backend/LLM/llm_call.py`
  - LLM Provider(Google Generative AI, OpenRouter 등)에 대한 HTTP 호출 모듈.
  - 프롬프트 생성, 응답 파싱 및 오류 처리.
- `backend/LLM/llm_db_save.py`
  - LLM 응답을 Oracle DB에 저장하는 로직.
- `backend/LLM/lat_lon_kakao.py`
  - Kakao/기타 지오코딩 서비스와 연동하여 주소 → 위경도 변환.
- `backend/services/llm_adapter.py`
  - LLM 응답(JSON/텍스트)을 내부 도메인 모델(JSON 스키마)로 변환합니다.

## 목표

- LLM을 이용해 “배송 계획/설명”을 자연어 + JSON 형태로 생성합니다.
- LLM 응답을 안전하게 검증하고, 최적화 엔진 및 DB에 전달 가능한 형태로 변환합니다.

## 프롬프트/응답 구조 (개념)

- 입력:
  - 차량/섹터/작업(Job)에 대한 기본 정보.
  - 비즈니스 제약 조건(예: CO2 최소화, 시간 제한).
- 출력:
  - JSON 형태의 계획안.
  - 사용자에게 보여줄 설명 텍스트.

예시(개념적인 구조):

```json
{
  "plan": {
    "vehicles": [...],
    "jobs": [...],
    "constraints": {...}
  },
  "explanation": "이 계획은 CO2 배출을 최소화하기 위해 ..."
}
```

## 에러/안전성 전략

- 응답 검증:
  - JSON 파싱 실패 시 재시도 또는 fallback 전략.
  - 필수 필드 누락 시 기본값/에러 처리.
- 토큰/비용 관리:
  - 요청당 토큰 제한, Rate Limit 고려.
- 로깅:
  - 프롬프트/응답은 PII/민감정보 제거 후 로그로 남김.

## 향후 개선 아이디어

- 다양한 LLM 백엔드(예: OpenAI, Azure OpenAI)로 확장 가능한 인터페이스 계층.
- 프롬프트 템플릿 관리(버전 관리, 실험 A/B 테스트).

