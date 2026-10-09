import asyncio

from langchain_core.messages import AIMessage, ToolMessage

from src.agent import middleware
from src.agent.middleware import MAX_STEPS
from src.models.all_models import StatusEnum
from src.services import task_service
from tests.agent_helpers import (
    assistant_messages,
    call,
    run_turn,
    tasks_of,
    text_of,
    types,
    use_script,
)


async def test_small_talk_calls_no_tools_and_creates_no_task(owner, monkeypatch):
    use_script(monkeypatch, AIMessage(content="Hi! How can I help?"))

    events = await run_turn(owner, "hi")

    assert types(events) == ["text", "done"]
    assert text_of(events) == "Hi! How can I help?"
    assert events[-1]["stop_reason"] == "end_turn"
    assert events[-1]["steps"] == 1
    assert await tasks_of(owner) == []


async def test_list_then_update_chain_in_one_turn(owner, monkeypatch):
    async with _session() as db:
        task = await task_service.create_task(db, owner.id, "Pay rent")

    def update_first(messages):
        listed = next(m for m in reversed(messages) if isinstance(m, ToolMessage))
        assert "Pay rent" in listed.content
        return call("update_task", "c2", task_id=str(task.id), status="DONE")

    model = use_script(
        monkeypatch,
        call("list_tasks", "c1"),
        update_first,
        AIMessage(content="Marked 'Pay rent' done."),
    )

    events = await run_turn(owner, "what's on my list? mark the first one done")

    assert types(events) == ["tool_call", "tool_result", "tool_call", "tool_result", "text", "done"]
    calls = [e for e in events if e["type"] == "tool_call"]
    results = [e for e in events if e["type"] == "tool_result"]
    assert [c["id"] for c in calls] == [r["id"] for r in results] == ["c1", "c2"]
    assert results[0]["summary"] == "1 task"
    assert results[1]["status"] == "ok"
    assert events[-1]["steps"] == 3
    assert len(model.calls) == 3
    assert (await tasks_of(owner))[0].status == StatusEnum.DONE


async def test_turn_is_persisted_as_content_blocks(owner, monkeypatch):
    use_script(
        monkeypatch, call("create_task", "c1", title="Buy milk"), AIMessage(content="Added.")
    )

    await run_turn(owner, "remind me to buy milk")

    [message] = await assistant_messages(owner)
    assert [b["type"] for b in message.content] == ["tool_call", "tool_result", "text"]
    assert message.content[0]["input"] == {"title": "Buy milk"}
    assert message.content[1]["id"] == "c1"
    assert message.text == "Added."


async def test_tool_exception_goes_back_to_model(owner, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("db exploded with secret details")

    monkeypatch.setattr(task_service, "list_tasks", boom)
    model = use_script(
        monkeypatch, call("list_tasks", "c1"), AIMessage(content="Sorry, I couldn't load tasks.")
    )

    events = await run_turn(owner, "list my tasks")

    result = next(e for e in events if e["type"] == "tool_result")
    assert result["status"] == "error"
    assert result["summary"] == "internal error (RuntimeError)"
    # The model saw the error (without internal details) and answered.
    tool_message = model.calls[1][-1]
    assert isinstance(tool_message, ToolMessage) and tool_message.status == "error"
    assert "secret" not in tool_message.content
    assert events[-1]["stop_reason"] == "end_turn"


async def test_tool_error_lets_model_recover(owner, monkeypatch):
    async with _session() as db:
        task = await task_service.create_task(db, owner.id, "Renew passport")

    use_script(
        monkeypatch,
        call("update_task", "c1", task_id="not-a-uuid", status="DONE"),
        call("list_tasks", "c2"),
        call("update_task", "c3", task_id=str(task.id), status="DONE"),
        AIMessage(content="Done."),
    )

    events = await run_turn(owner, "mark passport done")

    statuses = [e["status"] for e in events if e["type"] == "tool_result"]
    assert statuses == ["error", "ok", "ok"]
    assert (await tasks_of(owner))[0].status == StatusEnum.DONE


async def test_tool_timeout(owner, monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(5)

    monkeypatch.setattr(task_service, "list_tasks", slow)
    monkeypatch.setattr(middleware, "DEFAULT_TOOL_TIMEOUT", 0.05)
    use_script(monkeypatch, call("list_tasks", "c1"), AIMessage(content="It timed out."))

    events = await run_turn(owner, "list my tasks")

    result = next(e for e in events if e["type"] == "tool_result")
    assert result["status"] == "error"
    assert result["summary"] == "the tool timed out"


async def test_step_cap_stops_runaway_loop(owner, monkeypatch):
    use_script(monkeypatch, *[call("list_tasks") for _ in range(MAX_STEPS + 2)])

    events = await run_turn(owner, "loop forever")

    done = events[-1]
    assert done["stop_reason"] == "max_steps"
    assert done["steps"] == MAX_STEPS
    assert f"stopped after {MAX_STEPS} steps" in text_of(events)
    # Every call the model made got a result; nothing dangles in history.
    calls = [e["id"] for e in events if e["type"] == "tool_call"]
    results = [e["id"] for e in events if e["type"] == "tool_result"]
    assert calls == results


class RateLimited(Exception):
    status_code = 429


class BadRequest(Exception):
    status_code = 400


async def test_transient_provider_error_is_retried(owner, monkeypatch):
    monkeypatch.setattr(middleware, "RETRY_INITIAL_DELAY", 0.0)
    model = use_script(
        monkeypatch,
        AIMessage(content="unused: call 0 fails"),
        AIMessage(content="Recovered."),
        fail_on_call={0: RateLimited("slow down")},
    )

    events = await run_turn(owner, "hello")

    assert text_of(events) == "Recovered."
    assert events[-1]["stop_reason"] == "end_turn"
    assert len(model.calls) == 2


async def test_permanent_provider_error_ends_run_with_error(owner, monkeypatch):
    use_script(monkeypatch, AIMessage(content="never"), fail_on_call={0: BadRequest("nope")})

    events = await run_turn(owner, "hello")

    assert types(events) == ["error", "done"]
    assert events[0]["message"] == "The assistant failed (BadRequest). Please try again."
    assert events[-1]["stop_reason"] == "error"


async def test_run_finishes_after_client_disconnects(owner, monkeypatch):
    from src.agent import runner

    use_script(
        monkeypatch, call("create_task", "c1", title="Water plants"), AIMessage(content="Added.")
    )

    run = await runner.start_run(owner.id, "remind me to water plants", runner.PlatformEnum.WEB)
    stream = run.events()
    await stream.__anext__()  # the client reads one event, then goes away
    await stream.aclose()
    await asyncio.wait_for(run.task, timeout=5)

    [message] = await assistant_messages(owner)
    assert [b["type"] for b in message.content] == ["tool_call", "tool_result", "text"]
    assert [t.title for t in await tasks_of(owner)] == ["Water plants"]


async def test_demo_model_without_api_key(owner):
    # No monkeypatch: OPENAI_API_KEY is empty in tests, so the demo model is used.
    events = await run_turn(owner, "remind me to buy milk")

    assert types(events) == ["tool_call", "tool_result", "text", "done"]
    assert [t.title for t in await tasks_of(owner)] == ["buy milk"]
    assert "Demo mode" in text_of(events)


def _session():
    from src.core.database import async_session_factory

    return async_session_factory()
