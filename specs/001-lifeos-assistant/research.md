# Research: LifeOS Assistant Implementation

## Decision: Authentication & Authorization
- **Decision**: FastAPI with `fastapi-users` or standard OAuth2 password bearer using Google's public keys.
- **Rationale**: We must enforce a hardcoded check for `vinhho2508@gmail.com` after token validation.
- **Alternatives**: Auth0/Firebase (rejected to keep dependencies minimal for a personal project).

## Decision: Task/Reminder Extraction (NLP)
- **Decision**: Use a structured prompt with a small LLM (e.g., OpenAI/Claude) to extract `task_name`, `due_date`, and `priority`.
- **Rationale**: Natural language varies too much for simple regex. LLMs are highly reliable for this at low volume.
- **Alternatives**: Rule-based (rejected as too rigid).

## Decision: RAG Implementation
- **Decision**: PostgreSQL + pgvector via LangChain.
- **Rationale**: Simplifies the stack by using one database for both tasks and embeddings.
- **Alternatives**: Pinecone/Chroma (rejected to avoid extra external infrastructure).

## Decision: UI/UX (Kanban Board)
- **Decision**: React + Vanilla CSS (Flexbox/Grid).
- **Rationale**: Meets the user's requirement for "Vanilla HTML/CSS as much as possible" while maintaining React for state management.
- **Alternatives**: Drag-and-drop libraries (e.g., dnd-kit) will be used to ensure standard board interactions.

## Decision: Document Digestion Method
- **Decision**: Support both file upload (PDF/TXT) and text paste.
- **Rationale**: Provides maximum flexibility for the user as a life assistant.
- **Alternatives considered**: Text-only (too limiting for research).
