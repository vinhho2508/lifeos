# LifeOS Assistant

Personal life assistant with AI-powered chat, Kanban task board, document Q&A, and Slack integration.

> **Note**: LifeOS is single-user. Access is restricted to one Google account configured via `ALLOWED_USER_EMAIL`.

## Tech Stack

| Layer            | Technology                                                                                                                                         |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend          | FastAPI (Python 3.12), SQLAlchemy 2.0 async, pgvector                                                                                              |
| Frontend         | React 18, TypeScript, Vite 5, Tailwind CSS 4, Radix UI                                                                                             |
| Slack Bot        | Slack Bolt (Python), Socket Mode                                                                                                                   |
| Chrome Extension | React 18, TypeScript, Vite 5, Chrome Extension APIs                                                                                                |
| Database         | PostgreSQL 16 + pgvector                                                                                                                           |
| AI               | Tool-calling agent on LangChain v1 / LangGraph; OpenAI (default GPT-5.4 nano), Anthropic or Gemini for chat; GPT Image 1.5, text-embedding-3-small |
| Auth             | Google OAuth 2.0, JWT                                                                                                                              |
| Infra            | Docker Compose, APScheduler, Alembic                                                                                                               |

## Architecture

```
┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────┐
│   Web    │  │  Slack   │  │    Chrome    │  │   Cron   │
│ (React)  │  │   Bot    │  │  Extension   │  │Scheduler │
└────┬─────┘  └────┬─────┘  └──────┬───────┘  └────┬─────┘
     │             │               │               │
     └─────────────┼───────────────┼───────────────┘
                   │               │
            ┌──────▼───────────────▼──────┐
            │     FastAPI Backend         │
            │        (:8000)              │
            └──────┬──────────────┬──────┘
                   │              │
          ┌────────▼──────┐  ┌───▼──────────────────────┐
          │  PostgreSQL   │  │ OpenAI / Anthropic /     │
          │  + pgvector   │  │ Gemini                   │
          └───────────────┘  └──────────────────────────┘
```

### The chat agent

Every chat message (web, Slack, extension) runs a tool-calling loop in `backend/src/agent/`:

```
POST /chat/stream ─auth─▶ save user message ─▶ background run ──▶ queue ──▶ NDJSON stream
                                                   │
      create_agent(model, tools, middleware) ◀─────┘   history: last 20 messages, all platforms
        │  model ──▶ tool calls? ──yes──▶ tools ──▶ results back to the model ──▶ repeat
        │                          no ──▶ final answer
        ├─ tools: search_documents · create_task · list_tasks · update_task · generate_image
        └─ middleware: time-aware system prompt (user timezone) · per-tool timeout + errors
                       returned to the model · 8-step cap · provider retry on 429/5xx
```

- The model decides which tools to use; small talk never creates tasks.
- Each tool step streams to the client (`tool_call` / `tool_result` with a shared `id`) and is
  saved in the message, so follow-ups like "push it to Monday" work across platforms.
- Runs continue if the client disconnects; each completed step is saved as it happens.
- Without an API key for the selected provider, a scripted demo model drives the same tools.

Stream format: [specs/002-agent-loop/contracts/chat-stream.md](specs/002-agent-loop/contracts/chat-stream.md).
Design decisions: [specs/002-agent-loop/research.md](specs/002-agent-loop/research.md).

## Quick Start

### Prerequisites

- **Docker** — for PostgreSQL + pgvector
- **Python** 3.12+
- **Node.js** 20+

### 1. Start the database

```bash
git clone <repo-url> && cd lifeos
docker compose up -d db
```

PostgreSQL with pgvector runs on `localhost:5432` (credentials: `user` / `password` / `lifeos`).

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env      # edit .env with your keys (see table below)
uvicorn src.main:app --reload
```

API runs on `http://localhost:8000`. Database migrations (Alembic) run automatically at startup;
a database created by an older version is detected and upgraded in place.

Tests use a separate `<db>_test` database (created once with
`docker compose exec db createdb -U user lifeos_test`) and never call an LLM:

```bash
python -m pytest
```

To check tool choice against real providers (a few cents per provider; providers without a key
are skipped):

```bash
python -m scripts.agent_smoke_eval            # or: ... openai anthropic
```

To measure retrieval quality (recall@5 / MRR, vector-only vs hybrid, on `scripts/rag_eval_corpus/`;
needs `OPENAI_API_KEY`, costs well under a cent):

```bash
python -m scripts.rag_eval
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.sample .env      # add VITE_GOOGLE_CLIENT_ID and VITE_API_URL
npm run dev
```

Web UI runs on `http://localhost:5173`. The Vite dev server proxies `/api` requests to `:8000`.

### 4. (Optional) Slack Bot

```bash
cd slack_bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

Requires `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET`, and `SLACK_SERVICE_TOKEN`
(the same value as in `backend/.env`; the bot uses it to authenticate to the backend).

### Run everything in Docker

Instead of steps 1–4 you can run the database, backend, frontend and Slack bot as containers:

```bash
# backend/.env and slack_bot/.env are passed to the containers as-is
echo "VITE_GOOGLE_CLIENT_ID=<your-client-id>" > .env   # baked into the frontend build
docker compose up -d --build
```

- Web UI on `http://localhost:5173`. nginx serves the build and proxies `/api` to the backend.
- API on `http://localhost:8000`.
- `DATABASE_URL` and `BACKEND_URL` are set to the compose service names, so the
  `localhost` values in your `.env` files don't need to change.
- Uploaded originals are stored in the `uploads` volume (when `S3_BUCKET_NAME` is unset).
- If a port is already in use, override it with `DB_PORT`, `BACKEND_PORT` or `FRONTEND_PORT`.
- To run without the Slack bot: `docker compose up -d --build db backend frontend`.

### 5. (Optional) Chrome Extension

```bash
cd chrome_extension
npm install && npm run build
```

Load `dist/` as an unpacked extension in `chrome://extensions/`. See [chrome_extension/README.md](chrome_extension/README.md).

## Environment Variables

### Required

| Variable                | Purpose                                                                      | File            |
| ----------------------- | ---------------------------------------------------------------------------- | --------------- |
| `DATABASE_URL`          | PostgreSQL connection string                                                 | `backend/.env`  |
| `OPENAI_API_KEY`        | OpenAI key for chat, embeddings, images (without it, chat runs a demo model) | `backend/.env`  |
| `GOOGLE_CLIENT_ID`      | Google OAuth client ID                                                       | `backend/.env`  |
| `GOOGLE_CLIENT_SECRET`  | Google OAuth client secret                                                   | `backend/.env`  |
| `ALLOWED_USER_EMAIL`    | Email of the single authorized user                                          | `backend/.env`  |
| `SECRET_KEY`            | JWT signing secret; chat rejects JWTs while it is empty                      | `backend/.env`  |
| `VITE_GOOGLE_CLIENT_ID` | Same Google OAuth client ID (exposed to browser)                             | `frontend/.env` |
| `VITE_API_URL`          | Backend API base URL (default: `http://localhost:8000`)                      | `frontend/.env` |

### Optional

| Variable                                      | Purpose                                                        | File                                |
| --------------------------------------------- | -------------------------------------------------------------- | ----------------------------------- |
| `SLACK_BOT_TOKEN`                             | Slack bot token for DM reminders                               | `backend/.env`                      |
| `SLACK_DM_USER_ID`                            | Slack user ID to receive DMs                                   | `backend/.env`                      |
| `SLACK_SIGNING_SECRET`                        | Slack signing secret                                           | `backend/.env`                      |
| `SLACK_APP_TOKEN`                             | Slack Socket Mode token                                        | `slack_bot/.env`                    |
| `SLACK_SERVICE_TOKEN`                         | Shared secret the Slack bot uses to call `/chat/stream`        | `backend/.env` and `slack_bot/.env` |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`        | Keys for the other chat providers (pick one in Settings)       | `backend/.env`                      |
| `S3_BUCKET_NAME`                              | S3 bucket for generated images and document originals          | `backend/.env`                      |
| `UPLOAD_DIR`                                  | Local folder for document originals when S3 is unset           | `backend/.env`                      |
| `AWS_REGION`                                  | AWS region for S3 (default: `us-east-1`)                       | `backend/.env`                      |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | S3 / R2 access keys                                            | `backend/.env`                      |
| `S3_ENDPOINT_URL`                             | S3-compatible endpoint, e.g. Cloudflare R2 (`AWS_REGION=auto`) | `backend/.env`                      |
| `S3_PUBLIC_URL`                               | Public base URL for generated image links (R2 domain)          | `backend/.env`                      |

For the complete reference, see `specs/001-lifeos-assistant/quickstart.md`.

## Core Features

### AI Chat

Chat with the assistant through three surfaces:

- **Web**: Visit `/chat`, type a message, and receive streaming responses with markdown rendering, thinking indicators, citations, and generated images.
- **Slack**: Send a DM to the bot — responses stream back in real time.
- **Chrome Extension**: Select text on any page, click the floating LifeOS icon, and chat in the side panel.

### Kanban Task Board

Visit `/tasks` to manage tasks on a drag-and-drop board: **Todo → Working → Done**. Drag cards between columns or use the arrow buttons to change status.

### Tasks from Chat

Ask the assistant to add, list or change tasks — e.g. _"Remind me to call Mom at 6pm"_, _"what's
overdue?"_, _"mark the first one done"_. Relative dates resolve in the timezone set on the
Settings page (it defaults to your browser's timezone).

### Slack Integration

- **Chat**: DM the bot to access the assistant.
- **Task from message**: React to any Slack message with a 📌 (pushpin) emoji to create a task from it.
- **Reminders & Digests**: The bot sends hourly overdue-task reminders, a daily 9am morning digest, and crypto price updates every 6 hours. Requires `SLACK_BOT_TOKEN` and `SLACK_DM_USER_ID`.

### Document Q&A (RAG)

In `/knowledge-base`, upload `.txt`, `.md`, `.pdf` or `.html` files (up to 20 MB), or add a web page by URL. Uploads return immediately and are digested in the background. The list shows each document's status (queued, digesting, ready, failed with the reason), and you can re-index or delete documents there.

- **Ingest**: the original goes to S3 (when `S3_BUCKET_NAME` is set) or `UPLOAD_DIR`. It is parsed into sections (Markdown/HTML headings, PDF pages) and split into ~400-token chunks that keep their page and heading. The chunks are embedded with `text-embedding-3-small` in pgvector. Unfinished digests are resumed at startup and every 5 minutes.
- **Search**: hybrid retrieval. pgvector cosine (HNSW) and Postgres full-text results are fused with Reciprocal Rank Fusion, so exact codes and names are found too. Citations in chat show the document, page and section.
- **No key, no index**: without `OPENAI_API_KEY`, documents fail with a clear error instead of being indexed with placeholder vectors.

### Automated Reminders & Digests

APScheduler runs in-process within the backend:

| Schedule                      | Job                                          |
| ----------------------------- | -------------------------------------------- |
| Hourly (`0 * * * *`)          | Slack DM for each overdue, un-reminded task  |
| Daily 9am (`0 9 * * *`)       | Morning digest of all TODO and WORKING tasks |
| Every 6 hours (`0 */6 * * *`) | Top 10 cryptocurrency price update           |

All require Slack to be configured.

### Chrome Extension

Select text on any webpage to reveal a floating LifeOS icon. Click it to open the side panel with two modes:

- **With Backend**: Connects to your running LifeOS backend. Requires you to be logged into the web app — the extension reads the JWT from `localStorage`.
- **Direct OpenAI**: Uses your own API key directly, no backend required. Plain chat only: no tools.

Chat about selected text or click **"Add as Task"** to create a task from it. Local history is capped at 50 messages. See [chrome_extension/README.md](chrome_extension/README.md) for details.

### Dark / Light Theme

Toggle between dark and light themes using the sun/moon button in the sidebar. Your preference is persisted to `localStorage`.

## Further Documentation

- [specs/002-agent-loop/](specs/002-agent-loop/) — agent loop spec, design decisions, stream contract
- [specs/001-lifeos-assistant/quickstart.md](specs/001-lifeos-assistant/quickstart.md) — detailed setup and development workflow
- [chrome_extension/README.md](chrome_extension/README.md) — Chrome extension setup and architecture
- [AGENTS.md](AGENTS.md) — developer reference (commands, conventions, architecture notes)
