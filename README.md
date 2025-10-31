# Eco Logistics Optimizer

LLM을 활용한 친환경 물류 경로 최적화 시스템의 웹 프론트엔드 프로토타입입니다.

## 🚀 기능 개요

### 주요 페이지
- **경로 계획** (`/plan`): 자연어/폼 입력을 통한 배송 계획 수립
- **경로 결과** (`/routes`): 최적화 결과 및 지도 시각화
- **대시보드** (`/dashboard`): 성과 지표 및 차트 분석
- **데이터 관리** (`/admin`): 차량/섹터/작업 마스터 데이터 관리

### 핵심 특징
- 🌱 **친환경 최적화**: CO₂ 배출량 최소화 경로 계획
- 🤖 **LLM 자연어 처리**: 자연어 입력을 구조화된 배송 요구사항으로 변환
- 🗺️ **지도 시각화**: 카카오맵 기반 경로 및 차량 위치 표시
- 📊 **실시간 대시보드**: 주행거리, CO₂ 배출량, 처리량 등 KPI 모니터링
- 📱 **반응형 디자인**: 모바일/태블릿/데스크톱 최적화

## 🛠️ 기술 스택

### Frontend
- **Framework**: Next.js 13 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS + shadcn/ui
- **상태관리**: Zustand
- **차트**: Recharts
- **아이콘**: Lucide React

### Backend
- **Framework**: Flask
- **Language**: Python
- **최적화 엔진**: Google OR-Tools
- **데이터베이스**: Oracle Database
- **DB 연동**: oracledb

## 📦 설치 및 실행
### Frontend
```bash
# frontend 폴더로 이동
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행 (http://localhost:3000)
npm run dev
```
### Backend
```bash
# backend 폴더로 이동
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
.\venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행 (http://localhost:5000)
python app.py
```

## 📁 프로젝트 구조

```
Eco Logistics Optimizer/
├── frontend/                 # Next.js 프론트엔드 소스 코드
│   ├── app/                  # Next.js App Router 페이지
│   │   ├── plan/             # 경로 계획 페이지
│   │   ├── routes/           # 경로 결과 페이지
│   │   ├── dashboard/        # 대시보드 페이지
│   │   └── admin/            # 데이터 관리 페이지
│   ├── components/           # 재사용 가능한 컴포넌트
│   │   ├── ui/               # shadcn/ui 컴포넌트
│   │   ├── layout/           # 레이아웃 컴포넌트
│   │   ├── plan/             # 계획 관련 컴포넌트
│   │   └── admin/            # 관리 관련 컴포넌트
│   ├── lib/                  # 유틸리티 및 설정
│   │   ├── types.ts          # TypeScript 타입 정의
│   │   ├── store.ts          # Zustand 상태 관리
│   │   ├── mock-data.ts      # 더미 데이터
│   │   └── utils.ts          # 공통 유틸리티
│   └── hooks/                # 커스텀 훅
├── backend/                  # Flask 백엔드 소스 코드
│   ├── venv/                 # 파이썬 가상환경
│   ├── app.py                # Flask API 서버 실행 파일
│   ├── config.py             # 환경 설정 관리
│   ├── .env                  # DB 접속 정보 등 (Git 추적 안됨)
│   ├── requirements.txt      # 파이썬 의존성 목록
│   ├── optimizer/            # OR-Tools 최적화 엔진
│   │   ├── __init__.py
│   │   └── engine.py
│   └── services/             # 핵심 비즈니스 로직
│       ├── __init__.py
│       │── call_llm.py       # LLM 호출 로직
│       ├── db_handler.py     # 데이터베이스 핸들러
│       └── co2_calculator.py # CO2 배출량 계산기
└── .gitignore                # Git 무시 파일 (루트)
└── README.md                 # 프로젝트 설명서 (현재 파일)
```

## 🎯 현재 구현 상태

### ✅ 완료된 기능
- [x] 반응형 UI/UX 디자인
- [x] 자연어 입력 및 JSON 파싱 시뮬레이션
- [x] 폼 기반 배송 계획 입력
- [x] 카카오맵 플레이스홀더 및 컨트롤
- [x] 차트 기반 대시보드
- [x] CRUD 기반 데이터 관리
- [x] 더미 데이터 기반 완전 시연 환경
- [x] TypeScript 타입 안정성
- [x] 접근성 고려 (aria-label, 키보드 네비게이션)

### 🚧 향후 개발 예정
- [ ] 실제 LLM API 연동
- [ ] 카카오맵 SDK 통합
- [ ] 경로 최적화 알고리즘 백엔드 연동
- [ ] 실시간 차량 트래킹
- [ ] 사용자 인증 및 권한 관리
- [ ] 데이터베이스 연동
- [ ] 배포 및 CI/CD 파이프라인

## 🎨 디자인 시스템

### 색상 팔레트
- **Primary**: Green-600 (#16a34a) - 친환경 테마
- **Secondary**: Blue-600 (#2563eb) - 신뢰성
- **Accent**: Orange-500 (#f97316) - 강조
- **Success**: Green-500 (#22c55e) - 성공
- **Warning**: Amber-500 (#f59e0b) - 주의
- **Error**: Red-500 (#ef4444) - 오류

### 타이포그래피
- **Font**: Inter (Google Fonts)
- **Heading**: 24px-32px, font-bold
- **Body**: 14px-16px, font-normal
- **Caption**: 12px-14px, text-muted-foreground

## 📊 데이터 모델

### 주요 엔티티
- **Vehicle**: 차량 정보 (ID, 타입, 용량, 연료, 배출계수)
- **Sector**: 배송 섹터 (ID, 이름, 좌표, 시간창, 우선순위)
- **Job**: 배송 작업 (섹터, 날짜, 수요량, 시간창, 우선순위)
- **Route**: 경로 정보 (차량, 스텝, 거리, CO₂, 소요시간)

## 🔧 환경 설정
### Frontend
현재는 프론트엔드 목업으로 구현되어 있으며, 모든 데이터는 더미 데이터를 사용합니다.
실제 API 연결 시 다음 환경변수가 필요합니다:

```env
NEXT_PUBLIC_KAKAO_MAP_API_KEY=your_kakao_map_api_key
NEXT_PUBLIC_LLM_API_ENDPOINT=your_llm_api_endpoint
NEXT_PUBLIC_OPTIMIZATION_API_ENDPOINT=your_optimization_api_endpoint
```
### Backend
백엔드 실행 시 backend 폴더에 .env 파일을 생성하고 다음 환경변수가 필요합니다:

```env
DB_USER=your_oracle_username
DB_PASSWORD=your_oracle_password
DB_DSN=your_oracle_dsn

OPENROUTER_API_KEY=""
OPENROUTER_API_URL=""
REST_API_KEY=""
```

## 🤝 기여하기

1. 프로젝트를 Fork합니다
2. Feature 브랜치를 생성합니다 (`git checkout -b feature/AmazingFeature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 Push합니다 (`git push origin feature/AmazingFeature`)
5. Pull Request를 생성합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.
