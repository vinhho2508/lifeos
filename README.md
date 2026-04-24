# LifeOS Assistant

Personal life assistant with Chat, Kanban Board, Reminders, and RAG.

## Features
- **Secure Access**: Restricted to authorized Google account.
- **Chat Interface**: Natural language task and reminder creation.
- **Kanban Board**: Visual task tracking (To-do, Working, Done).
- **RAG**: Document-based knowledge retrieval.
- **Slack Integration**: Manage tasks and receive reminders via Slack.

## Architecture
- **Backend**: FastAPI, SQLAlchemy, pgvector.
- **Frontend**: React, TypeScript, Vanilla CSS.
- **Bot**: Slack Bolt (Socket Mode).
- **Database**: PostgreSQL with pgvector.

## Setup
See `specs/001-lifeos-assistant/quickstart.md` for detailed instructions.
