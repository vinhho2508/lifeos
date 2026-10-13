# Contract: `POST /chat/stream`

## Auth

One of:

- `Authorization: Bearer <JWT>` (web app; Chrome extension in backend mode)
- `X-Service-Token: <SLACK_SERVICE_TOKEN>` (Slack bot; maps to `ALLOWED_USER_EMAIL`)

Missing or invalid → `401`. `GET /chat/history` uses the same auth.

## Request

```json
{ "message": "what's overdue? mark the first one done", "platform": "WEB" }
```

## Response

`200`, `Content-Type: application/x-ndjson`. One JSON object per line. Every line has `type`; any other fields depend on the type. Clients MUST ignore unknown types and unknown fields.

| `type`        | Fields                                                                     | Notes                                                                                         |
| ------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `text`        | `delta`                                                                    | Appended to the current text block.                                                           |
| `thinking`    | `delta`                                                                    | Provider reasoning, when available.                                                           |
| `tool_call`   | `id`, `name`, `input`                                                      | Sent once the call's arguments are complete (not streamed partially).                         |
| `tool_result` | `id`, `name`, `status` (`ok`/`error`), `summary`, `output`                 | `summary` is one human-readable line; `output` may be large. Slack shows `summary` only.      |
| `citation`    | `document_id`, `chunk_text`, `source_name`                                 | Sent after a `search_documents` result, one per chunk the model may cite.                     |
| `image`       | `url`, `alt`                                                               | Sent after `generate_image` succeeds.                                                         |
| `error`       | `message`, `retryable`                                                     | Sanitized; no stack traces or keys.                                                           |
| `done`        | `run_id`, `stop_reason` (`end_turn`/`max_steps`/`error`), `steps`, `usage` | Always the last line. `usage` = `{input_tokens, output_tokens}` when the provider reports it. |

### Example

```
{"type":"tool_call","id":"call_1","name":"list_tasks","input":{"overdue_only":true}}
{"type":"tool_result","id":"call_1","name":"list_tasks","status":"ok","summary":"2 overdue tasks","output":[{"id":"…","title":"Pay rent","due_date":"2026-10-03T09:00:00+07:00"}]}
{"type":"tool_call","id":"call_2","name":"update_task","input":{"task_id":"…","status":"DONE"}}
{"type":"tool_result","id":"call_2","name":"update_task","status":"ok","summary":"Marked 'Pay rent' done","output":{"id":"…","status":"DONE"}}
{"type":"text","delta":"Done — 'Pay rent' is marked complete. "}
{"type":"text","delta":"You still have 'Renew passport' overdue."}
{"type":"done","run_id":"…","stop_reason":"end_turn","steps":3,"usage":{"input_tokens":1834,"output_tokens":96}}
```

## Compatibility

- Additive over the current stream: `text`, `thinking` and `image` are unchanged.
- `delta` is now optional on non-text types; the web `ContentDelta` type must make it optional.
- Clients that predate this change render tool steps without pairing. Slack's `deltas_to_text` must switch from printing `output` to printing `summary`.

## Removed

`POST /chat/` (non-streaming) is deleted.

## Tool schemas (model-facing)

```text
search_documents(query: str, k: int = 5) -> [{document_id, source_name, chunk_text, score}]
create_task(title: str, description: str | None = None, due_date: str | None = None)  # ISO-8601 with offset
    -> {id, title, status, due_date}
list_tasks(status: "TODO"|"WORKING"|"DONE" | None = None, overdue_only: bool = False, limit: int = 20)
    -> [{id, title, status, due_date}]
update_task(task_id: str, status: ... | None = None, due_date: str | None = None, title: str | None = None)
    -> {id, title, status, due_date}
generate_image(prompt: str) -> {url, alt}
```

`user_id` is never a tool parameter. Dates in tool output are rendered in the user's timezone.
