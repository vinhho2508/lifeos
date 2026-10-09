# Feature Specification: Tool-Calling Agent Loop

**Feature Branch**: `002-agent-loop`
**Created**: 2026-10-09
**Status**: Draft
**Input**: Replace the fixed chat pipeline (always-on RAG → `extract_task_info` → unconditional task creation → single-pass reply) with a real tool-calling agent that decides which actions to take, observes their results, and iterates until it can answer.

## Problem Statement

Today every chat message runs the same pipeline in `backend/src/api/chat.py`:

1. Embed the message and fetch the top-3 document chunks, whether or not the question is about documents.
2. Run `extract_task_info` (a blocking LLM call inside an async handler).
3. **Create a task whenever no document context was found** — "hi" becomes a task.
4. Stream a reply. `generate_image` is the only tool, and its result is never fed back to the model.

The model receives no conversation history, the backend has no notion of the user's timezone, and the chat endpoints do not verify the caller (they load the first user in the database).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The assistant decides what to do (Priority: P1) 🎯 MVP

As the user, I want the assistant to choose which actions to take based on my message, so that small talk doesn't create tasks and questions about my documents actually search them.

**Independent Test**: Send "hi", "remind me to pay rent Friday 9am", and "what does my lease say about pets?" and check the tool calls each one produces.

**Acceptance Scenarios**:

1. **Given** any message with no actionable intent, **When** I send it, **Then** no tool is called and no task is created.
2. **Given** "remind me to pay rent Friday 9am", **When** I send it, **Then** `create_task` is called once with a due date of the coming Friday 09:00 *in my timezone*, and the reply confirms it.
3. **Given** a question covered by an uploaded document, **When** I send it, **Then** `search_documents` is called and the reply includes citations to the matched chunks.
4. **Given** "what's overdue? mark the first one done", **When** I send it, **Then** the agent calls `list_tasks` and then `update_task` with an id taken from the list result, in a single turn.

---

### User Story 2 - I can see what the agent did (Priority: P1)

As the user (and as an interviewer watching a demo), I want each tool step to be visible, so that I can trust and debug the agent's actions.

**Independent Test**: Trigger a multi-tool turn and verify each tool step renders in the web UI and in Slack.

**Acceptance Scenarios**:

1. **Given** a turn that calls tools, **When** it streams in the web UI, **Then** each tool step appears as a collapsible card showing the tool name, its input, a status (running/ok/error), and a one-line summary.
2. **Given** the same turn in Slack, **When** it streams, **Then** each tool step is shown as a single line (e.g. `🔧 Searched documents (3 hits)`) and raw tool output is never posted.
3. **Given** a reloaded chat page, **When** history loads, **Then** past tool steps render the same way they did live.

---

### User Story 3 - Follow-ups work across platforms (Priority: P1)

As the user, I want the assistant to remember the recent conversation, so that follow-ups like "move that one to tomorrow" work — even if I started on the web and continue in Slack.

**Independent Test**: Create a task on the web, then in Slack say "push it to Monday" and verify the same task is updated.

**Acceptance Scenarios**:

1. **Given** a task created in the previous turn, **When** I say "push it to Monday", **Then** `update_task` targets that task's id without calling `list_tasks` again.
2. **Given** a conversation started on the web, **When** I continue in Slack, **Then** the agent sees the web turns (history is shared across platforms).

---

### User Story 4 - The agent fails gracefully (Priority: P2)

As the user, I want tool or provider failures not to break the chat, so that a single bad call doesn't lose my turn.

**Acceptance Scenarios**:

1. **Given** a tool raises an error or times out, **When** the agent runs, **Then** the error is returned to the model, the step shows `status: error`, and the model may retry or explain.
2. **Given** the agent keeps calling tools, **When** it reaches 8 steps, **Then** the run stops with `stop_reason: "max_steps"` and a short explanation.
3. **Given** I close the tab mid-stream, **When** the run continues server-side, **Then** history is consistent (every completed tool step and the final reply are saved) when I reopen the chat.

---

### User Story 5 - Only I can drive the agent (Priority: P1)

As the single authorized user, I want the chat endpoints to require authentication, so that a deployed agent that can write data cannot be driven by anyone else.

**Acceptance Scenarios**:

1. **Given** no or an invalid JWT, **When** calling `/chat/stream` or `/chat/history`, **Then** the response is 401.
2. **Given** the Slack bot's service token, **When** it calls `/chat/stream`, **Then** the request is accepted as the allowed user.
3. **Given** any tool call, **Then** the acting `user_id` comes from the server-side run context and never from model-supplied arguments.

### Edge Cases

- **Ambiguous time** ("remind me later", "next week"): the agent asks a clarifying question or picks a documented default; it never silently uses UTC.
- **Invented ids**: `update_task` with an unknown or another user's `task_id` returns a tool error, not a 500.
- **Parallel tool calls**: two calls in one model response are each paired with their result by `id`.
- **History replay**: a stored tool call without a stored result (e.g. a crash mid-step) must not be replayed as an unpaired call; providers reject that.
- **No API key**: the app still runs using the scripted demo model.
- **Provider switch mid-conversation**: history saved under one provider must replay correctly under another.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The chat backend MUST run a tool-calling loop where the model decides whether to call tools and sees every tool result before continuing.
- **FR-002**: The v1 tool set MUST be exactly: `search_documents`, `create_task`, `list_tasks`, `update_task`, `generate_image`.
- **FR-003**: `extract_task_info`, the unconditional RAG lookup and unconditional task creation MUST be removed.
- **FR-004**: A run MUST stop after at most 8 model steps, and MUST report why it stopped (`end_turn`, `max_steps`, `error`).
- **FR-005**: Each tool call MUST time out after 20 s; tool errors and timeouts MUST be returned to the model as error tool results.
- **FR-006**: Provider 429/5xx errors MUST be retried twice with backoff before surfacing a sanitized error block.
- **FR-007**: Each turn's model input MUST include a system prompt with the current time in the user's timezone, and the last 20 messages across all platforms, with past tool results truncated to about 500 characters.
- **FR-008**: The stream MUST stay backward-compatible NDJSON, and tool blocks MUST carry an `id` so each result is paired with its call (see `contracts/chat-stream.md`).
- **FR-009**: Tool calls, tool results and citations MUST be saved in `messages.content` and rendered on history reload.
- **FR-010**: `/chat/*` MUST require a valid JWT or the Slack service token.
- **FR-011**: Tools MUST get `user_id`, timezone and platform from an injected run context, not from model arguments.
- **FR-012**: The user's timezone MUST be stored in `UserSettings`; due dates MUST be stored as timezone-aware UTC.
- **FR-013**: A run MUST finish and save its results even if the client disconnects.
- **FR-014**: The agent MUST work with all three configured providers (OpenAI, Anthropic, Gemini).
- **FR-015**: With no provider API key, the app MUST fall back to a scripted demo model that exercises at least one tool.
- **FR-016**: `POST /chat/` (non-streaming) MUST be removed; `/chat/stream` becomes the single chat endpoint.

### Key Entities

- **Agent Run**: one user turn, from the incoming message to a final answer or stop; identified by `run_id`, which is also the checkpoint thread id.
- **Tool Step**: a paired `tool_call` and `tool_result` content block sharing an `id`.
- **Agent Context**: server-injected `{user_id, timezone, platform}` available to every tool.

## Success Criteria *(mandatory)*

- **SC-001**: 0 tasks created for a set of 10 non-actionable messages ("hi", "thanks", ...).
- **SC-002**: ≥ 90% correct tool choice on the v1 smoke eval set, per provider.
- **SC-003**: 100% of `create_task` calls with relative dates resolve in the user's timezone in the eval set.
- **SC-004**: Unit tests cover loop order, error recovery, max-steps, history replay pairing, and disconnect consistency, using the scripted model only (no network).
- **SC-005**: Unauthenticated `/chat/*` requests return 401 (test-enforced).

## Out of Scope (v1)

- Destructive or outward-facing tools (`delete_task`, `send_slack_message`) and human-in-the-loop approval — planned next via `HumanInTheLoopMiddleware`.
- Token/cost budgets, tracing and observability (separate work item).
- Long-term memory and conversation summarization.
- Tool support in the Chrome extension's direct-OpenAI mode (it gets labeled "no tools").
- Auth hardening for the `tasks`, `documents` and `settings` routers (follow-up PR).
