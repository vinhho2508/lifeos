# Research: Tool-Calling Agent Loop

Decisions were made in a design review on 2026-10-09. LangChain/LangGraph API facts were checked against docs.langchain.com that day.

## Decision: Orchestration framework
- **Decision**: LangChain v1 `langchain.agents.create_agent` (built on LangGraph) with custom middleware.
- **Rationale**: Standard harness with built-in checkpointing and interrupts; guardrails become small, independently testable middleware; `HumanInTheLoopMiddleware` makes the planned approval feature a one-line addition. Keeps the existing `BaseChatProvider` abstraction (providers already return LangChain chat models).
- **Notes**: `langgraph.prebuilt.create_react_agent` is deprecated in LangGraph v1. Per-run dependencies are injected through `context_schema` / `context=`, not `config["configurable"]`. Tool error handling is middleware (`wrap_tool_call`). Pre-bound models (`llm.bind_tools(...)`) are not accepted; pass the bare model.
- **Alternatives**: Hand-rolled loop on `bind_tools` (most transparent, but approval and persistence must be built by hand); custom `StateGraph` (reimplements what `create_agent` provides); `create_deep_agent` (too heavy for 5 tools); native provider SDKs (three adapters to maintain).

## Decision: Source of truth for conversation state
- **Decision**: The `messages` table is the source of truth. A LangGraph checkpointer (`AsyncPostgresSaver`) keeps one short-lived thread per run (`thread_id = run_id`), used only for resuming paused runs; checkpoints older than 7 days are pruned.
- **Rationale**: One history shared by Web, Slack and the extension; no second store growing forever or drifting from the UI.
- **Cost**: `langgraph-checkpoint-postgres` needs psycopg 3 and its own connection pool alongside SQLAlchemy/asyncpg.
- **Alternatives**: Checkpointer as source of truth (two stores drift); in-memory saver only (paused runs lost on redeploy).

## Decision: Tool set and fate of the pipeline
- **Decision**: Remove `extract_task_info`, the always-on RAG and unconditional task creation. Ship five non-destructive tools: `search_documents`, `create_task`, `list_tasks`, `update_task`, `generate_image`.
- **Rationale**: Clear before/after story; no destructive tools means no approval flow is needed in v1.
- **Alternatives**: Add `delete_task`/`send_slack_message` (forces HITL into v1); add external-data tools such as crypto prices or web search (more surface area and evals).

## Decision: Stream protocol
- **Decision**: Extend the existing NDJSON `ContentDelta` stream; add `id`, `status` and `summary` to tool blocks plus a final `done` block. See `contracts/chat-stream.md`.
- **Rationale**: Web `applyDelta` and Slack `deltas_to_text` already handle `tool_call`, `tool_result` and `citation`; the change is additive.
- **Alternatives**: Vercel AI SDK data-stream protocol (rewrites three clients); final-answer only (hides the agent).

## Decision: Guardrails
- **Decision**: 8-step cap, 20 s per-tool timeout, tool errors returned to the model as error `ToolMessage`s, two provider retries with backoff, each step saved as it completes, runs finish even if the client disconnects.
- **Rationale**: Lets the model recover from bad ids or empty searches; keeps history consistent.
- **Implementation note**: `StreamingResponse` cancels its generator when the client disconnects. The run must execute in a background `asyncio.Task` that writes to an `asyncio.Queue`; the HTTP generator only drains the queue.
- **Deferred**: Per-run token/cost budget (belongs with observability).

## Decision: Context assembly
- **Decision**: A dynamic system prompt (role, tool policy, current time in the user's timezone, date rules) plus the last 20 messages across all platforms. Past tool steps are replayed as `AIMessage(tool_calls)` + `ToolMessage` pairs, with outputs truncated to about 500 characters; image and thinking blocks are dropped from replay.
- **Rationale**: Enables follow-ups; Anthropic and Gemini reject unpaired tool calls, so pairing is enforced at replay time.
- **Alternatives**: Token budget plus summary memory (extra LLM call; overlaps the memory work item); current message only (breaks follow-ups).

## Decision: Timezones
- **Decision**: Add `UserSettings.timezone` (IANA name, defaulting to the browser's zone on first settings load). Store `Task.due_date` as timezone-aware UTC. Tools accept and return ISO-8601 with an offset.
- **Rationale**: The backend currently has no timezone handling; with the model choosing due dates, every reminder would otherwise be interpreted as UTC.
- **Side effect**: Cron jobs (9 am digest) should run in the user's timezone; tracked as a follow-up.

## Decision: Auth
- **Decision**: Add a `get_current_user` dependency (JWT bearer, or an `X-Service-Token` header mapped to `ALLOWED_USER_EMAIL`) on `/chat/*`. Tools read `user_id` from `runtime.context`.
- **Rationale**: No router verifies tokens today, and the chat endpoints load the first user. An agent that writes data must not be callable anonymously once deployed.
- **Alternatives**: A separate auth PR across all routers first (delays the feature; kept as a follow-up); defer entirely (rejected).

## Decision: Testing and mock mode
- **Decision**: A `ScriptedChatModel` (a LangChain fake chat model with a `bind_tools` override) replays scripted `AIMessage`s. Unit tests run the real agent graph, real tools and the test database with it. With no API key, the app uses it with a demo script.
- **Rationale**: Deterministic, no network, exercises the real loop. Real-LLM quality checks belong to the eval suite.
- **Alternatives**: Recorded HTTP cassettes (go stale with SDK upgrades); dropping mock mode.

## Decision: Migrations
- **Decision**: Introduce an Alembic baseline before any schema change.
- **Rationale**: `alembic` is in `requirements.txt` but no migrations exist; tables are created with `Base.metadata.create_all` (`backend/src/main.py:28`), which never alters existing tables, so new columns would not reach existing databases.

## Decision: Scope at the edges
- **Decision**: Delete `POST /chat/`; `/chat/stream` is the single entry point. The extension's direct-OpenAI mode stays plain chat, labeled "no tools". All three providers are supported, with one smoke eval each.
