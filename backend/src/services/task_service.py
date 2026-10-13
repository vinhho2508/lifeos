import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.models.all_models import StatusEnum, Task


def parse_due_date(value: str | datetime | None, tz: str) -> datetime | None:
    """Parse an ISO-8601 date/datetime into aware UTC; naive values are read in `tz`.

    A bare date ("2026-10-10") means 09:00 local time that day.
    """
    if value is None or value == "":
        return None
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if len(text) == 10:  # date only
            parsed = parsed.replace(hour=9)
    else:
        parsed = value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(tz))
    return parsed.astimezone(UTC)


async def create_task(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str,
    description: str | None = None,
    due_date: datetime | None = None,
) -> Task:
    task = Task(user_id=user_id, title=title, description=description, due_date=due_date)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    logger.info(f"Task created: {task.id} for user {user_id}")
    return task


async def get_tasks(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(select(Task).where(Task.user_id == user_id))
    return result.scalars().all()


async def list_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: StatusEnum | None = None,
    overdue_only: bool = False,
    limit: int = 20,
) -> list[Task]:
    query = select(Task).where(Task.user_id == user_id)
    if status is not None:
        query = query.where(Task.status == status)
    if overdue_only:
        query = query.where(Task.due_date < datetime.now(UTC), Task.status != StatusEnum.DONE)
    query = query.order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc()).limit(limit)
    return list((await db.execute(query)).scalars().all())


async def get_task(db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    return result.scalar_one_or_none()


async def update_task(
    db: AsyncSession,
    task: Task,
    *,
    title: str | None = None,
    status: StatusEnum | None = None,
    due_date: datetime | None = None,
) -> Task:
    if title:
        task.title = title
    if status is not None:
        task.status = status
    if due_date is not None:
        task.due_date = due_date
        # A moved due date deserves a fresh reminder.
        task.reminder_sent = False
    await db.commit()
    await db.refresh(task)
    logger.info(f"Task updated: {task.id}")
    return task
