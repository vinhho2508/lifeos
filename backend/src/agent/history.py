"""Rebuild model input from the messages table.

Stored assistant content is a list of UI blocks (text, tool_call, tool_result, ...).
Replay turns them back into LangChain messages, keeping every tool call paired with
its result: Anthropic and Gemini reject a tool call without a matching result.
"""

import json
import uuid

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.models.all_models import Message, SenderEnum

HISTORY_LIMIT = 20
TOOL_OUTPUT_REPLAY_CHARS = 500


def _truncate(text: str, limit: int = TOOL_OUTPUT_REPLAY_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + "…[truncated]"


def _tool_result_text(block: dict) -> str:
    if block.get("status") == "error":
        return f"Error: {block.get('summary', 'tool failed')}"
    output = block.get("output")
    text = output if isinstance(output, str) else json.dumps(output, default=str)
    return _truncate(text)


def assistant_blocks_to_messages(blocks: list[dict]) -> list[BaseMessage]:
    """Convert one stored assistant turn into AIMessage/ToolMessage pairs."""
    out: list[BaseMessage] = []
    text = ""
    calls: list[dict] = []
    results: dict[str, dict] = {}

    def flush() -> None:
        nonlocal text, calls, results
        paired = [c for c in calls if c.get("id") in results]
        for c in calls:
            if c.get("id") not in results:
                logger.warning(f"Dropping unpaired tool call {c.get('id')} from history")
        if text or paired:
            out.append(
                AIMessage(
                    content=text,
                    tool_calls=[
                        {"name": c["name"], "args": c.get("input") or {}, "id": c["id"]}
                        for c in paired
                    ],
                )
            )
        for c in paired:
            result = results[c["id"]]
            out.append(
                ToolMessage(
                    content=_tool_result_text(result),
                    tool_call_id=c["id"],
                    name=c["name"],
                    status="error" if result.get("status") == "error" else "success",
                )
            )
        text, calls, results = "", [], {}

    for block in blocks or []:
        kind = block.get("type")
        if kind == "text":
            if calls:  # text after a tool step starts the next model step
                flush()
            text += block.get("text", "")
        elif kind == "tool_call" and block.get("id"):
            if results:  # a call after results starts the next model step
                flush()
            calls.append(block)
        elif kind == "tool_result" and block.get("id"):
            results[block["id"]] = block
        # thinking, image and citation blocks are UI-only and not replayed
    flush()
    return out


def messages_to_langchain(rows: list[Message]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for row in rows:
        if row.sender == SenderEnum.USER:
            if row.text:
                out.append(HumanMessage(content=row.text))
        else:
            out.extend(assistant_blocks_to_messages(row.content or []))
    # Providers require the conversation to start with a user turn.
    while out and not isinstance(out[0], HumanMessage):
        out.pop(0)
    return out


async def load_history(
    db: AsyncSession, user_id: uuid.UUID, exclude_ids: set[uuid.UUID] | None = None
) -> list[BaseMessage]:
    """Last HISTORY_LIMIT messages across all platforms, oldest first."""
    query = select(Message).where(Message.user_id == user_id)
    if exclude_ids:
        query = query.where(Message.id.not_in(exclude_ids))
    query = query.order_by(Message.timestamp.desc()).limit(HISTORY_LIMIT)
    rows = list((await db.execute(query)).scalars().all())
    rows.reverse()
    return messages_to_langchain(rows)
