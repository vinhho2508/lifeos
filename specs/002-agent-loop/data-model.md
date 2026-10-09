# Data Model: Tool-Calling Agent Loop

All schema changes ship as Alembic migrations (see research.md, "Migrations").

## Changed: `user_settings`

| Column | Type | Notes |
|---|---|---|
| `timezone` | `String(64)`, not null, default `'UTC'` | IANA zone name (e.g. `Asia/Ho_Chi_Minh`). Validated with `zoneinfo.ZoneInfo`. The frontend sets it from `Intl.DateTimeFormat().resolvedOptions().timeZone` when the stored value is still the default. |

## Changed: `tasks`

| Column | Change | Notes |
|---|---|---|
| `due_date` | `DateTime` → `DateTime(timezone=True)` | Existing naive values are treated as UTC in the migration. |
| `created_at` | `DateTime` → `DateTime(timezone=True)` | Same treatment. |

Code that writes these columns uses `datetime.now(UTC)` instead of `datetime.utcnow()`.

## Changed: `messages.content` (JSON) block types

No column change; the allowed block shapes grow. The stored blocks are the source both for UI rendering and for replaying history to the model.

```jsonc
{ "type": "text", "text": "..." }
{ "type": "thinking", "thinking": "..." }            // not replayed to the model
{ "type": "image", "url": "...", "alt": "..." }      // not replayed to the model
{ "type": "citation", "document_id": "uuid", "chunk_text": "...", "source_name": "lease.pdf" }
{ "type": "tool_call", "id": "call_abc", "name": "list_tasks", "input": { "overdue_only": true } }
{ "type": "tool_result", "id": "call_abc", "name": "list_tasks", "status": "ok" | "error",
  "summary": "3 overdue tasks", "output": <json, truncated to 4 KB when stored> }
```

### Replay mapping (stored blocks → LangChain messages)

| Stored | Replayed as |
|---|---|
| USER message text | `HumanMessage` |
| ASSISTANT `tool_call` blocks (consecutive) | one `AIMessage(content=<preceding text>, tool_calls=[...])` |
| ASSISTANT `tool_result` | `ToolMessage(tool_call_id=id, content=output truncated to ~500 chars)` |
| ASSISTANT trailing text | `AIMessage(content=text)` |
| `tool_call` with no matching `tool_result` | dropped, with a warning logged |
| `thinking`, `image`, `citation` | dropped |

Tool-call ids are kept as the provider issued them. When replaying under a different provider, ids are passed through unchanged (all three accept opaque string ids).

## New: `AgentContext` (runtime only, not persisted)

```python
@dataclass
class AgentContext:
    user_id: uuid.UUID
    timezone: str        # IANA name
    platform: PlatformEnum
    run_id: uuid.UUID
```

## New: LangGraph checkpoint tables

Created by `AsyncPostgresSaver.setup()` (owned by `langgraph-checkpoint-postgres`, not by Alembic). One thread per run (`thread_id = run_id`). A daily cron job deletes threads older than 7 days.
