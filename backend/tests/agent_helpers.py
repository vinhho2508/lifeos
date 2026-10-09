import uuid

from langchain_core.messages import AIMessage
from sqlalchemy import select

from src.agent import runner
from src.agent.scripted_model import ScriptedChatModel
from src.core.database import async_session_factory
from src.models.all_models import Message, PlatformEnum, SenderEnum, Task


def use_script(monkeypatch, *steps, fail_on_call=None) -> ScriptedChatModel:
    """Make the next agent runs use a scripted model instead of a real provider."""
    model = ScriptedChatModel(script=list(steps), fail_on_call=fail_on_call or {})
    monkeypatch.setattr(runner, "build_model", lambda _settings: model)
    return model


def call(name: str, call_id: str | None = None, **args) -> AIMessage:
    tool_call = {"name": name, "args": args, "id": call_id or f"call_{uuid.uuid4().hex[:8]}"}
    return AIMessage(content="", tool_calls=[tool_call])


async def run_turn(user, text: str, platform=PlatformEnum.WEB) -> list[dict]:
    run = await runner.start_run(user.id, text, platform)
    return [event async for event in run.events()]


def types(events: list[dict]) -> list[str]:
    """Event types with consecutive text deltas collapsed."""
    out: list[str] = []
    for event in events:
        if event["type"] == "text" and out and out[-1] == "text":
            continue
        out.append(event["type"])
    return out


def text_of(events: list[dict]) -> str:
    return "".join(e["delta"] for e in events if e["type"] == "text")


async def tasks_of(user) -> list[Task]:
    async with async_session_factory() as db:
        result = await db.execute(select(Task).where(Task.user_id == user.id))
        return list(result.scalars().all())


async def assistant_messages(user) -> list[Message]:
    async with async_session_factory() as db:
        result = await db.execute(
            select(Message)
            .where(Message.user_id == user.id, Message.sender == SenderEnum.ASSISTANT)
            .order_by(Message.timestamp)
        )
        return list(result.scalars().all())
