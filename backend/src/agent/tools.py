"""Tools the agent can call.

Every tool returns (content, artifact):
- content: compact text the model reads.
- artifact: structured data for the UI and history ({summary, output, ...}); the
  runner turns it into tool_result / citation / image stream blocks.

Tools raise ToolError for problems the model should see and can recover from.
"""

import json
import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from langchain.tools import ToolRuntime, tool
from sqlalchemy import select

from src.agent.context import AgentContext
from src.core.database import async_session_factory
from src.models.all_models import Document, DocumentChunk, StatusEnum, Task
from src.services import task_service
from src.services.image_generation import image_service
from src.services.rag_service import get_embeddings

Status = Literal["TODO", "WORKING", "DONE"]


class ToolError(Exception):
    """An error whose message is safe to show to the model and the user."""


def _local_iso(value: datetime | None, tz: str) -> str | None:
    return value.astimezone(ZoneInfo(tz)).isoformat(timespec="minutes") if value else None


def _task_dict(task: Task, tz: str) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status.value,
        "due_date": _local_iso(task.due_date, tz),
    }


def _parse_due(value: str | None, tz: str) -> datetime | None:
    try:
        return task_service.parse_due_date(value, tz)
    except ValueError:
        raise ToolError(f"due_date '{value}' is not ISO-8601 (e.g. 2026-10-10T09:00)")


def _parse_task_id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ToolError(f"task_id '{value}' is not a valid id; use an id from list_tasks")


@tool(response_format="content_and_artifact")
async def search_documents(query: str, runtime: ToolRuntime[AgentContext], k: int = 5):
    """Search the user's uploaded documents for passages relevant to the query.

    Use this whenever the user asks about the content of their documents, notes or
    files. Cite the returned sources in your answer.
    """
    k = max(1, min(k, 10))
    embedding = (await get_embeddings([query]))[0]
    distance = DocumentChunk.embedding.cosine_distance(embedding)
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(DocumentChunk.content, Document.id, Document.filename, distance)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(Document.user_id == runtime.context.user_id)
                .order_by(distance)
                .limit(k)
            )
        ).all()

    hits = [
        {
            "document_id": str(doc_id),
            "source_name": filename,
            "chunk_text": content,
            "score": round(1 - float(dist), 3),
        }
        for content, doc_id, filename, dist in rows
    ]
    summary = f"{len(hits)} passage{'s' if len(hits) != 1 else ''} found"
    if not hits:
        return "No matching passages in the user's documents.", {"summary": summary, "output": []}

    content = "\n\n".join(
        f"[{i}] {h['source_name']} (score {h['score']}):\n{h['chunk_text']}"
        for i, h in enumerate(hits, 1)
    )
    return content, {"summary": summary, "output": hits, "citations": hits}


@tool(response_format="content_and_artifact")
async def create_task(
    title: str,
    runtime: ToolRuntime[AgentContext],
    description: str | None = None,
    due_date: str | None = None,
):
    """Create a task on the user's board.

    Only call this when the user asks to add a task, to-do or reminder.
    due_date is ISO-8601 in the user's local time (e.g. 2026-10-10T09:00), or omitted.
    """
    if not title.strip():
        raise ToolError("title must not be empty")
    tz = runtime.context.timezone
    due = _parse_due(due_date, tz)
    async with async_session_factory() as db:
        task = await task_service.create_task(
            db, runtime.context.user_id, title.strip(), description, due
        )
        data = _task_dict(task, tz)
    when = f" due {data['due_date']}" if data["due_date"] else ""
    return json.dumps(data), {"summary": f"Created '{data['title']}'{when}", "output": data}


@tool(response_format="content_and_artifact")
async def list_tasks(
    runtime: ToolRuntime[AgentContext],
    status: Status | None = None,
    overdue_only: bool = False,
    limit: int = 20,
):
    """List the user's tasks, soonest due first.

    Filter by status, or set overdue_only to get tasks past their due date that are
    not done. Use the returned ids for update_task.
    """
    tz = runtime.context.timezone
    async with async_session_factory() as db:
        tasks = await task_service.list_tasks(
            db,
            runtime.context.user_id,
            status=StatusEnum(status) if status else None,
            overdue_only=overdue_only,
            limit=max(1, min(limit, 50)),
        )
        data = [_task_dict(t, tz) for t in tasks]
    label = "overdue task" if overdue_only else "task"
    summary = f"{len(data)} {label}{'s' if len(data) != 1 else ''}"
    return json.dumps(data), {"summary": summary, "output": data}


@tool(response_format="content_and_artifact")
async def update_task(
    task_id: str,
    runtime: ToolRuntime[AgentContext],
    status: Status | None = None,
    due_date: str | None = None,
    title: str | None = None,
):
    """Update one of the user's tasks: change its status, due date or title.

    task_id must come from list_tasks or create_task; never guess it.
    due_date is ISO-8601 in the user's local time.
    """
    if status is None and due_date is None and not title:
        raise ToolError("nothing to update; pass status, due_date or title")
    tz = runtime.context.timezone
    task_uuid = _parse_task_id(task_id)
    due = _parse_due(due_date, tz)
    async with async_session_factory() as db:
        task = await task_service.get_task(db, runtime.context.user_id, task_uuid)
        if task is None:
            raise ToolError(f"no task with id {task_id}; call list_tasks to find it")
        task = await task_service.update_task(
            db,
            task,
            title=title,
            status=StatusEnum(status) if status else None,
            due_date=due,
        )
        data = _task_dict(task, tz)

    changes = []
    if status:
        changes.append(f"status {status}")
    if due:
        changes.append(f"due {data['due_date']}")
    if title:
        changes.append("title")
    summary = f"Updated '{data['title']}': {', '.join(changes)}"
    return json.dumps(data), {"summary": summary, "output": data}


@tool(response_format="content_and_artifact")
async def generate_image(prompt: str):
    """Generate an image from a text prompt.

    Use this when the user asks for a picture, image, diagram, or visual
    representation of something. The image is shown to the user automatically.
    """
    url = await image_service.generate_image(prompt)
    if not url:
        raise ToolError("image generation failed")
    # The URL can be a multi-megabyte data URL, so it never goes to the model or tool output.
    return (
        "The image was generated and is already displayed to the user.",
        {
            "summary": "Generated an image",
            "output": {"alt": prompt},
            "image": {"url": url, "alt": prompt},
        },
    )


TOOLS = [search_documents, create_task, list_tasks, update_task, generate_image]

# Per-tool timeouts in seconds; image generation is much slower than DB tools.
TOOL_TIMEOUTS = {"generate_image": 120.0}
DEFAULT_TOOL_TIMEOUT = 20.0
