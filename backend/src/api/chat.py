from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.nlp import extract_task_info
from src.services.task_service import create_task
from src.models.all_models import Message, SenderEnum, PlatformEnum, DocumentChunk, Document, DocStatusEnum
from src.services.rag_service import get_embeddings
from sqlalchemy import select, func

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    platform: PlatformEnum = PlatformEnum.WEB

@router.post("/")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    # ... previous mock user logic ...
    from src.models.all_models import User
    res = await db.execute(select(User).limit(1))
    user = res.scalar_one_or_none()
    if not user: raise HTTPException(status_code=401)
    
    # Save user message
    user_msg = Message(user_id=user.id, sender=SenderEnum.USER, platform=req.platform, text=req.message)
    db.add(user_msg)
    
    # RAG search
    query_embedding = (await get_embeddings([req.message]))[0]
    # Similarity search using pgvector
    result = await db.execute(
        select(DocumentChunk.content)
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(3)
    )
    context_chunks = result.scalars().all()
    context = "\n".join(context_chunks)
    
    # Process with NLP (passing context)
    info = extract_task_info(f"Context: {context}\nQuestion: {req.message}")
    
    # If the LLM identifies it's a question about docs, we should answer it
    # For now, we mix both: task extraction + RAG answer
    reply = f"Based on your documents: {info['title']}" if context else f"I've added your task: {info['title']}"
    
    if info.get('due_date') and not context:
        reply += f" for {info['due_date']}"
        await create_task(db, user.id, info['title'], info.get('description'), info['due_date'])
    elif not context:
        await create_task(db, user.id, info['title'], info.get('description'))
    
    # Save assistant message
    assistant_msg = Message(user_id=user.id, sender=SenderEnum.ASSISTANT, platform=req.platform, text=reply)
    db.add(assistant_msg)
    await db.commit()
    
    return {"reply": reply}

@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db)):
    from src.models.all_models import User
    res = await db.execute(select(User).limit(1))
    user = res.scalar_one_or_none()
    if not user: raise HTTPException(status_code=401)
    
    result = await db.execute(
        select(Message)
        .where(Message.user_id == user.id)
        .order_by(Message.timestamp.asc())
    )
    return result.scalars().all()
