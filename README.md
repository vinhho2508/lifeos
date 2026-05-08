# LifeOS Assistant

Personal life assistant with AI-powered chat, Kanban task board, document Q&A, and Slack integration.

> **Note**: LifeOS is single-user. Access is restricted to one Google account configured via `ALLOWED_USER_EMAIL`.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.12), SQLAlchemy 2.0 async, pgvector |
| Frontend | React 18, TypeScript, Vite 5, Tailwind CSS 4, Radix UI |
| Slack Bot | Slack Bolt (Python), Socket Mode |
| Chrome Extension | React 18, TypeScript, Vite 5, Chrome Extension APIs |
| Database | PostgreSQL 16 + pgvector |
| AI | OpenAI GPT-4o, DALL·E 3, text-embedding-3-small |
| Auth | Google OAuth 2.0, JWT |
| Infra | Docker Compose, APScheduler, Alembic |

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
          ┌────────▼──────┐  ┌───▼──────────┐
          │  PostgreSQL   │  │    OpenAI     │
          │  + pgvector   │  │     API       │
          └───────────────┘  └──────────────┘
```

## Quick Start

### Prerequisites

- **Docker** — for PostgreSQL + pgvector
- **Python** 3.12+
- **Node.js** 20+

### 1. Start the database

```bash
git clone <repo-url> && cd lifeos
docker compose up -d
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

API runs on `http://localhost:8000`.

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

Requires `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, and `SLACK_SIGNING_SECRET`.

### 5. (Optional) Chrome Extension

```bash
cd chrome_extension
npm install && npm run build
```

Load `dist/` as an unpacked extension in `chrome://extensions/`. See [chrome_extension/README.md](chrome_extension/README.md).

## Environment Variables

### Required

| Variable | Purpose | File |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `backend/.env` |
| `OPENAI_API_KEY` | OpenAI key for chat, embeddings, images | `backend/.env` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | `backend/.env` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | `backend/.env` |
| `ALLOWED_USER_EMAIL` | Email of the single authorized user | `backend/.env` |
| `VITE_GOOGLE_CLIENT_ID` | Same Google OAuth client ID (exposed to browser) | `frontend/.env` |
| `VITE_API_URL` | Backend API base URL (default: `http://localhost:8000`) | `frontend/.env` |

### Optional

| Variable | Purpose | File |
|---|---|---|
| `SLACK_BOT_TOKEN` | Slack bot token for DM reminders | `backend/.env` |
| `SLACK_DM_USER_ID` | Slack user ID to receive DMs | `backend/.env` |
| `SLACK_SIGNING_SECRET` | Slack signing secret | `backend/.env` |
| `SLACK_APP_TOKEN` | Slack Socket Mode token | `slack_bot/.env` |
| `S3_BUCKET_NAME` | S3 bucket for file uploads | `backend/.env` |
| `AWS_REGION` | AWS region for S3 (default: `us-east-1`) | `backend/.env` |
| `SECRET_KEY` | JWT signing secret (default: `supersecretkey`) | `backend/.env` |

For the complete reference, see `specs/001-lifeos-assistant/quickstart.md`.

## Core Features

### AI Chat

Chat with the assistant through three surfaces:

- **Web**: Visit `/chat`, type a message, and receive streaming responses with markdown rendering, thinking indicators, citations, and generated images.
- **Slack**: Send a DM to the bot — responses stream back in real time.
- **Chrome Extension**: Select text on any page, click the floating LifeOS icon, and chat in the side panel.

### Kanban Task Board

Visit `/tasks` to manage tasks on a drag-and-drop board: **Todo → Working → Done**. Drag cards between columns or use the arrow buttons to change status.

### Task Extraction from Chat

Ask the AI to create a task — e.g. *"Remind me to call Mom at 6pm"*. The assistant extracts the task automatically via NLP and adds it to your board.

### Slack Integration

- **Chat**: DM the bot to access the assistant.
- **Task from message**: React to any Slack message with a 📌 (pushpin) emoji to create a task from it.
- **Reminders & Digests**: The bot sends hourly overdue-task reminders, a daily 9am morning digest, and crypto price updates every 6 hours. Requires `SLACK_BOT_TOKEN` and `SLACK_DM_USER_ID`.

### Document Q&A (RAG)

Upload `.txt` files in `/knowledge-base`. The backend chunks and embeds documents with `text-embedding-3-small` and stores vectors in pgvector. Ask questions about your documents in chat — answers cite source documents.

### Automated Reminders & Digests

APScheduler runs in-process within the backend:

| Schedule | Job |
|---|---|
| Hourly (`0 * * * *`) | Slack DM for each overdue, un-reminded task |
| Daily 9am (`0 9 * * *`) | Morning digest of all TODO and WORKING tasks |
| Every 6 hours (`0 */6 * * *`) | Top 10 cryptocurrency price update |

All require Slack to be configured.

### Chrome Extension

Select text on any webpage to reveal a floating LifeOS icon. Click it to open the side panel with two modes:

- **With Backend**: Connects to your running LifeOS backend. Requires you to be logged into the web app — the extension reads the JWT from `localStorage`.
- **Direct OpenAI**: Uses your own API key directly, no backend required.

Chat about selected text or click **"Add as Task"** to create a task from it. Local history is capped at 50 messages. See [chrome_extension/README.md](chrome_extension/README.md) for details.

### Dark / Light Theme

Toggle between dark and light themes using the sun/moon button in the sidebar. Your preference is persisted to `localStorage`.

## Further Documentation

- [specs/001-lifeos-assistant/quickstart.md](specs/001-lifeos-assistant/quickstart.md) — detailed setup and development workflow
- [chrome_extension/README.md](chrome_extension/README.md) — Chrome extension setup and architecture
- [AGENTS.md](AGENTS.md) — developer reference (commands, conventions, architecture notes)
