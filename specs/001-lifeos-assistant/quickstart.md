# Quickstart: LifeOS Assistant

## Prerequisites
- **Python**: 3.12+
- **Node.js**: 20+
- **Docker**: For running PostgreSQL + pgvector
- **Google Cloud Console**: OAuth Client ID and Secret for `vinhho2508@gmail.com`
- **Slack Workspace**: For app installation and bot token

## Environment Variables
Create a `.env` file in the root with:
```env
# Backend
DATABASE_URL=postgresql://user:password@localhost:5432/lifeos
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
ALLOWED_USER_EMAIL=vinhho2508@gmail.com
OPENAI_API_KEY=... # For RAG embeddings and Chat
SLACK_BOT_TOKEN=...
SLACK_SIGNING_SECRET=...

# Frontend
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=...
```

## Running Locally

### 1. Database
```bash
docker run -d --name lifeos-db -p 5432:5432 -e POSTGRES_PASSWORD=password pgvector/pgvector:pg16
```

### 2. Backend (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

### 3. Frontend (React)
```bash
cd frontend
npm install
npm run dev
```

### 4. Slack Bot (Optional if testing Slack)
```bash
cd slack_bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

## Development Workflow
1. Log in via Google UI (must use `vinhho2508@gmail.com`).
2. Add a task via chat: "Remind me to call Mom at 6pm".
3. Check the Kanban board to see the new task in "To-do".
4. Upload a document and ask a question: "What is the summary of this document?".
