# 코딩 컨벤션 가이드

이 문서는 프론트엔드/백엔드/SQL 코드 스타일과 컨벤션을 정의합니다.

## 공통 원칙

- 읽기 쉬운 코드 > 짧은 코드.
- 한 함수는 하나의 책임에 집중.
- 의미 있는 변수/함수/파일 이름 사용.

## Python (Backend)

- PEP 8 스타일 가이드 준수.
- 타입 힌트 사용 권장:

```python
def run_optimization(payload: dict) -> dict:
    ...
```

- 예외 처리:
  - 가능한 구체적인 예외 타입 사용.
  - 로그 기록 후 적절한 HTTP 에러 응답으로 변환.

- 모듈 구조:
  - `app.py` 는 라우팅/의존성 주입 중심.
  - 비즈니스 로직은 `services/`, `optimizer/`, `LLM/` 등에 분리.

## TypeScript/React (Frontend)

- 파일 확장자: `.tsx` (컴포넌트), `.ts` (유틸/타입).
- 컴포넌트 네이밍: PascalCase.
- 훅 네이밍: `useSomething`.

```tsx
function DashboardPage() {
  return <div>...</div>;
}
```

- 상태 관리:
  - 전역 상태: `lib/store.ts` (Zustand).
  - 페이지 한정 상태: React `useState`, `useReducer`.

## SQL

- 테이블/컬럼 네이밍:
  - 대문자 스네이크케이스 권장 (예: `RUN_SUMMARY`, `CREATED_AT`).
- 인덱스/제약조건:
  - 의미 있는 이름 사용 (예: `PK_ASSIGNMENTS`, `IDX_ASSIGNMENTS_RUN_ID`).
- DDL/DML 스크립트:
  - 변경 이력 관리 (날짜/버전 주석).

