"""Render the backend's NDJSON chat stream as Slack message text."""

import json

TOOL_LABELS = {
    "search_documents": "Searched documents",
    "create_task": "Created task",
    "list_tasks": "Listed tasks",
    "update_task": "Updated task",
    "generate_image": "Generated image",
}


def deltas_to_text(raw: str) -> str:
    """Convert the stream received so far into Slack text.

    `raw` is everything read from the response; a trailing partial line is ignored
    until the rest of it arrives. Tool steps show one line with the result summary,
    never the raw tool output.
    """
    parts: list[str] = []
    pending_tools: dict[str, str] = {}
    for line in raw.split("\n")[:-1]:  # the last element is "" or a partial line
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "text":
            parts.append(event.get("delta", ""))
        elif kind == "image":
            parts.append(
                f"\n🖼️ <{event.get('url', '')}|{event.get('alt') or 'image'}>\n"
            )
        elif kind == "tool_call":
            pending_tools[event.get("id", "")] = event.get("name", "tool")
        elif kind == "tool_result":
            name = pending_tools.pop(event.get("id", ""), event.get("name", "tool"))
            icon = "🔧" if event.get("status") == "ok" else "⚠️"
            label = TOOL_LABELS.get(name, name)
            parts.append(f"{icon} {label}: {event.get('summary', '')}\n")
        elif kind == "error":
            parts.append(f"\n⚠️ {event.get('message', 'Something went wrong.')}\n")
    # Tools still running show as in progress.
    for name in pending_tools.values():
        parts.append(f"⏳ {TOOL_LABELS.get(name, name)}…\n")
    return "".join(parts).strip()
