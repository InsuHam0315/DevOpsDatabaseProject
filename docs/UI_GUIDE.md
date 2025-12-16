# UI 가이드

이 문서는 공통 UI 스타일과 컴포넌트 사용 원칙을 설명합니다.

## 디자인 토큰

- 색상 (README 참고):
  - Primary: Green-600 (#16a34a).
  - Secondary: Blue-600 (#2563eb).
  - Accent: Orange-500 (#f97316).
  - Success: Green-500 (#22c55e).
  - Warning: Amber-500 (#f59e0b).
  - Error: Red-500 (#ef4444).

- 타이포그래피:
  - 폰트: Inter.
  - Heading: 24~32px, `font-bold`.
  - Body: 14~16px, `font-normal`.
  - Caption: 12~14px, `text-muted-foreground`.

## 컴포넌트 사용 원칙

- `components/ui/*`: shadcn/ui 기반 공통 컴포넌트.
  - 버튼, 모달, 입력 폼 등을 여기서 재사용.
- `components/layout/*`: 페이지 레이아웃/헤더/사이드바 등.
  - 페이지별 중복되는 레이아웃은 여기에서 관리.

## 접근성

- 주요 인터랙티브 요소에 `aria-label` 등 적절한 속성 부여.
- 키보드로 모든 주요 기능에 접근 가능하도록 설계.

