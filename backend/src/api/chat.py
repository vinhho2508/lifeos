import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.runner import start_run
from src.core.auth import get_current_user
from src.core.database import get_db
from src.models.all_models import Message, PlatformEnum, User

router = APIRouter()


class ChatStreamRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    platform: PlatformEnum = PlatformEnum.WEB


@router.post("/stream")
async def chat_stream(req: ChatStreamRequest, user: User = Depends(get_current_user)):
    """Run the agent for one turn; NDJSON events per contracts/chat-stream.md."""
    run = await start_run(user.id, req.message, req.platform)

    async def ndjson():
        async for event in run.events():
            yield json.dumps(event, default=str) + "\n"

    return StreamingResponse(ndjson(), media_type="application/x-ndjson")


@router.get("/history")
async def get_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message).where(Message.user_id == user.id).order_by(Message.timestamp.asc())
    )
    return result.scalars().all()
