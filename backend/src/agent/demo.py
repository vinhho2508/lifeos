"""Scripted demo model used when the selected provider has no API key.

It exercises the real tools and stream so the UI shows tool steps without any
LLM: "remind me to ..." creates a task, "what's overdue" / "my tasks" lists them.
"""

import re
import uuid

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from src.agent.scripted_model import ScriptedChatModel

DEMO_NOTE = "_(Demo mode: no API key is configured for the selected provider.)_"


def _call_id() -> str:
    return f"call_{uuid.uuid4().hex[:8]}"


def _last_user_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def _choose_action(messages: list[BaseMessage]) -> AIMessage:
    text = _last_user_text(messages)
    lowered = text.lower()
    if re.search(r"\b(remind me|add (a )?task|to-?do)\b", lowered):
        title = re.sub(
            r"(?i)^.*?(remind me to|remind me|add (a )?task( to)?|to-?do:?)\s*", "", text
        )
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "create_task",
                    "args": {"title": title[:120] or text[:120]},
                    "id": _call_id(),
                }
            ],
        )
    if re.search(r"\b(overdue|my tasks|list tasks|what.*tasks)\b", lowered):
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "list_tasks",
                    "args": {"overdue_only": "overdue" in lowered},
                    "id": _call_id(),
                }
            ],
        )
    return AIMessage(content=f"{DEMO_NOTE}\n\nTry “remind me to buy milk” or “what's overdue?”.")


def _summarize_result(messages: list[BaseMessage]) -> AIMessage:
    result = next((m for m in reversed(messages) if isinstance(m, ToolMessage)), None)
    artifact = result.artifact if result is not None and isinstance(result.artifact, dict) else {}
    summary = artifact.get("summary") or (result.content if result else "Done")
    return AIMessage(content=f"{DEMO_NOTE}\n\n{summary}.")


def demo_model() -> ScriptedChatModel:
    return ScriptedChatModel(script=[_choose_action, _summarize_result])
