import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stream_format import deltas_to_text


def ndjson(*events) -> str:
    return "".join(json.dumps(e) + "\n" for e in events)


def test_tool_steps_show_summary_not_output():
    raw = ndjson(
        {"type": "tool_call", "id": "c1", "name": "list_tasks", "input": {}},
        {
            "type": "tool_result",
            "id": "c1",
            "name": "list_tasks",
            "status": "ok",
            "summary": "3 tasks",
            "output": [{"id": "secret-id", "title": "x"}],
        },
        {"type": "text", "delta": "You have "},
        {"type": "text", "delta": "3 tasks."},
        {"type": "done", "stop_reason": "end_turn"},
    )

    text = deltas_to_text(raw)

    assert text == "🔧 Listed tasks: 3 tasks\nYou have 3 tasks."
    assert "secret-id" not in text


def test_running_tool_and_partial_line():
    raw = ndjson(
        {"type": "tool_call", "id": "c1", "name": "search_documents", "input": {}}
    )
    raw += '{"type": "tool_res'  # partial line still arriving

    assert deltas_to_text(raw) == "⏳ Searched documents…"


def test_error_result_and_error_event():
    raw = ndjson(
        {"type": "tool_call", "id": "c1", "name": "update_task", "input": {}},
        {
            "type": "tool_result",
            "id": "c1",
            "status": "error",
            "summary": "no task with id x",
        },
        {
            "type": "error",
            "message": "The assistant failed (RateLimitError). Please try again.",
        },
    )

    assert deltas_to_text(raw) == (
        "⚠️ Updated task: no task with id x\n\n"
        "⚠️ The assistant failed (RateLimitError). Please try again."
    )
