import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.all_models import StatusEnum, Task, User
from src.services.nlp import extract_task_info
from src.services.task_service import create_task, get_tasks

router = APIRouter()

class TaskUpdate(BaseModel):
    title: str = None
    status: StatusEnum = None

class TaskFromMessageRequest(BaseModel):
    message: str

@router.get("/")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).limit(1))
    user = res.scalar_one_or_none()
    if not user: raise HTTPException(status_code=401)
    
    return await get_tasks(db, user.id)

@router.put("/{task_id}")
async def update_task(task_id: uuid.UUID, update: TaskUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if update.title: task.title = update.title
    if update.status: task.status = update.status
    
    await db.commit()
    return task

@router.post("/from-message")
async def create_task_from_message(req: TaskFromMessageRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).limit(1))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401)

    info = extract_task_info(req.message)
    task = await create_task(
        db,
        user.id,
        info["title"],
        info.get("description"),
        info.get("due_date"),
    )
    return task
