# LifeOS Assistant — Agent Guide

Compact repo-specific context for OpenCode sessions.

## Project Overview

Personal assistant (Chat, Kanban, Reminders, RAG) restricted to a single Google account. Three semi-independent modules:

- `backend/` — FastAPI + async SQLAlchemy + pgvector
- `frontend/` — React 18 + TypeScript + Vite + Vanilla CSS
- `slack_bot/` — Slack Bolt (Socket Mode), forwards messages to backend `/chat/stream` (auth: `X-Service-Token`)
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

- **Alembic migrations** in `backend/migrations/`, run automatically by the FastAPI lifespan (`src/core/migrations.py`). A pre-migration database (tables but no `alembic_version`) is stamped at `0001` first. After changing models: `cd backend && alembic revision --autogenerate -m "..."`, then review the file.
- **Chat agent**: `backend/src/agent/` — `create_agent` (LangChain v1) with tools in `tools.py`, policies as middleware in `middleware.py`, history replay in `history.py`, stream mapping and persistence in `runner.py`. The stream contract is `specs/002-agent-loop/contracts/chat-stream.md`. Tools take the user from `runtime.context` (`AgentContext`), never from model arguments.
- **Auth**: `get_current_user` (`backend/src/core/auth.py`) guards `/chat/*` (JWT bearer or `X-Service-Token`). The tasks, documents and settings routers still use the first user in the DB.
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

- Backend uses `pytest-asyncio` in auto mode with one session-wide event loop (`pyproject.toml`).
- Tests run against `<DATABASE_URL db>_test` (or `TEST_DATABASE_URL`), rebuild its schema through the migrations, and truncate tables per test; `tests/conftest.py` refuses any database not named `*_test`. Create it once: `createdb lifeos_test`.
- Tests never call an LLM: provider keys are blanked, and agent tests script the model with `ScriptedChatModel` (`tests/agent_helpers.py::use_script`).
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

<!-- graft:start -->
## Graft — repo context graph

This repo is indexed in `graft/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `graft map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `graft ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
  definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `graft grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `graft skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `graft callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `graft/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `graft ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `graft build` (deterministic,
no API key, $0).
<!-- graft:end -->
