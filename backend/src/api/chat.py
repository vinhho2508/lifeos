from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory, get_db
from src.models.all_models import (
    DocumentChunk,
    Message,
    PlatformEnum,
    SenderEnum,
)
from src.services.nlp import extract_task_info, stream_reply
from src.services.rag_service import get_embeddings
from src.services.task_service import create_task

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    platform: PlatformEnum = PlatformEnum.WEB


class ChatStreamRequest(BaseModel):
    message: str
    platform: PlatformEnum = PlatformEnum.WEB


@router.post("/")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    from src.models.all_models import User
    res = await db.execute(select(User).limit(1))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401)

    # Save user message
    user_msg = Message(
        user_id=user.id,
        sender=SenderEnum.USER,
        platform=req.platform,
        text=req.message,
        content=[{"type": "text", "text": req.message}],
    )
    db.add(user_msg)

    # RAG search
    query_embedding = (await get_embeddings([req.message]))[0]
    result = await db.execute(
        select(DocumentChunk.content)
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(3)
    )
    context_chunks = result.scalars().all()
    context = "\n".join(context_chunks)

    # Process with NLP
    info = extract_task_info(f"Context: {context}\nQuestion: {req.message}")

    # Build reply content blocks
    content_blocks: list[dict] = []
    if context:
        reply_text = f"Based on your documents: {info['title']}"
    else:
        reply_text = f"I've added your task: {info['title']}"

    if info.get("due_date") and not context:
        reply_text += f" for {info['due_date']}"
        await create_task(
            db, user.id, info["title"], info.get("description"), info["due_date"]
        )
    elif not context:
        await create_task(db, user.id, info["title"], info.get("description"))

    content_blocks.append({"type": "text", "text": reply_text})

    # Save assistant message with structured content
    assistant_msg = Message(
        user_id=user.id,
        sender=SenderEnum.ASSISTANT,
        platform=req.platform,
        text=reply_text,
        content=content_blocks,
    )
    db.add(assistant_msg)
    await db.commit()

    return {"reply": reply_text, "content": content_blocks}


@router.post("/stream")
async def chat_stream(req: ChatStreamRequest):
    from src.models.all_models import User

    async with async_session_factory() as db:
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401)
        user_id = user.id

    async def generate():
        async with async_session_factory() as db:
            # Save user message
            user_msg = Message(
                user_id=user_id,
                sender=SenderEnum.USER,
                platform=req.platform,
                text=req.message,
                content=[{"type": "text", "text": req.message}],
            )
            db.add(user_msg)

            # RAG search
            query_embedding = (await get_embeddings([req.message]))[0]
            result = await db.execute(
                select(DocumentChunk.content)
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(3)
            )
            context_chunks = result.scalars().all()
            context = "\n".join(context_chunks)

            # Process with NLP
            info = extract_task_info(f"Context: {context}\nQuestion: {req.message}")

            # Create task if applicable
            if info.get("due_date") and not context:
                await create_task(
                    db, user_id, info["title"], info.get("description"), info["due_date"]
                )
            elif not context:
                await create_task(db, user_id, info["title"], info.get("description"))

            # Stream reply as NDJSON
            accumulated_blocks: list[dict] = []
            current_text = ""
            current_thinking = ""

            async for delta in stream_reply(req.message, context, info):
                # Yield the delta as an NDJSON line
                yield delta.to_json() + "\n"

                # Accumulate into content blocks for DB storage
                if delta.type == "text":
                    current_text += delta.delta
                elif delta.type == "thinking":
                    current_thinking += delta.delta
                elif delta.type == "image":
                    # Flush any pending text/thinking first
                    if current_text:
                        accumulated_blocks.append(
                            {"type": "text", "text": current_text}
                        )
                        current_text = ""
                    if current_thinking:
                        accumulated_blocks.append(
                            {"type": "thinking", "thinking": current_thinking}
                        )
                        current_thinking = ""
                    accumulated_blocks.append(
                        {
                            "type": "image",
                            "url": delta.extra.get("url", ""),
                            "alt": delta.extra.get("alt", ""),
                        }
                    )

            # Flush remaining accumulated text/thinking
            if current_thinking:
                accumulated_blocks.append(
                    {"type": "thinking", "thinking": current_thinking}
                )
            if current_text:
                accumulated_blocks.append({"type": "text", "text": current_text})

            # Build plain-text fallback
            plain_text = ""
            for block in accumulated_blocks:
                if block["type"] == "text":
                    plain_text += block["text"]
                elif block["type"] == "thinking":
                    plain_text += f"\n[Thinking: {block['thinking']}]\n"
                elif block["type"] == "image":
                    plain_text += f"\n[Image: {block.get('alt', '')}]\n"

            # Save assistant message
            assistant_msg = Message(
                user_id=user_id,
                sender=SenderEnum.ASSISTANT,
                platform=req.platform,
                text=plain_text,
                content=accumulated_blocks,
            )
            db.add(assistant_msg)
            await db.commit()

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db)):
    from src.models.all_models import User
    res = await db.execute(select(User).limit(1))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401)

    result = await db.execute(
        select(Message)
        .where(Message.user_id == user.id)
        .order_by(Message.timestamp.asc())
    )
    return result.scalars().all()
