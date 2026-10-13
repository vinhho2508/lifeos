# Tasks: Tool-Calling Agent Loop

**Input**: Design documents from `specs/002-agent-loop/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/chat-stream.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)

## Phase 1: Setup

- [x] T001 Pin `langchain`, `langgraph`, `langgraph-checkpoint-postgres`, `psycopg[binary,pool]` and the three provider packages in `backend/requirements.txt` (check current versions on PyPI)
- [x] T002 Initialize Alembic in `backend/` and generate a baseline migration matching `backend/src/models/all_models.py`
- [x] T003 Replace `Base.metadata.create_all` in `backend/src/main.py` with migrations; update `specs/001-lifeos-assistant/quickstart.md` and the README setup steps

## Phase 2: Foundational (blocks all stories)

- [x] T004 [US5] Add `get_current_user` (JWT bearer or `X-Service-Token` → `ALLOWED_USER_EMAIL`) in `backend/src/core/auth.py`
- [x] T005 [P] [US5] Tests: 401 without or with a bad token, 200 with JWT, 200 with service token in `backend/tests/test_chat_auth.py`
- [x] T006 Migration `0002`: `user_settings.timezone`, tz-aware `tasks.due_date` and `created_at`; update the models; replace `utcnow()` in the task paths
- [x] T007 [P] Add `update_task` and `list_tasks(status, overdue_only, limit)` to `backend/src/services/task_service.py`; make `backend/src/api/tasks.py` PUT use `update_task`
- [x] T008 [P] Add `AgentContext` in `backend/src/agent/context.py`
- [x] T009 [P] Add `ScriptedChatModel` (fake chat model plus a `bind_tools` override) in `backend/src/agent/scripted_model.py`

**Checkpoint**: Auth enforced on `/chat/*`; schema migrated; agent package scaffolded.

## Phase 3: US1 — The assistant decides what to do (P1) 🎯 MVP

### Tests

- [x] T010 [P] [US1] Tool unit tests (user isolation, unknown `task_id` → error, timezone parsing of `due_date`) in `backend/tests/test_agent_tools.py`
- [x] T011 [P] [US1] Loop tests with the scripted model: no-tool reply; `list_tasks` → `update_task` chain; event order `tool_call, tool_result, text, done` in `backend/tests/test_agent_loop.py`
- [x] T012 [P] [US1] Rewrite `backend/tests/test_chat_tasks.py`: "hi" creates no task; "remind me ..." creates exactly one

### Implementation

- [x] T013 [US1] Implement the 5 tools in `backend/src/agent/tools.py`, reading `user_id` and timezone from the runtime context
- [x] T014 [US1] Implement `TimeAwarePrompt` (dynamic system prompt) in `backend/src/agent/middleware.py`
- [x] T015 [US1] Implement `backend/src/agent/runner.py`: build `create_agent`, map the stream to `ContentDelta` (tool_call / tool_result / citation / image / text / done)
- [x] T016 [US1] Swap `/chat/stream` to the runner; delete `POST /chat/`, `extract_task_info` and `stream_reply`; trim `backend/tests/test_nlp.py`
- [x] T017 [US1] Use `ScriptedChatModel` with a demo script when the provider has no API key

**Checkpoint**: The agent chooses tools; "hi" no longer creates tasks.

## Phase 4: US2 — I can see what the agent did (P1)

- [x] T018 [P] [US2] Update `frontend/src/types/chat.ts` per the contract (`id`, `status`, `summary`, optional `delta`, `done`, `error`)
- [~] T019 [US2] Pair `tool_result` with its `tool_call` by `id` — done at render time in `MessageBubble.tsx` (`applyDelta` stores both blocks). Vitest test not added: the frontend has no test runner installed
- [x] T020 [US2] Collapsible ToolStep card in `frontend/src/components/Chat/MessageBubble.tsx`
- [x] T021 [P] [US2] Slack: show `summary` instead of `output`, send `X-Service-Token`, in `slack_bot/src/main.py`; update `slack_bot/tests`
- [x] T022 [US2] Save tool and citation blocks into `messages.content`; check that history reload renders the same cards

## Phase 5: US3 — Follow-ups work across platforms (P1)

- [x] T023 [P] [US3] Replay tests: tool pairs rebuilt, unpaired call dropped, image and thinking blocks dropped, truncation, cross-platform ordering, in `backend/tests/test_agent_history.py`
- [x] T024 [US3] Implement `backend/src/agent/history.py` (last 20 messages → LangChain messages)
- [x] T025 [US3] Timezone setting in `frontend/src/pages/SettingsPage.tsx` (default from the browser) and in the settings API

## Phase 6: US4 — The agent fails gracefully (P2)

- [x] T026 [P] [US4] Tests: tool exception → error result plus model recovery; timeout; max_steps stop; provider 429 retry; disconnect leaves consistent history
- [x] T027 [US4] Implement `ToolGuard` (20 s timeout, errors returned as ToolMessages), `StepCap(8)` and `ModelRetry(2)` in `backend/src/agent/middleware.py`
- [~] T028 [US4] Background `asyncio.Task` + `Queue` in the runner; save each step as it completes. Startup sweep not implemented: an interrupted run keeps its saved steps, and replay drops any unpaired tool call
- [x] T029 [US4] `AsyncPostgresSaver` lifecycle in `backend/src/agent/checkpointer.py` (lifespan pool, `setup()`, daily job to prune threads older than 7 days)

## Phase 7: Polish & cross-cutting

- [x] T030 [P] Chrome extension: label direct-OpenAI mode "no tools" in `chrome_extension/popup/Settings.tsx`
- [x] T031 [P] Per-provider smoke eval script (OpenAI, Anthropic, Gemini): non-actionable set, create-for-Friday-9am, document question, list→update chain
- [x] T032 Update `README.md`: agent architecture diagram, tool list, stream contract link, multi-provider note
- [ ] T033 Follow-ups (not in this feature): run cron jobs in the user's timezone; auth on the tasks/documents/settings routers; HITL with `delete_task`

## Dependencies

- Phase 1 → Phase 2 → US1. US2 needs US1's stream; US3 needs T013–T015; US4 can start after T015.
- US2 frontend tasks (T018–T020) and US3 history tests (T023) can run in parallel.

## Implementation notes (2026-10-09)

Deviations from the plan, decided while implementing:

- **Built-in middleware where it exists.** The step cap and provider retry use LangChain's
  `ModelCallLimitMiddleware(run_limit=8, exit_behavior="end")` and
  `ModelRetryMiddleware(on_failure="error", retry_on=is_retryable_provider_error)`. Only
  `ToolGuard` (timeout and error-to-ToolMessage) and the time-aware prompt are custom.
- **`generate_image` timeout is 120 s**, not 20 s: GPT Image generation routinely takes longer.
  Other tools use 20 s (`TOOL_TIMEOUTS` in `src/agent/tools.py`).
- **`extract_task_info` is kept for the Slack 📌 reaction** (`/tasks/from-message`), rewritten as
  async, timezone-aware and using structured output. Chat no longer uses it (FR-003 holds for chat).
- **Tool outputs travel as tool artifacts** (`response_format="content_and_artifact"`): the model
  reads compact `content`; the UI gets `summary`, `output`, citations and images from the artifact.
  Image URLs (possibly multi-megabyte data URLs) never reach the model.
- **Chrome extension backend mode was not updated.** Its API client (`chrome_extension/src/lib/`)
  is matched by the root `.gitignore` rule `lib/`, so it is not in the repo or this checkout.
  Only the "no tools" label on direct mode shipped (T030).
- **Verification**: 44 backend tests (scripted model, no network); legacy-database upgrade tested on
  a schema built by the old `create_all`; `scripts/agent_smoke_eval.py` passed 6/6 on OpenAI
  `gpt-5.4-nano`. Anthropic and Gemini were not run (no API keys configured).
