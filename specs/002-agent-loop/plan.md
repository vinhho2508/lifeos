# Implementation Plan: Tool-Calling Agent Loop

**Branch**: `002-agent-loop` | **Date**: 2026-10-09 | **Spec**: [specs/002-agent-loop/spec.md]
**Input**: Feature specification from `specs/002-agent-loop/spec.md`

## Summary

Replace the fixed chat pipeline with a LangChain v1 `create_agent` loop over five tools. Guardrails are implemented as middleware. The `messages` table stays the history store, and a Postgres checkpointer keeps one short-lived thread per run. The existing NDJSON stream is extended with paired tool blocks. The same change adds the user's timezone, minimal auth on `/chat/*`, and an Alembic baseline.

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x
**New/pinned dependencies**: `langchain>=1,<2`, `langgraph>=1,<2`, `langgraph-checkpoint-postgres`, `psycopg[binary,pool]>=3`, plus pins for the existing `langchain-openai`, `langchain-anthropic` and `langchain-google-genai`. Exact versions are checked against PyPI at implementation time.
**Storage**: PostgreSQL 16 + pgvector; LangGraph checkpoint tables in the same database.
**Testing**: pytest + `ScriptedChatModel` (no network); Vitest for `applyDelta`.
**Constraints**: Single user; the backend runs as exactly one process (cron runs in-process).

## Constitution Check

- [x] I. Code Quality: Each guardrail is a separate middleware; tools are thin wrappers over services.
- [x] II. Testing: Scripted-model tests for loop order, errors, max-steps, replay pairing and disconnect; 401 tests.
- [x] III. UX Consistency: One stream contract rendered by Web, Slack and the extension.
- [x] IV. Performance: Removing the always-on embedding call and the blocking `extract_task_info` saves one embedding call and one LLM call on most turns.
- [x] V. Simplicity: Uses the standard harness; no destructive tools or approval flow in v1.

## Architecture

```text
POST /chat/stream ──auth──▶ chat_stream()
                              │ create run_id, save USER message
                              ▼
                     asyncio.create_task(run_agent(...)) ──▶ asyncio.Queue ──▶ NDJSON generator ──▶ client
                              │                                         (client disconnect only stops draining)
                              ▼
          agent = create_agent(model, TOOLS, context_schema=AgentContext,
                               middleware=[TimeAwarePrompt, ToolGuard, StepCap, ModelRetry],
                               checkpointer=AsyncPostgresSaver)
          agent.astream({"messages": replay(last 20)}, context=AgentContext(...),
                        config={"thread_id": run_id}, stream_mode=["messages", "updates"])
                              │
                              ├─ model tokens  → text / thinking deltas
                              ├─ tool calls    → tool_call deltas   ┐ each completed step is
                              └─ tool results  → tool_result (+ citation / image) deltas ┘ saved to messages
```

## Project Structure

### Documentation (this feature)

```text
specs/002-agent-loop/
├── spec.md
├── plan.md               # This file
├── research.md           # Decisions and alternatives
├── data-model.md
├── contracts/chat-stream.md
└── tasks.md
```

### Source code (new and changed)

```text
backend/
├── alembic.ini, migrations/                # NEW baseline + 0002_timezone_and_tz_dates
├── src/
│   ├── agent/                              # NEW package
│   │   ├── __init__.py
│   │   ├── context.py                      # AgentContext dataclass
│   │   ├── tools.py                        # 5 tools; read runtime.context
│   │   ├── middleware.py                   # TimeAwarePrompt, ToolGuard, StepCap, ModelRetry
│   │   ├── history.py                      # stored blocks ⇄ LangChain messages (replay + pairing)
│   │   ├── runner.py                       # build agent, run in background task, map stream → ContentDelta
│   │   ├── checkpointer.py                 # AsyncPostgresSaver lifecycle + prune job
│   │   └── scripted_model.py               # ScriptedChatModel for tests and the no-key demo
│   ├── api/chat.py                         # CHANGED: auth, remove POST /chat/, use runner
│   ├── core/auth.py                        # CHANGED: get_current_user (JWT or service token)
│   ├── models/all_models.py                # CHANGED: UserSettings.timezone, tz-aware datetimes
│   ├── services/task_service.py            # CHANGED: update_task, list_tasks(filters)
│   ├── services/nlp.py                     # CHANGED: remove extract_task_info/stream_reply; keep ContentDelta
│   └── main.py                             # CHANGED: drop create_all, open checkpointer pool in lifespan
└── tests/
    ├── test_agent_loop.py, test_agent_history.py, test_agent_tools.py, test_chat_auth.py  # NEW
    ├── test_chat_tasks.py                  # REWRITTEN as an agent test
    └── test_nlp.py                         # CHANGED: extract_task_info tests removed
frontend/src/
├── types/chat.ts                           # CHANGED: id/status/summary, optional delta, done/error
├── components/Chat/Chat.tsx                # CHANGED: applyDelta pairs results by id
├── components/Chat/MessageBubble.tsx       # CHANGED: collapsible ToolStep card
└── pages/SettingsPage.tsx                  # CHANGED: timezone field
slack_bot/src/main.py                       # CHANGED: X-Service-Token, show summary not output
chrome_extension/popup/Settings.tsx         # CHANGED: "no tools" label on direct mode
```

## Phasing

1. **Foundations**: Alembic baseline, timezone and tz-aware dates, `get_current_user`, task-service functions.
2. **Agent core**: context, tools, history replay, middleware, runner, scripted model, all with tests.
3. **Endpoint swap**: `/chat/stream` uses the runner; delete `POST /chat/`, `extract_task_info` and `stream_reply`.
4. **Clients**: Web tool cards, Slack summaries and service token, extension label, timezone setting.
5. **Verification**: Per-provider smoke evals, README update.

## Risks

| Risk | Mitigation |
|---|---|
| Unpaired tool calls in replayed history make Anthropic or Gemini reject requests | `history.py` drops unpaired calls; dedicated tests run under each provider's message validation |
| psycopg 3 pool alongside asyncpg | Small pool (max 2), opened and closed in the FastAPI lifespan |
| Gemini or Anthropic stream tool-call chunks differently from OpenAI | Emit `tool_call` only from completed `updates`, never from partial chunks |
| Background runs outliving a redeploy | The run is saved step by step; an interrupted run ends with `stop_reason: error` on the next startup sweep |
| `create_all` removal breaks fresh setups | The baseline migration matches the current models exactly; quickstart updated to `alembic upgrade head` |
