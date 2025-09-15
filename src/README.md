# 음성 주문 앱 (Voice Order App)

노인분들을 위한 간단하고 직관적인 음성 기반 음식점 주문 앱입니다.

## 🚀 주요 특징

- **음성 + 터치 지원**: 음성 명령과 터치 모두 지원
- **단계별 안내**: 4단계로 나누어진 명확한 주문 과정
- **큰 글자와 버튼**: 노인분들이 사용하기 편한 UI/UX
- **아름다운 디자인**: 모던한 다크 테마와 그라데이션 카드
- **직관적 네비게이션**: 이전 단계로 돌아가기 기능

## 📱 주문 과정

1. **환영 단계** - 서비스 소개 (골드 그라데이션)
2. **메뉴 추천** - 메뉴 탐색 및 선택 (핑크 그라데이션)
3. **수량 선택** - 주문 수량 조절 (블루 그라데이션)
4. **주문 확인** - 최종 확인 및 주문 (그린 그라데이션)

## 🛠️ 기술 스택

- **Framework**: Next.js 15.1.4 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide React
- **Images**: Unsplash API

## 🏃‍♂️ 시작하기

### 개발 환경 실행

```bash
npm install
npm run dev
```

http://localhost:3000에서 앱을 확인할 수 있습니다.

### 빌드

```bash
npm run build
npm start
```

## 📁 프로젝트 구조

```
├── app/
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── VoiceOrderScreen.tsx
│   ├── OrderCompleteScreen.tsx
│   ├── figma/
│   │   └── ImageWithFallback.tsx
│   └── ui/
│       └── (shadcn components)
├── next.config.js
├── package.json
├── tailwind.config.js
└── tsconfig.json
```

## 🎨 디자인 시스템

- **컬러 팔레트**: 다크 테마 기반
- **그라데이션**: 각 단계별 고유 색상
- **둥근 모서리**: 40px 반지름의 부드러운 디자인
- **백드롭 블러**: 깊이감 있는 시각 효과

## 📝 사용법

1. "주문 시작하기" 버튼을 클릭하거나 "주문할게요"라고 말하세요
2. 좌우 화살표로 메뉴를 탐색하고 원하는 메뉴를 선택하세요
3. +/- 버튼으로 수량을 조절하세요
4. 최종 확인 후 주문을 완료하세요

## 🔧 향후 개선 사항

- [ ] 실제 음성 인식 API 연동
- [ ] 결제 시스템 통합
- [ ] 다국어 지원
- [ ] 접근성 개선
- [ ] PWA 지원

---

이 앱은 노인분들의 디지털 접근성을 고려하여 설계되었습니다. 🧓💙