"""The old pipeline created a task for every message without document context."""

from langchain_core.messages import AIMessage

from tests.agent_helpers import call, run_turn, tasks_of, use_script


async def test_small_talk_creates_no_task(owner, monkeypatch):
    for text in ("hi", "thanks!", "how are you?"):
        use_script(monkeypatch, AIMessage(content="Hello!"))
        await run_turn(owner, text)

    assert await tasks_of(owner) == []


async def test_reminder_creates_exactly_one_task(owner, monkeypatch):
    use_script(monkeypatch, call("create_task", title="Buy milk"), AIMessage(content="Added."))

    await run_turn(owner, "Remind me to buy milk")

    assert [t.title for t in await tasks_of(owner)] == ["Buy milk"]
