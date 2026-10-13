"""A deterministic chat model that replays scripted AIMessages.

Used by unit tests (no network) and as the demo model when no provider API key
is configured. Each call to the model pops the next scripted message; text is
streamed word by word and tool calls are emitted as a single tool-call chunk,
which mirrors how real providers stream.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Callable, Iterator, Sequence

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

# A script step is either a fixed message or a function of the conversation so far,
# which lets the demo script react to the user's message.
ScriptStep = AIMessage | Callable[[list[BaseMessage]], AIMessage]


class ScriptExhaustedError(RuntimeError):
    """Raised when the model is called more times than the script allows."""


class ScriptedChatModel(BaseChatModel):
    script: list[Any] = Field(default_factory=list)
    calls: list[list[BaseMessage]] = Field(default_factory=list)
    # When set, the model raises this exception on the matching (0-based) call index.
    fail_on_call: dict[int, Exception] = Field(default_factory=dict)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "ScriptedChatModel":
        # Tools are chosen by the script, so binding is a no-op.
        return self

    def _next(self, messages: list[BaseMessage]) -> AIMessage:
        index = len(self.calls)
        self.calls.append(list(messages))
        if index in self.fail_on_call:
            raise self.fail_on_call[index]
        if index >= len(self.script):
            raise ScriptExhaustedError(f"Script has {len(self.script)} steps; call {index + 1}")
        step = self.script[index]
        return step(messages) if callable(step) else step

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next(messages))])

    def _chunks(self, message: AIMessage) -> Iterator[AIMessageChunk]:
        text = message.content if isinstance(message.content, str) else ""
        words = text.split(" ") if text else []
        for i, word in enumerate(words):
            yield AIMessageChunk(content=word + (" " if i < len(words) - 1 else ""))
        if message.tool_calls:
            yield AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {
                        "name": tc["name"],
                        "args": _json_args(tc["args"]),
                        "id": tc["id"],
                        "index": i,
                        "type": "tool_call_chunk",
                    }
                    for i, tc in enumerate(message.tool_calls)
                ],
            )
        if not words and not message.tool_calls:
            yield AIMessageChunk(content="")

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        for chunk in self._chunks(self._next(messages)):
            if run_manager:
                run_manager.on_llm_new_token(
                    str(chunk.content), chunk=ChatGenerationChunk(message=chunk)
                )
            yield ChatGenerationChunk(message=chunk)

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        for chunk in self._chunks(self._next(messages)):
            if run_manager:
                await run_manager.on_llm_new_token(
                    str(chunk.content), chunk=ChatGenerationChunk(message=chunk)
                )
            yield ChatGenerationChunk(message=chunk)


def _json_args(args: dict) -> str:
    return json.dumps(args)
