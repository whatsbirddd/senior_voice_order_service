# 시니어 음성 주문 MVP (Voice-first Restaurant)

음성으로 매장 소개 → 추천 → 메뉴 선택 → 수량/요약 → 모의 결제를 진행하는 풀스택 MVP입니다.
- 백엔드: FastAPI + Azure OpenAI(에이전트) + Azure Speech(STT/Whisper 대체)
- 프론트: Next.js(App Router) + Azure Speech SDK(브라우저 STT/TTS)

**구성 요약**
- 백엔드: `voice_mvp/fastapi_app/main.py`
- 에이전트: `voice_mvp/agent/` (도구: `voice_mvp/agent/tools.py`, 프롬프트: `voice_mvp/agent/prompt.py`)
- 프론트: `voice_mvp/src/` (UI: `voice_mvp/src/components/VoiceOrderScreen.tsx`)
- 샘플 메뉴: `voice_mvp/data/oxoban_menu.json`

## 빠른 시작

1) Python 백엔드 실행
- 권장: Python 3.10+ 가상환경 생성 후 의존성 설치
  - `pip install -r senior_voice_order_service/fastapi_app/requirements.txt`
- 환경변수 설정(필요 시 아래 [환경 변수] 참고)
- 개발 서버 실행
  - `uvicorn senior_voice_order_service.fastapi_app.main:app --reload --port 8000`
  - .env를 인식하지 못한다면, fastapi_app에 .env를 추가하고 fastapi_app 에서 `uvicorn main:app --reload --port 8000` 를 실행하세요.

2) Next.js 프론트 실행 (별도 터미널)
- `cd voice_mvp/src`
- `npm install`
- (선택) `.env.local`에 백엔드 주소와 음성키 설정
  - `NEXT_PUBLIC_BACKEND_BASE=http://localhost:8000`
  - `SPEECH_SUBSCRIPTION_KEY=<Azure Speech 키>`
  - `AZURE_SPEECH_REGION=<예: eastus>`
- 개발 서버 실행: `npm run dev`
- 브라우저: http://localhost:3000

## 환경 변수

백엔드(FastAPI)
- `AZURE_OPENAI_API_KEY` 또는 `AZURE_OPENAI_KEY`
- `AZURE_OPENAI_ENDPOINT` (예: https://{resource}.openai.azure.com/)
- `AZURE_OPENAI_DEPLOYMENT` (배포 이름)
- `AZURE_OPENAI_API_VERSION` (기본: 2024-08-01-preview)
- 음성 인식(선택): `AZURE_SPEECH_KEY` 또는 `SPEECH_KEY`, `AZURE_SPEECH_REGION` 또는 `SPEECH_REGION`
- 오디오 전사(선택, Whisper/GPT-4o-transcribe): `AUDIO_OPENAI_ENDPOINT`, `AUDIO_OPENAI_DEPLOYMENT`, `AUDIO_OPENAI_API_VERSION`

프론트(Next.js)
- `NEXT_PUBLIC_BACKEND_BASE` 또는 `BACKEND_BASE` (백엔드 베이스 URL)
- 브라우저 STT/TTS 토큰 발급용: `SPEECH_SUBSCRIPTION_KEY`, `AZURE_SPEECH_REGION`

## 주요 기능
- 음성 입출력: 브라우저 Azure Speech SDK(STT/TTS), 백엔드 전사 API(대체)
- 에이전트: Azure OpenAI 함수 호출로 도구 자동 선택/실행
  - 리뷰 수집: DuckDuckGo → 네이버 블로그/지도 등 스니펫 수집
  - 간이 영양정보 추정: 검색 스니펫에서 kcal/나트륨/당/단백질 추정
  - 카탈로그/결제/지도 링크 등 로컬 도구
- 시니어 친화 프롬프트/액션: `SHOW_RECOMMENDATIONS`, `SELECT_MENU_BY_NAME`, `SET_QTY`, `ORDER` 등

## API 개요 (백엔드, 포트 8000)
- `GET /health` 런타임 헬스체크
- `GET /api/menu?store=...` 메뉴/대표메뉴 응답
- `POST /api/menu/import` 카탈로그 업서트(JSON: store, menu[], featured)
- `GET /api/reviews?store=...` 리뷰 요약(간이)
- `POST /api/pay` 모의 결제 합계 계산
- `POST /agent/chat` 에이전트 대화 엔드포인트
- `POST /api/agent` 기존 UI 호환 엔드포인트(동일 동작)
- `POST /api/audio/transcribe` 파일 전사(Azure Speech 또는 Azure OpenAI 구성 시)
- `POST /api/samsung-pay` 샘플 응답(모의)
- 사용자 프로필: `GET /user/profile`, `POST /user/profile/upsert`, `GET /user/history`

프론트 프록시(Next.js)
- `/app/api/*` 경로에서 백엔드로 프록시: 예) `src/app/api/agent/route.ts`

## 데이터/카탈로그
- 서버 부팅 시 `voice_mvp/data/oxoban_menu.json`을 자동 로드합니다. 다른 매장을 쓰려면 Import API 사용:
  - `bash voice_mvp/scripts/import_oxoban.sh` (기본 프론트 프록시로 POST)
  - 또는 직접: `curl -X POST http://localhost:8000/api/menu/import -H 'Content-Type: application/json' --data-binary @voice_mvp/data/oxoban_menu.json`

## 개발 팁
- 백엔드 실행 진입점: `voice_mvp/fastapi_app/main.py:1`
- 에이전트 로직: `voice_mvp/agent/core.py:1`, 도구 정의: `voice_mvp/agent/tools.py:1`
- 프론트 메인 화면: `voice_mvp/src/components/VoiceOrderScreen.tsx:1`
- 백엔드 URL 변경은 프론트 `.env.local`의 `NEXT_PUBLIC_BACKEND_BASE`로 제어

## 트러블슈팅
- LLM 미구성: 응답에 "LLM not available" 로그가 보이면 Azure OpenAI 환경변수를 설정하세요.
- STT/TTS 미구성: 브라우저 음성 토큰(`/src/app/api/audio/transcribe`) 발급을 위해 `SPEECH_SUBSCRIPTION_KEY`와 `AZURE_SPEECH_REGION`을 설정하세요.
- CORS: 기본으로 `*` 허용. 프록시 없이 직접 호출 시 백엔드 포트/도메인을 환경변수로 맞춰주세요.

## 라이선스
내부 해커톤/프로토타입 용도. 별도 고지 전까지 상용 사용 금지.
