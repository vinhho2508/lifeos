"""One-shot task extraction for the Slack 📌 reaction (/tasks/from-message).

Chat no longer uses this: the agent decides when to create tasks (src/agent).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from src.core.logging import logger
from src.providers.factory import get_chat_provider
from src.services.task_service import parse_due_date


class ExtractedTask(BaseModel):
    title: str = Field(description="Short imperative task title")
    description: str | None = Field(default=None, description="Extra details, if any")
    due_date: str | None = Field(
        default=None,
        description="ISO-8601 local date/time if the text states one, else null",
    )


async def extract_task_info(
    text: str,
    provider_name: str = "openai",
    model: str = "gpt-5.4-nano",
    timezone: str = "UTC",
) -> dict:
    """Extract title, description and due date (aware UTC datetime or None) from text."""
    provider = get_chat_provider(provider_name, model)
    if not provider.api_key:
        return {
            "title": text.replace("Remind me to ", "")[:255],
            "description": None,
            "due_date": None,
        }

    llm = provider.get_langchain_llm(streaming=False).with_structured_output(ExtractedTask)
    now = datetime.now(ZoneInfo(timezone)).isoformat(timespec="minutes")
    try:
        result: ExtractedTask = await llm.ainvoke(
            f"Extract a task from this message. Current local time is {now} ({timezone}).\n\n"
            f"Message: {text}"
        )
        due = parse_due_date(result.due_date, timezone)
    except Exception as exc:
        logger.warning(f"Task extraction failed ({type(exc).__name__}); using raw text")
        return {"title": text[:255], "description": None, "due_date": None}
    return {"title": result.title[:255], "description": result.description, "due_date": due}
