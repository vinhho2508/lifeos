import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.all_models import Task, StatusEnum
from src.core.logging import logger

async def create_task(db: AsyncSession, user_id: uuid.UUID, title: str, description: str = None, due_date = None):
    task = Task(user_id=user_id, title=title, description=description, due_date=due_date)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    logger.info(f"Task created: {task.id} for user {user_id}")
    return task

async def get_tasks(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(select(Task).where(Task.user_id == user_id))
    return result.scalars().all()
