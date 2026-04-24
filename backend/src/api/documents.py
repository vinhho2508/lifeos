from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from src.core.database import get_db
from src.models.all_models import Document, DocumentChunk, DocStatusEnum, User
from src.services.rag_service import chunk_text, get_embeddings
from sqlalchemy import select

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    # Mock user for now
    res = await db.execute(select(User).limit(1))
    user = res.scalar_one_or_none()
    if not user: raise HTTPException(status_code=401)
    
    content = await file.read()
    text = content.decode("utf-8")
    
    doc = Document(user_id=user.id, filename=file.filename, status=DocStatusEnum.DIGESTING)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    # Process chunks
    chunks = chunk_text(text)
    embeddings = await get_embeddings(chunks)
    
    for i, c in enumerate(chunks):
        chunk = DocumentChunk(document_id=doc.id, content=c, embedding=embeddings[i])
        db.add(chunk)
    
    doc.status = DocStatusEnum.READY
    await db.commit()
    
    return {"document_id": str(doc.id), "status": "READY"}
