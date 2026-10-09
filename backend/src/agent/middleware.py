"""Agent policies, each as one middleware.

- time_aware_prompt: system prompt with the current time in the user's timezone.
- ToolGuard: per-tool timeout; tool failures go back to the model as error results.
- ModelCallLimitMiddleware: caps the loop at MAX_STEPS model calls per run.
- ModelRetryMiddleware: retries transient provider errors (429/5xx/timeouts).
"""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    ModelRequest,
    ModelRetryMiddleware,
    dynamic_prompt,
)
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphBubbleUp
from pydantic import ValidationError

from src.agent.context import AgentContext
from src.agent.tools import DEFAULT_TOOL_TIMEOUT, TOOL_TIMEOUTS, ToolError
from src.core.logging import logger

MAX_STEPS = 8
MODEL_RETRIES = 2
RETRY_INITIAL_DELAY = 1.0

SYSTEM_PROMPT = """You are LifeOS, the user's personal assistant. You manage their tasks \
and answer questions from their uploaded documents.

Current time: {now} ({timezone}). The user is chatting from {platform}.

How to work:
- Use tools for anything about tasks or documents; never invent tasks, ids or document content.
- Only create a task when the user asks to add a task, to-do or reminder. Small talk and \
questions never create tasks.
- Resolve relative dates ("Friday 9am", "tomorrow") in the user's timezone and pass them to \
tools as ISO-8601 local time, e.g. 2026-10-10T09:00. If the time is too vague to schedule \
("later", "sometime"), ask instead of guessing.
- To change a task, use an id returned by list_tasks or create_task, including ones from \
earlier in this conversation.
- When you answer from documents, mention which source each fact came from.
- If a tool returns an error, fix the call or explain the problem; do not repeat the same \
failing call.
- Keep replies short and conversational. Markdown is fine."""


@dynamic_prompt
def time_aware_prompt(request: ModelRequest) -> str:
    ctx: AgentContext = request.runtime.context
    now = datetime.now(ZoneInfo(ctx.timezone))
    return SYSTEM_PROMPT.format(
        now=now.strftime("%A %Y-%m-%dT%H:%M%z"),
        timezone=ctx.timezone,
        platform=ctx.platform.value.lower().replace("_", " "),
    )


def _error_message(exc: Exception) -> str:
    if isinstance(exc, ToolError):
        return str(exc)
    if isinstance(exc, TimeoutError):
        return "the tool timed out"
    if isinstance(exc, ValidationError):
        return "invalid arguments: " + "; ".join(e["msg"] for e in exc.errors()[:3])
    # Unexpected failures: name the type, never leak internal details to the model.
    return f"internal error ({type(exc).__name__})"


class ToolGuard(AgentMiddleware):
    """Run each tool with a timeout and turn failures into error ToolMessages."""

    async def awrap_tool_call(self, request, handler):
        call = request.tool_call
        timeout = TOOL_TIMEOUTS.get(call["name"], DEFAULT_TOOL_TIMEOUT)
        try:
            return await asyncio.wait_for(handler(request), timeout=timeout)
        except GraphBubbleUp:
            raise  # interrupts and other LangGraph control flow
        except Exception as exc:
            message = _error_message(exc)
            if not isinstance(exc, ToolError):
                logger.exception(f"Tool {call['name']} failed")
            return ToolMessage(
                content=f"Error: {message}",
                tool_call_id=call["id"],
                name=call["name"],
                status="error",
                artifact={"summary": message[:120], "output": None},
            )


_RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
_RETRYABLE_NAMES = {"APIConnectionError", "APITimeoutError", "ServiceUnavailable"}


def is_retryable_provider_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return (
        status in _RETRYABLE_STATUS
        or isinstance(exc, (TimeoutError, ConnectionError))
        or type(exc).__name__ in _RETRYABLE_NAMES
    )


def build_middleware() -> list[AgentMiddleware]:
    return [
        time_aware_prompt,
        ToolGuard(),
        ModelCallLimitMiddleware(run_limit=MAX_STEPS, exit_behavior="end"),
        ModelRetryMiddleware(
            max_retries=MODEL_RETRIES,
            retry_on=is_retryable_provider_error,
            on_failure="error",
            initial_delay=RETRY_INITIAL_DELAY,
        ),
    ]
