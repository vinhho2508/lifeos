# Tasks: LifeOS Assistant

**Input**: Design documents from `specs/001-lifeos-assistant/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md, research.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

## Phase 1: Setup

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure for `backend/`, `frontend/`, and `slack_bot/` per implementation plan
- [x] T002 [P] Initialize FastAPI project in `backend/` with dependencies (SQLAlchemy, pgvector, etc.)
- [x] T003 [P] Initialize React project in `frontend/` with TypeScript and dependencies
- [x] T004 [P] Configure linting and formatting for both backend and frontend

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T005 Setup PostgreSQL with pgvector extension in `docker-compose.yml`
- [x] T006 Implement database connection and base models in `backend/src/models/` (User, Task, Document, Message)
- [x] T007 [P] Implement core error handling and logging in `backend/src/core/`
- [x] T008 [P] Setup basic API routing structure in `backend/src/api/`

## Phase 3: User Story 1 - Secure Personal Access (Priority: P1) 🎯 MVP

**Goal**: Restrict access to the authorized Google account only.

**Independent Test**: Verify that only `vinhho2508@gmail.com` can log in.

### Tests for User Story 1

- [x] T009 [P] [US1] Create integration test for Google OAuth callback in `backend/tests/test_auth.py`
- [x] T010 [P] [US1] Create unit test for email authorization check in `backend/tests/test_auth_logic.py`

### Implementation for User Story 1

- [x] T011 [US1] Implement Google OAuth2 login flow in `backend/src/api/auth.py`
- [x] T012 [US1] Implement email restriction check (`vinhho2508@gmail.com`) in `backend/src/core/auth.py`
- [x] T013 [US1] Create basic login page in `frontend/src/pages/Login.tsx`
- [x] T014 [US1] Setup JWT token storage and authenticated API client in `frontend/src/services/api.ts`

**Checkpoint**: User Story 1 complete - system is secured.

## Phase 4: User Story 2 - Chat-based Task & Reminder Management (Priority: P1) 🎯 MVP

**Goal**: Capture tasks and reminders through natural language chat.

**Independent Test**: Add a task via chat and verify it appears in the database and triggers a reminder.

### Tests for User Story 2

- [x] T015 [P] [US2] Create unit test for NLP task extraction in `backend/tests/test_nlp.py`
- [x] T016 [P] [US2] Create integration test for task creation via chat in `backend/tests/test_chat_tasks.py`

### Implementation for User Story 2

- [x] T017 [US2] Implement LLM-based task/reminder extraction service in `backend/src/services/nlp.py`
- [x] T018 [US2] Create task management service in `backend/src/services/task_service.py`
- [x] T019 [US2] Implement chat endpoint (`/chat`) in `backend/src/api/chat.py`
- [x] T020 [US2] Build chat interface component with Vanilla CSS in `frontend/src/components/Chat/`
- [x] T021 [US2] Implement background reminder worker using `APScheduler` or similar in `backend/src/services/reminder_worker.py`

**Checkpoint**: User Story 2 complete - tasks can be managed via chat.

## Phase 5: User Story 5 - Document Digestion & Knowledge Retrieval (RAG) (Priority: P1) 🎯 MVP

**Goal**: Upload documents and ask questions about their content.

**Independent Test**: Upload a file, ask a question, and receive an accurate answer based on the file.

### Tests for User Story 5

- [x] T022 [P] [US5] Create unit test for document chunking and embedding in `backend/tests/test_rag.py`
- [x] T023 [P] [US5] Create integration test for RAG query flow in `backend/tests/test_rag_flow.py`

### Implementation for User Story 5

- [x] T024 [US5] Implement document upload and text digestion endpoints in `backend/src/api/documents.py`
- [x] T025 [US5] Implement RAG service using LangChain and pgvector in `backend/src/services/rag_service.py`
- [x] T026 [US5] Integrate RAG query capability into the `/chat` endpoint logic
- [x] T027 [US5] Create document management UI in `frontend/src/components/Documents/Documents.tsx`

**Checkpoint**: User Story 5 complete - RAG capability is functional.

## Phase 6: User Story 3 - Visual Task Board (Priority: P2)

**Goal**: Visualize and manage tasks using a Kanban-style board.

**Independent Test**: Move a task between columns in the UI and verify its status update.

### Tests for User Story 3

- [x] T028 [P] [US3] Create frontend test for board drag-and-drop in `frontend/tests/Board.test.tsx`
- [x] T029 [P] [US3] Create integration test for task status update API in `backend/tests/test_tasks_api.py`

### Implementation for User Story 3

- [x] T030 [US3] Implement CRUD endpoints for tasks in `backend/src/api/tasks.py`
- [x] T031 [US3] Create Kanban board layout with "To-do", "Working", and "Done" columns in `frontend/src/components/Board/`
- [x] T032 [US3] Implement drag-and-drop logic for task status transitions
- [x] T033 [US3] Sync board state with backend task updates

**Checkpoint**: User Story 3 complete - visual task board is functional.

## Phase 7: User Story 4 - Slack Integration (Priority: P2)

**Goal**: Interact with the assistant via Slack.

**Independent Test**: Send a Slack message and verify the task is created in the web UI.

### Tests for User Story 4

- [x] T034 [P] [US4] Create unit test for Slack event signature validation in `slack_bot/tests/test_slack_auth.py`
- [x] T035 [P] [US4] Create integration test for Slack message to internal chat routing in `slack_bot/tests/test_slack_routing.py`

### Implementation for User Story 4

- [x] T036 [US4] Initialize Slack Bolt app in `slack_bot/src/main.py`
- [x] T037 [US4] Implement Slack event handler for messages and mentions
- [x] T038 [US4] Implement proxy logic to call backend `/chat` endpoint from Slack bot
- [x] T039 [US4] Implement Slack notification delivery for reminders in `backend/src/services/reminder_worker.py`

**Checkpoint**: User Story 4 complete - Slack integration is functional.

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final refinements and cross-interface consistency.

- [x] T040 Implement persistent chat history retrieval in `backend/src/api/chat.py`
- [x] T041 [P] Refine Vanilla CSS styles across all components for a polished "LifeOS" aesthetic
- [x] T042 [P] Final documentation update in `README.md` and `docs/`
- [x] T043 Perform end-to-end validation of the entire flow (Login -> Chat -> Board -> Slack -> RAG)

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1. BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Phase 2.
  - US1 (Phase 3) BLOCKS all other stories (auth required).
  - US2 (Phase 4) and US5 (Phase 5) can run in parallel after US1.
  - US3 (Phase 6) depends on US2 (needs tasks to display).
  - US4 (Phase 7) depends on US2 (needs chat logic).
- **Polish (Final Phase)**: Depends on all user stories.

### Parallel Opportunities

- T002, T003, T004 (Setup)
- T007, T008 (Foundational)
- All test tasks marked [P] can run in parallel with their respective implementation tasks
- US2 and US5 can be implemented in parallel after US1 is done

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Setup & Foundational.
2. Complete US1 (Auth) - **CRITICAL**.
3. Complete US2 (Chat Tasks) & US5 (RAG).
4. **VALIDATE MVP**: Secure personal assistant with chat tasking and RAG.

### Incremental Delivery

1. Add US3 (Kanban Board) for visual tracking.
2. Add US4 (Slack Integration) for accessibility.
3. Final Polish.
