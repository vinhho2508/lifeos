"""NLP services: task extraction, streaming replies, and tool use."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from src.core.database import settings
from src.core.logging import logger
from src.services.image_generation import image_service

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


@tool
def generate_image(prompt: str) -> str:
    """Generate an image from a text prompt using DALL-E 3.

    Use this when the user asks for a picture, image, diagram, or visual
    representation of something.
    """
    # Synchronous wrapper; the async caller will handle the real execution
    return f"[IMAGE:{prompt}]"


TOOLS = [generate_image]


# ---------------------------------------------------------------------------
# Task extraction
# ---------------------------------------------------------------------------


def extract_task_info(text: str) -> Dict[str, Any]:
    """Extract task title, description, and due date from free-form text."""
    if not settings.OPENAI_API_KEY:
        return {
            "title": text.replace("Remind me to ", ""),
            "description": None,
            "due_date": datetime.utcnow() + timedelta(hours=1),
        }

    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY, model="gpt-5.4-2026-03-05"
    )
    prompt = ChatPromptTemplate.from_template(
        "Extract task information from this message: {message}. "
        "Return JSON with 'title', 'description', and 'due_date' (ISO format). "
        "Current time is {now}."
    )

    chain = prompt | llm
    response = chain.invoke(
        {"message": text, "now": datetime.utcnow().isoformat()}
    )

    try:
        data = json.loads(response.content)
        if data.get("due_date"):
            data["due_date"] = datetime.fromisoformat(data["due_date"])
        return data
    except Exception:
        return {"title": text, "description": None, "due_date": None}


# ---------------------------------------------------------------------------
# Structured streaming
# ---------------------------------------------------------------------------


class ContentDelta:
    """A single delta emitted during streaming."""

    def __init__(
        self, delta_type: str, delta: str = "", extra: Optional[dict] = None
    ):
        self.type = delta_type
        self.delta = delta
        self.extra = extra or {}

    def to_json(self) -> str:
        payload = {"type": self.type, "delta": self.delta, **self.extra}
        return json.dumps(payload)


async def stream_reply(
    message: str,
    context: str,
    task_info: Optional[Dict[str, Any]],
) -> AsyncIterator[ContentDelta]:
    """Yield structured reply deltas (text, thinking, image, tool_call, etc.)."""

    if not settings.OPENAI_API_KEY:
        # Mock streaming with structured blocks
        if context:
            reply = (
                f"Based on your documents, here's what I found regarding "
                f"{task_info['title'] if task_info else 'that'}."
            )
        elif task_info:
            reply = f"I've noted your task: {task_info['title']}."
        else:
            reply = f"I received your message: {message}."

        # Emit a fake thinking block first
        yield ContentDelta(
            "thinking", "Analyzing the user request and available context..."
        )
        await asyncio.sleep(0.2)

        words = reply.split()
        for i, word in enumerate(words):
            suffix = " " if i < len(words) - 1 else ""
            yield ContentDelta("text", word + suffix)
            await asyncio.sleep(0.05)
        return

    # Real LLM streaming with tool support
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model="gpt-5.4-2026-03-05",
        streaming=True,
    )

    # Bind tools so the model can choose to call generate_image
    llm_with_tools = llm.bind_tools(TOOLS)

    prompt = ChatPromptTemplate.from_template(
        "You are a helpful personal assistant.\n"
        "User message: {message}\n"
        "Document context: {context}\n"
        "Task info: {task_info}\n"
        "Provide a concise, conversational response. "
        "If the user asks for an image, use the generate_image tool."
    )

    chain = prompt | llm_with_tools
    task_info_str = json.dumps(task_info, default=str) if task_info else "None"

    # We accumulate the full assistant message to detect tool calls
    accumulated_content = ""
    tool_calls: list[dict] = []

    async for chunk in chain.astream(
        {
            "message": message,
            "context": context or "None",
            "task_info": task_info_str,
        }
    ):
        # Handle tool call deltas
        if chunk.tool_call_chunks:
            for tc_chunk in chunk.tool_call_chunks:
                # Accumulate tool call arguments
                existing = next(
                    (
                        t
                        for t in tool_calls
                        if t.get("index") == tc_chunk.get("index")
                    ),
                    None,
                )
                if existing is None:
                    tool_calls.append(
                        {
                            "index": tc_chunk.get("index"),
                            "name": tc_chunk.get("name", ""),
                            "args": tc_chunk.get("args", ""),
                        }
                    )
                else:
                    existing["name"] = (
                        existing["name"] or tc_chunk.get("name", "")
                    )
                    existing["args"] += tc_chunk.get("args", "")
            continue

        # Regular text content
        delta = chunk.content
        if delta:
            accumulated_content += delta
            yield ContentDelta("text", delta)

    # After streaming finishes, process any tool calls
    for tc in tool_calls:
        name = tc.get("name", "")
        args_str = tc.get("args", "")
        try:
            args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args = {}

        if name == "generate_image":
            prompt_text = args.get("prompt", "")
            # Yield thinking block
            yield ContentDelta("thinking", f"Generating image for: {prompt_text}")
            # Execute image generation
            image_url = await image_service.generate_image(prompt_text)
            if image_url:
                yield ContentDelta(
                    "image", "", extra={"url": image_url, "alt": prompt_text}
                )
            else:
                yield ContentDelta(
                    "text", "\n\n(Sorry, I couldn't generate the image.)"
                )
        else:
            logger.warning(f"Unknown tool call: {name}")
