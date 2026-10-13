"""Digest documents in the background. documents.status is the queue:

UPLOADED -> DIGESTING -> READY | ERROR

Upload and re-index set UPLOADED and call schedule_digest(). sweep_pending() (at startup
and every few minutes) re-schedules UPLOADED docs and DIGESTING docs that went stale
because the process died mid-digest.
"""

import asyncio
import uuid
from datetime import timedelta

from sqlalchemy import delete, or_, select

from src.core.database import async_session_factory, settings
from src.core.logging import logger
from src.models.all_models import (
    DocSourceEnum,
    DocStatusEnum,
    Document,
    DocumentChunk,
    utcnow,
)
from src.services.rag import embeddings, parsers
from src.services.rag.chunking import chunk_sections
from src.services.rag.fetch import FetchError, fetch_url
from src.services.rag.storage import get_file_store

STALE_AFTER = timedelta(minutes=10)

_semaphore: asyncio.Semaphore | None = None
_in_flight: set[uuid.UUID] = set()
_tasks: set[asyncio.Task] = set()


class DigestError(Exception):
    """A digest failure whose message is safe to show the user."""


_USER_SAFE = (
    DigestError,
    parsers.ParseError,
    parsers.UnsupportedFileType,
    FetchError,
    embeddings.EmbeddingsNotConfigured,
)


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.RAG_DIGEST_CONCURRENCY)
    return _semaphore


def schedule_digest(document_id: uuid.UUID) -> bool:
    """Digest a document in the background; False if it is already being digested."""
    if document_id in _in_flight:
        return False
    _in_flight.add(document_id)

    async def run():
        try:
            async with _get_semaphore():
                await digest_document(document_id)
        finally:
            _in_flight.discard(document_id)

    task = asyncio.create_task(run(), name=f"digest-{document_id}")
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return True


async def sweep_pending() -> int:
    """Schedule every document that is waiting or stuck; returns how many were scheduled."""
    stale = utcnow() - STALE_AFTER
    async with async_session_factory() as db:
        ids = (
            await db.scalars(
                select(Document.id).where(
                    Document.storage_key.is_not(None),
                    or_(
                        Document.status == DocStatusEnum.UPLOADED,
                        (Document.status == DocStatusEnum.DIGESTING)
                        & (Document.status_changed_at < stale),
                    ),
                )
            )
        ).all()
    scheduled = sum(schedule_digest(doc_id) for doc_id in ids)
    if scheduled:
        logger.info(f"RAG sweep scheduled {scheduled} document(s) for digest.")
    return scheduled


async def _set_status(document_id: uuid.UUID, status: DocStatusEnum, error: str | None = None):
    async with async_session_factory() as db:
        doc = await db.get(Document, document_id)
        if doc is None:
            return None
        doc.status = status
        doc.status_changed_at = utcnow()
        doc.error_message = error
        await db.commit()
        return doc


async def _load_original(doc: Document) -> tuple[bytes, str]:
    store = get_file_store()
    if doc.source_type == DocSourceEnum.URL:
        fetched = await fetch_url(doc.source_url)
        mime = _url_mime(fetched.content_type, fetched.data)
        await store.put(doc.storage_key, fetched.data, mime)
        return fetched.data, mime
    return await store.get(doc.storage_key), doc.mime_type or parsers.MIME_TEXT


def _url_mime(content_type: str, data: bytes) -> str:
    if content_type == parsers.MIME_PDF or data.startswith(b"%PDF-"):
        return parsers.MIME_PDF
    if content_type in ("text/plain", "text/markdown"):
        return content_type
    if content_type in ("", "text/html", "application/xhtml+xml"):
        return parsers.MIME_HTML
    raise DigestError(f"Unsupported content type: {content_type}.")


async def digest_document(document_id: uuid.UUID) -> None:
    doc = await _set_status(document_id, DocStatusEnum.DIGESTING)
    if doc is None:
        return
    if doc.storage_key is None:
        await _set_status(document_id, DocStatusEnum.ERROR, "The original file is not stored.")
        return
    try:
        data, mime = await _load_original(doc)
        sections = await asyncio.to_thread(parsers.parse, data, mime)
        title = doc.filename
        if doc.source_type == DocSourceEnum.URL and mime == parsers.MIME_HTML:
            title = await asyncio.to_thread(parsers.html_title, data.decode("utf-8", "replace"))
            title = (title or doc.filename)[:255]
        drafts = await asyncio.to_thread(chunk_sections, sections, title)
        if len(drafts) > settings.RAG_MAX_CHUNKS:
            raise DigestError(
                f"The document is too large ({len(drafts)} chunks; the limit is "
                f"{settings.RAG_MAX_CHUNKS})."
            )
        vectors = await embeddings.embed([d.embed_text for d in drafts])
    except Exception as e:
        if isinstance(e, _USER_SAFE):
            message = str(e)
            logger.warning(f"Digest of document {document_id} failed: {message}")
        else:
            message = "Unexpected error while digesting the document."
            logger.exception(f"Digest of document {document_id} failed")
        await _set_status(document_id, DocStatusEnum.ERROR, message)
        return

    async with async_session_factory() as db:
        doc = await db.get(Document, document_id)
        if doc is None:  # deleted while digesting
            return
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        db.add_all(
            DocumentChunk(
                document_id=document_id,
                ordinal=d.ordinal,
                content=d.content,
                page=d.page,
                heading_path=d.heading_path,
                token_count=d.token_count,
                embedding=v,
            )
            for d, v in zip(drafts, vectors, strict=True)
        )
        doc.filename = title
        doc.mime_type = mime
        doc.status = DocStatusEnum.READY
        doc.status_changed_at = utcnow()
        doc.error_message = None
        doc.chunk_count = len(drafts)
        doc.embedding_model = embeddings.model_name()
        await db.commit()
    logger.info(f"Digested document {document_id}: {len(drafts)} chunk(s).")
