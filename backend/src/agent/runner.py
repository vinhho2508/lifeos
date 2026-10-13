"""Run the agent for one user turn and stream it as NDJSON events.

The run executes in a background task that writes events to a queue; the HTTP
response only drains the queue. A client disconnect therefore stops the stream but
not the run, which finishes and saves its results (see contracts/chat-stream.md).
"""

import asyncio
import json
import uuid
from typing import Any, AsyncIterator

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from src.agent.checkpointer import get_checkpointer
from src.agent.context import AgentContext
from src.agent.demo import demo_model
from src.agent.history import load_history
from src.agent.middleware import MAX_STEPS, build_middleware
from src.agent.tools import TOOLS
from src.core.database import async_session_factory
from src.core.logging import logger
from src.models.all_models import Message, PlatformEnum, SenderEnum, UserSettings
from src.providers.factory import get_chat_provider
from src.services.conversation_service import resolve_conversation, touch
from src.services.settings_service import get_user_settings

STORED_OUTPUT_MAX_CHARS = 4096

# Strong references so background runs are not garbage-collected mid-flight.
_background_runs: set[asyncio.Task] = set()


def build_model(user_settings: UserSettings) -> BaseChatModel:
    """The user's configured chat model, or the scripted demo model without an API key."""
    provider = get_chat_provider(user_settings.chat_provider, user_settings.chat_model)
    if not provider.api_key:
        logger.info(f"No API key for {provider.provider_name}; using the demo model")
        return demo_model()
    return provider.get_langchain_llm(streaming=True)


def build_agent(model: BaseChatModel):
    return create_agent(
        model,
        TOOLS,
        context_schema=AgentContext,
        middleware=build_middleware(),
        checkpointer=get_checkpointer(),
    )


# ---------------------------------------------------------------------------
# Stream mapping
# ---------------------------------------------------------------------------


def _content_deltas(content: Any) -> list[dict]:
    """Text/thinking deltas from a streamed chunk (string or provider content blocks)."""
    if isinstance(content, str):
        return [{"type": "text", "delta": content}] if content else []
    events = []
    for block in content or []:
        if isinstance(block, str):
            events.append({"type": "text", "delta": block})
        elif isinstance(block, dict):
            kind = block.get("type")
            if kind in ("text", "output_text") and block.get("text"):
                events.append({"type": "text", "delta": block["text"]})
            elif kind in ("thinking", "reasoning"):
                text = block.get("thinking") or block.get("reasoning") or ""
                if text:
                    events.append({"type": "thinking", "delta": text})
    return events


def _stored_output(output: Any) -> Any:
    text = json.dumps(output, default=str)
    return output if len(text) <= STORED_OUTPUT_MAX_CHARS else text[:STORED_OUTPUT_MAX_CHARS] + "…"


class TurnRecorder:
    """Accumulates stream events into stored content blocks for one assistant message."""

    def __init__(self, message_id: uuid.UUID):
        self.message_id = message_id
        self.blocks: list[dict] = []

    def apply(self, event: dict) -> None:
        kind = event["type"]
        last = self.blocks[-1] if self.blocks else None
        if kind == "text":
            if last and last["type"] == "text":
                last["text"] += event["delta"]
            else:
                self.blocks.append({"type": "text", "text": event["delta"]})
        elif kind == "thinking":
            if last and last["type"] == "thinking":
                last["thinking"] += event["delta"]
            else:
                self.blocks.append({"type": "thinking", "thinking": event["delta"]})
        elif kind == "tool_call":
            self.blocks.append(
                {
                    "type": "tool_call",
                    "id": event["id"],
                    "name": event["name"],
                    "input": event["input"],
                }
            )
        elif kind == "tool_result":
            self.blocks.append(
                {
                    "type": "tool_result",
                    "id": event["id"],
                    "name": event["name"],
                    "status": event["status"],
                    "summary": event["summary"],
                    "output": _stored_output(event["output"]),
                }
            )
        elif kind == "citation":
            self.blocks.append({k: v for k, v in event.items()})
        elif kind == "image":
            self.blocks.append({"type": "image", "url": event["url"], "alt": event.get("alt", "")})

    @property
    def plain_text(self) -> str:
        return "".join(b["text"] for b in self.blocks if b["type"] == "text")

    async def save(self) -> None:
        async with async_session_factory() as db:
            message = await db.get(Message, self.message_id)
            if message is None:
                return
            # Assign new objects: SQLAlchemy does not track in-place JSON mutation.
            message.content = [dict(b) for b in self.blocks]
            message.text = self.plain_text
            await db.commit()


def _tool_result_events(message: ToolMessage) -> list[dict]:
    artifact = message.artifact if isinstance(message.artifact, dict) else {}
    status = "error" if message.status == "error" else "ok"
    events = [
        {
            "type": "tool_result",
            "id": message.tool_call_id,
            "name": message.name,
            "status": status,
            "summary": artifact.get("summary") or ("Tool failed" if status == "error" else "Done"),
            "output": artifact.get("output", message.content),
        }
    ]
    for hit in artifact.get("citations", []):
        events.append(
            {
                "type": "citation",
                "document_id": hit["document_id"],
                "chunk_text": hit["chunk_text"],
                "source_name": hit["source_name"],
                "page": hit.get("page"),
                "heading_path": hit.get("heading_path"),
            }
        )
    if image := artifact.get("image"):
        events.append({"type": "image", "url": image["url"], "alt": image.get("alt", "")})
    return events


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


class AgentRun:
    def __init__(self, run_id: uuid.UUID, conversation_id: uuid.UUID | None = None):
        self.run_id = run_id
        self.conversation_id = conversation_id
        self.queue: asyncio.Queue[dict | None] = asyncio.Queue()
        self.task: asyncio.Task | None = None

    async def events(self) -> AsyncIterator[dict]:
        while (event := await self.queue.get()) is not None:
            yield event


async def _execute(
    run: AgentRun,
    model: BaseChatModel,
    context: AgentContext,
    input_messages: list,
    recorder: TurnRecorder,
) -> None:
    agent = build_agent(model)
    steps = 0
    usage = {"input_tokens": 0, "output_tokens": 0}
    stop_reason = "end_turn"

    def emit(event: dict) -> None:
        recorder.apply(event)
        run.queue.put_nowait(event)

    try:
        async for mode, chunk in agent.astream(
            {"messages": input_messages},
            context=context,
            config={
                "configurable": {"thread_id": str(run.run_id)},
                "recursion_limit": 4 * MAX_STEPS + 10,
            },
            stream_mode=["messages", "updates"],
        ):
            if mode == "messages":
                message, meta = chunk
                if meta.get("langgraph_node") == "model" and isinstance(message, AIMessageChunk):
                    for event in _content_deltas(message.content):
                        emit(event)
                continue

            for node, update in chunk.items():
                messages = update.get("messages", []) if isinstance(update, dict) else []
                if node == "model":
                    for m in messages:
                        if not isinstance(m, AIMessage):
                            continue
                        steps += 1
                        for key in usage:
                            usage[key] += (m.usage_metadata or {}).get(key, 0)
                        for call in m.tool_calls:
                            emit(
                                {
                                    "type": "tool_call",
                                    "id": call["id"],
                                    "name": call["name"],
                                    "input": call["args"],
                                }
                            )
                elif node == "tools":
                    for m in messages:
                        if isinstance(m, ToolMessage):
                            for event in _tool_result_events(m):
                                emit(event)
                elif node.startswith("ModelCallLimitMiddleware") and messages:
                    stop_reason = "max_steps"
                    emit(
                        {
                            "type": "text",
                            "delta": f"\n\nI stopped after {MAX_STEPS} steps without finishing. "
                            "Could you narrow the request?",
                        }
                    )
                else:
                    continue
                await recorder.save()
    except Exception as exc:
        logger.exception(f"Agent run {run.run_id} failed")
        stop_reason = "error"
        run.queue.put_nowait(
            {
                "type": "error",
                "message": f"The assistant failed ({type(exc).__name__}). Please try again.",
                "retryable": True,
            }
        )
    finally:
        try:
            await recorder.save()
        except Exception:
            logger.exception(f"Failed to save agent run {run.run_id}")
        run.queue.put_nowait(
            {
                "type": "done",
                "run_id": str(run.run_id),
                "stop_reason": stop_reason,
                "steps": steps,
                "usage": usage,
            }
        )
        run.queue.put_nowait(None)


async def start_run(
    user_id: uuid.UUID,
    text: str,
    platform: PlatformEnum,
    conversation_id: uuid.UUID | None = None,
) -> AgentRun:
    """Save the user's message, then run the agent in the background.

    Raises ConversationNotFound if conversation_id is not one of the user's. Without a
    conversation_id the user's latest conversation is used (created if none exists).
    """
    async with async_session_factory() as db:
        conversation = await resolve_conversation(db, user_id, conversation_id)
        run = AgentRun(uuid.uuid4(), conversation.id)
        user_settings = await get_user_settings(db, user_id)
        history = await load_history(db, conversation.id)
        touch(conversation, text)
        user_message = Message(
            user_id=user_id,
            conversation_id=conversation.id,
            sender=SenderEnum.USER,
            platform=platform,
            text=text,
            content=[{"type": "text", "text": text}],
        )
        db.add(user_message)
        await db.flush()
        assistant_message = Message(
            user_id=user_id,
            conversation_id=conversation.id,
            sender=SenderEnum.ASSISTANT,
            platform=platform,
            text="",
            content=[],
        )
        db.add(assistant_message)
        await db.commit()
        context = AgentContext(
            user_id=user_id, timezone=user_settings.timezone, platform=platform, run_id=run.run_id
        )
        model = build_model(user_settings)

    run.task = asyncio.create_task(
        _execute(
            run,
            model,
            context,
            history + [HumanMessage(content=text)],
            TurnRecorder(assistant_message.id),
        )
    )
    _background_runs.add(run.task)
    run.task.add_done_callback(_background_runs.discard)
    return run
