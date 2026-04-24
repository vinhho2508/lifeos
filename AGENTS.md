# LifeOS Assistant — Agent Guide

Compact repo-specific context for OpenCode sessions.

## Project Overview

Personal assistant (Chat, Kanban, Reminders, RAG) restricted to a single Google account. Three semi-independent modules:

- `backend/` — FastAPI + async SQLAlchemy + pgvector
- `frontend/` — React 18 + TypeScript + Vite + Vanilla CSS
- `slack_bot/` — Slack Bolt (Socket Mode), forwards messages to backend `/chat/`
- `specs/001-lifeos-assistant/` — Feature spec, plan, quickstart, and data model

## Critical Commands

### Backend
```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload   # dev server on :8000
pytest                          # run tests (needs DB running)
ruff check .                    # lint
ruff check --fix .              # auto-fix
ruff format .                   # format
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # Vite dev server on :5173
npm run build    # tsc && vite build
npm run lint     # eslint . --ext ts,tsx
```

### Slack Bot
```bash
cd slack_bot
source venv/bin/activate
python src/main.py
```

### Database
```bash
docker-compose up -d   # pgvector/pgvector:pg16 on :5432
```

## Architecture Notes

- **No Alembic migrations yet**: `backend/src/main.py` calls `Base.metadata.create_all()` on startup. Do not look for migration scripts.
- **Async SQLAlchemy 2.0 everywhere**: `create_async_engine`, `AsyncSession`, `mapped_column`, `Mapped[...]`. Never use sync engines or `session.query()`.
- **Single-user hardcode**: Auth allows only `vinhho2508@gmail.com` via `ALLOWED_USER_EMAIL` in `backend/src/core/database.py` (`Settings`).
- **Backend auto-creates `vector` extension** on startup (`CREATE EXTENSION IF NOT EXISTS vector`).
- **Frontend proxy**: Vite config proxies `/api` → `http://localhost:8000`. Frontend `api.ts` uses `baseURL: '/api'`, so backend must be on `:8000` during dev.
- **No CI / pre-commit / GitHub Actions** in this repo.

## Environment Variables

`.env.sample` files are empty. Required keys are documented in `specs/001-lifeos-assistant/quickstart.md`. Key vars:

- `DATABASE_URL` — used by backend (auto-prefixed with `postgresql+asyncpg://` if needed)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ALLOWED_USER_EMAIL`
- `OPENAI_API_KEY` — RAG embeddings and chat
- `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_APP_TOKEN` (bot)
- `VITE_API_URL` — frontend build target
- `VITE_GOOGLE_CLIENT_ID` — frontend Google login

Backend loads `.env` from cwd via `pydantic-settings` (`env_file=".env"`). Run backend commands from `backend/` so it picks up `backend/.env`.

## Testing Quirks

- Backend uses `pytest-asyncio` (`@pytest.mark.asyncio`).
- Tests instantiate the real FastAPI app (`from src.main import app`) and use `httpx.AsyncClient`. They require a running PostgreSQL database (no in-memory override).
- Frontend has **no test framework installed yet** despite `plan.md` mentioning Vitest. `frontend/package.json` has no test script.

## Style & Linting

- **Backend**: Ruff (`pyproject.toml`). Line length 100, target `py312`, isort `known-first-party = ["src"]`.
- **Frontend**: Prettier config at repo root (`semi: false`, `singleQuote: true`, `trailingComma: all`, `printWidth: 100`). ESLint in `frontend/.eslintrc.cjs` (strict TS, react-hooks, react-refresh).
- **TypeScript**: `tsconfig.json` has `noUnusedLocals` and `noUnusedParameters` enabled.

## Entrypoints

- Backend API: `backend/src/main.py`
- Frontend app: `frontend/src/main.tsx`
- Slack bot: `slack_bot/src/main.py`
- API routes wired in `backend/src/api/router.py`

## Speckit / Gemini Workflow

This repo was bootstrapped with Speckit. If extending the spec-driven workflow, see:
- `GEMINI.md` — short pointer to the current plan
- `specs/001-lifeos-assistant/plan.md` — implementation plan and constitution checks
- `.specify/` and `.gemini/` — workflow templates and commands

When adding a new major feature, follow the existing `specs/001-lifeos-assistant/` structure or create a new `specs/XXX-feature-name/` directory.
