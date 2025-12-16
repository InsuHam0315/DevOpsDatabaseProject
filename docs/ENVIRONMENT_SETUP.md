# 개발 환경 설정 가이드

이 문서는 Eco Logistics Optimizer를 로컬 개발 환경에서 실행하기 위한 설정 방법을 정리합니다.

## 1. 필수 설치 항목

- Git
- Node.js (LTS 권장)
- Python 3.x (프로젝트에 맞는 버전)
- Oracle 클라이언트 또는 Instant Client
- IDE/에디터 (VS Code 등)

## 2. 저장소 클론 및 기본 구조 확인

```bash
git clone <this-repo-url>
cd DevOpsDatabaseProject-main_v1/DevOpsDatabaseProject-main_v1
```

루트에는 `backend/`, `frontend/`, `sql/` 디렉터리가 있습니다.

## 3. 공통 환경 변수 개요

환경 변수는 주로 `backend/.env` 와 `frontend/.env.local`에서 관리합니다.

### Backend `.env` 예시

```env
DB_USER=your_oracle_username
DB_PASSWORD=your_oracle_password
DB_DSN=your_oracle_dsn

OPENROUTER_API_KEY=""
OPENROUTER_API_URL=""
REST_API_KEY=""             # Kakao REST API Key

GOOGLE_API_KEY=""           # Google Generative AI Key (옵션)
FLASK_PORT=5000
```

### Frontend `.env.local` 예시

```env
NEXT_PUBLIC_KAKAO_MAP_API_KEY=your_kakao_map_js_key
NEXT_PUBLIC_LLM_API_ENDPOINT=http://localhost:5000/api/optimize
NEXT_PUBLIC_OPTIMIZATION_API_ENDPOINT=http://localhost:5000/api/optimize
```

## 4. Backend 개발 환경 설정

```bash
cd backend

# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows PowerShell)
.\venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

`backend/.env` 파일을 위 예시를 참고해 생성합니다.

### Backend 서버 실행

```bash
cd backend
.\venv\Scripts\activate
python app.py
```

기본적으로 `http://localhost:5000` 에서 Flask 서버가 구동됩니다.

## 5. Frontend 개발 환경 설정

```bash
cd frontend
npm install
```

`frontend/.env.local` 파일을 예시에 맞게 생성합니다.

### Frontend 개발 서버 실행

```bash
cd frontend
npm run dev
```

기본적으로 `http://localhost:3000` 에서 Next.js 개발 서버가 구동됩니다.

## 6. Oracle DB 준비

1. Oracle DB 인스턴스 준비 (로컬 / 클라우드).
2. `DB_USER`, `DB_PASSWORD`, `DB_DSN` 을 `.env` 에 설정.
3. `sql/oracle_ddl_complete.sql` 실행으로 스키마 생성.
4. `sql/oracle_dml_fixed.sql`, `sql/oracle_dml_its_weather_seed.sql` 순서로 Seed 데이터 삽입.

DB 클라이언트(예: SQL*Plus, SQL Developer)를 사용해 스크립트를 실행할 수 있습니다.

## 7. 외부 API 키 발급

- **Kakao Map/Local API**
  - Kakao Developers에서 애플리케이션 생성.
  - REST API Key → `REST_API_KEY`.
  - JavaScript Key → `NEXT_PUBLIC_KAKAO_MAP_API_KEY`.

- **LLM API**
  - Google Generative AI / OpenRouter 등에서 API Key 발급.
  - 키와 엔드포인트를 Backend/Frontend 환경 변수에 연결.

## 8. 빠른 점검 체크리스트

- [ ] `backend/.env` 생성 및 값 설정
- [ ] `frontend/.env.local` 생성 및 값 설정
- [ ] 백엔드 가상환경 생성 및 `pip install`
- [ ] 프론트엔드 `npm install`
- [ ] Oracle DB 스키마/Seed 데이터 적용
- [ ] `http://localhost:3000`에서 UI 로딩 확인
- [ ] 최적화 요청/대시보드 조회 테스트

