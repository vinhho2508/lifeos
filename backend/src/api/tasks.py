import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.core.database import get_db
from src.models.all_models import StatusEnum, User
from src.services import task_service
from src.services.nlp import extract_task_info
from src.services.settings_service import get_user_settings
from src.services.task_service import create_task, get_tasks

router = APIRouter()


class TaskUpdate(BaseModel):
    title: str = None
    status: StatusEnum = None


class TaskFromMessageRequest(BaseModel):
    message: str


@router.get("/")
async def list_tasks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_tasks(db, user.id)


@router.put("/{task_id}")
async def update_task(
    task_id: uuid.UUID,
    update: TaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return await task_service.update_task(db, task, title=update.title, status=update.status)


@router.post("/from-message")
async def create_task_from_message(
    req: TaskFromMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_settings = await get_user_settings(db, user.id)
    info = await extract_task_info(
        req.message,
        provider_name=user_settings.chat_provider,
        model=user_settings.chat_model,
        timezone=user_settings.timezone,
    )
    task = await create_task(
        db,
        user.id,
        info["title"],
        info.get("description"),
        info.get("due_date"),
    )
    return task
