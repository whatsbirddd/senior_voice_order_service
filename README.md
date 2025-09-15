# Voice-first Restaurant MVP

A minimal Flask + static web app that demonstrates a voice-driven flow:
1) Review summary → 2) Menu explore/recommend → 3) Map → 4) Mock payment.

## Quick Start

- Install deps:
  - `pip install -r voice_mvp/requirements.txt`
- Run server:
  - `python voice_mvp/server.py`
- Open in browser:
  - `http://localhost:5173/` (Chrome recommended for Web Speech API)

## Next.js (Figma UI) Frontend
- Location: `voice_mvp/src/` (Next.js App Router)
- API proxy: Next routes under `/app/api/*` proxy to Flask backend (default `http://localhost:5173`)
- Env (optional): set `NEXT_PUBLIC_BACKEND_BASE` or `BACKEND_BASE` to override backend URL
- Run (in a separate terminal):
  - `cd voice_mvp/src`
  - `npm install` (first time)
  - `npm run dev`
  - Open `http://localhost:3000/`

## Features
- Voice input (STT) via Web Speech API (ko-KR)
- TTS prompts via `speechSynthesis`
- API endpoints (mock data):
  - `GET /api/reviews?store=...`
  - `GET /api/menu?store=...`
  - `POST /api/recommend` { store, history }
  - `GET /api/place?store=...`
  - `POST /api/pay` { store, items }

## Agent
- Orchestrator endpoint:
  - `POST /api/agent` { sessionId, message, store?, history?, selectedNames? }
  - Response includes `reply`, `ui` (reviews/summary/menu/recommendations/mapUrl/payment), `state`
- Config endpoints:
  - `GET /api/agent/config` → current prompt, enabled/available tools
  - `POST /api/agent/config` { prompt?, enabledTools?[] }
- Memory endpoints:
  - `GET /api/agent/memory?sessionId=...`
  - `POST /api/agent/memory/clear` { sessionId }

## Notes
- Naver/Kakao APIs are not yet wired; endpoints return mock data.
- Map opens Naver Map search in a new tab (embedding may be restricted).
- Payment is a mock that returns success.

## Next Steps
- Wire real web search for reviews/menus (Naver/Kakao)
- Embed map with official SDK and coordinates
- Replace mock payment with PG sandbox (e.g., TossPayments) including Samsung Pay
- Persist user history to a DB, add auth
