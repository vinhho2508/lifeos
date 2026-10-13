import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.core.database import get_db, settings
from src.core.logging import logger
from src.models.all_models import DocSourceEnum, DocStatusEnum, Document, User, utcnow
from src.services.rag import ingest, parsers
from src.services.rag.fetch import FetchError, validate_url
from src.services.rag.storage import StorageError, get_file_store, storage_key

router = APIRouter()

_READ_CHUNK = 1024 * 1024


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    source_type: DocSourceEnum
    source_url: str | None
    mime_type: str | None
    size_bytes: int | None
    status: DocStatusEnum
    error_message: str | None
    chunk_count: int
    created_at: datetime
    reindexable: bool

    @classmethod
    def of(cls, doc: Document) -> "DocumentOut":
        return cls(
            id=doc.id,
            filename=doc.filename,
            source_type=doc.source_type,
            source_url=doc.source_url,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            status=doc.status,
            error_message=doc.error_message,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
            reindexable=doc.storage_key is not None,
        )


class UrlIn(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


async def _owned(db: AsyncSession, user: User, document_id: uuid.UUID) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


async def _read_limited(file: UploadFile) -> bytes:
    limit = settings.RAG_MAX_UPLOAD_MB * 1024 * 1024
    data = bytearray()
    while part := await file.read(_READ_CHUNK):
        data.extend(part)
        if len(data) > limit:
            raise HTTPException(
                status_code=413, detail=f"File is larger than {settings.RAG_MAX_UPLOAD_MB} MB"
            )
    return bytes(data)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    docs = await db.scalars(
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    )
    return [DocumentOut.of(d) for d in docs]


@router.post("/upload", response_model=DocumentOut, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await _read_limited(file)
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")
    filename = (file.filename or "upload").rsplit("/", 1)[-1][:255]
    try:
        mime = parsers.detect_type(filename, data[:4096])
    except parsers.UnsupportedFileType as e:
        raise HTTPException(
            status_code=415, detail=f"{e}; supported: .txt, .md, .pdf, .html"
        ) from None

    doc_id = uuid.uuid4()
    key = storage_key(user.id, doc_id)
    try:
        await get_file_store().put(key, data, mime)
    except StorageError as e:
        raise HTTPException(status_code=503, detail=str(e)) from None
    doc = Document(
        id=doc_id,
        user_id=user.id,
        filename=filename,
        source_type=DocSourceEnum.FILE,
        mime_type=mime,
        size_bytes=len(data),
        storage_key=key,
        status=DocStatusEnum.UPLOADED,
        status_changed_at=utcnow(),
    )
    db.add(doc)
    await db.commit()
    ingest.schedule_digest(doc.id)
    return DocumentOut.of(doc)


@router.post("/url", response_model=DocumentOut, status_code=202)
async def add_url(
    body: UrlIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    try:
        url = validate_url(body.url)
    except FetchError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=user.id,
        filename=url[:255],
        source_type=DocSourceEnum.URL,
        source_url=url,
        storage_key=storage_key(user.id, doc_id),
        status=DocStatusEnum.UPLOADED,
        status_changed_at=utcnow(),
    )
    db.add(doc)
    await db.commit()
    ingest.schedule_digest(doc.id)
    return DocumentOut.of(doc)


@router.post("/{document_id}/reindex", response_model=DocumentOut, status_code=202)
async def reindex_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _owned(db, user, document_id)
    if doc.storage_key is None:
        raise HTTPException(
            status_code=409, detail="The original was not kept; upload the document again"
        )
    if doc.status in (DocStatusEnum.UPLOADED, DocStatusEnum.DIGESTING):
        raise HTTPException(status_code=409, detail="The document is already being digested")
    doc.status = DocStatusEnum.UPLOADED
    doc.status_changed_at = utcnow()
    doc.error_message = None
    await db.commit()
    ingest.schedule_digest(doc.id)
    return DocumentOut.of(doc)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _owned(db, user, document_id)
    key = doc.storage_key
    await db.delete(doc)
    await db.commit()
    if key:
        try:
            await get_file_store().delete(key)
        except Exception:
            logger.exception(f"Could not delete stored original {key}")
    return Response(status_code=204)
