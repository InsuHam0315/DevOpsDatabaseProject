# 배포 가이드

이 문서는 Eco Logistics Optimizer를 운영/스테이징 환경에 배포하는 방법과 고려 사항을 정리합니다.

## 환경 별 개요

- **개발(Dev)**: 로컬 개발자 환경, 실험/개발 브랜치.
- **스테이징(Stage)**: 운영과 유사한 테스트 환경, QA/검증용.
- **운영(Prod)**: 실제 고객이 사용하는 환경.

각 환경마다 다음 항목이 구분될 수 있습니다.

- 도메인 / URL
- DB 인스턴스 및 계정
- LLM/Kakao API 키
- 로깅/모니터링 설정

## Backend 배포

### 1. 의존성 설치

- Python 3.x
- 가상환경
- Oracle 클라이언트

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정

- 운영/스테이징 서버에서 `.env` 또는 환경 변수 관리 도구(예: Vault, Parameter Store)를 사용합니다.
- 개발용과 다른 DB 계정/DSN, API 키를 설정합니다.

### 3. 애플리케이션 서버

예시 (리눅스 기준 개념):

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Nginx 등 리버스 프록시를 앞단에 두어 HTTPS, 정적 파일 서빙 등을 처리할 수 있습니다.

## Frontend 배포

### 1. 빌드

```bash
cd frontend
npm install
npm run build
```

### 2. 서비스 방식

- Node.js 서버 기반 SSR/동적 라우팅 유지.
- 가능하다면 Static Export 후 정적 호스팅(S3, Vercel, Netlify 등)도 고려.

환경에 맞게:

- 운영 URL, API 엔드포인트를 환경 변수로 주입.
- 빌드 시점/실행 시점 환경 변수 처리 전략을 명확히 합니다.

## Oracle DB 배포/마이그레이션

- 초기에는 `sql/oracle_ddl_complete.sql` 실행.
- Seed 데이터 스크립트는 환경에 맞게 선택 적용.
- 스키마 변경 시 `docs/DB_MIGRATION_POLICY.md`에 정의된 절차에 따라 순차 적용.

## 로깅 및 모니터링

- 백엔드:
  - 요청/응답 로그(개인정보/민감정보 마스킹).
  - 에러 로그(스택 트레이스).
- 프론트엔드:
  - 에러 리포팅 도구(Sentry 등) 연동 고려.
- 인프라:
  - CPU, 메모리, 디스크, 네트워크 모니터링.

## 배포 체크리스트

- [ ] .env / 환경 변수 설정 완료.
- [ ] DB 마이그레이션/Seed 적용.
- [ ] 백엔드/프론트엔드 빌드 및 서버 기동.
- [ ] 주요 API 헬스체크 및 UI 시나리오 검증.
- [ ] 로그/모니터링 대시보드 확인.

