import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.runner import start_run
from src.core.auth import get_current_user
from src.core.database import get_db
from src.models.all_models import Conversation, Message, PlatformEnum, User
from src.services.conversation_service import (
    ConversationNotFound,
    create_conversation,
    get_conversation,
    latest_conversation,
)

router = APIRouter()

MESSAGE_PAGE_MAX = 200


class ChatStreamRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    platform: PlatformEnum = PlatformEnum.WEB
    # Omitted: continue the user's latest conversation (Slack, Chrome extension).
    conversation_id: uuid.UUID | None = None


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Conversation not found")


async def _owned(db: AsyncSession, user: User, conversation_id: uuid.UUID) -> Conversation:
    try:
        return await get_conversation(db, user.id, conversation_id)
    except ConversationNotFound:
        raise _not_found() from None


@router.post("/stream")
async def chat_stream(req: ChatStreamRequest, user: User = Depends(get_current_user)):
    """Run the agent for one turn; NDJSON events per contracts/chat-stream.md."""
    try:
        run = await start_run(user.id, req.message, req.platform, req.conversation_id)
    except ConversationNotFound:
        raise _not_found() from None

    async def ndjson():
        async for event in run.events():
            yield json.dumps(event, default=str) + "\n"

    return StreamingResponse(
        ndjson(),
        media_type="application/x-ndjson",
        headers={"X-Conversation-Id": str(run.conversation_id)},
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def new_conversation(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    conversation = await create_conversation(db, user.id)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def rename_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _owned(db, user, conversation_id)
    conversation.title = body.title.strip() or conversation.title
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _owned(db, user, conversation_id)
    await db.delete(conversation)
    await db.commit()
    return Response(status_code=204)


async def _messages(
    db: AsyncSession, conversation_id: uuid.UUID, limit: int, before: datetime | None
) -> list[Message]:
    """The newest `limit` messages (older than `before` if given), oldest first."""
    query = select(Message).where(Message.conversation_id == conversation_id)
    if before is not None:
        if before.tzinfo is not None:  # Message.timestamp is stored as naive UTC
            before = before.astimezone(UTC).replace(tzinfo=None)
        query = query.where(Message.timestamp < before)
    rows = (
        (await db.execute(query.order_by(Message.timestamp.desc()).limit(limit))).scalars().all()
    )
    return list(reversed(rows))


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(MESSAGE_PAGE_MAX, ge=1, le=MESSAGE_PAGE_MAX),
    before: datetime | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned(db, user, conversation_id)
    return await _messages(db, conversation_id, limit, before)


@router.get("/history")
async def get_history(
    conversation_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Messages of one conversation (default: the latest). Kept for the Chrome extension."""
    if conversation_id is not None:
        await _owned(db, user, conversation_id)
    else:
        latest = await latest_conversation(db, user.id)
        if latest is None:
            return []
        conversation_id = latest.id
    return await _messages(db, conversation_id, MESSAGE_PAGE_MAX, None)
