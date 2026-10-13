from datetime import timedelta

from sqlalchemy import func, select

from src.core.database import async_session_factory, settings
from src.models.all_models import DocStatusEnum, Document, DocumentChunk, utcnow
from src.services.rag import embeddings, ingest
from src.services.rag.storage import get_file_store
from tests.rag_helpers import make_pdf

MD = b"# Lease\n\nRent is due on the first.\n\n## Pets\n\nOne cat allowed with a deposit.\n"


async def _upload(client, auth_headers, name="lease.md", data=MD):
    return await client.post(
        "/documents/upload", files={"file": (name, data)}, headers=auth_headers
    )


async def _doc(doc_id) -> Document:
    async with async_session_factory() as db:
        return await db.get(Document, doc_id)


async def _chunks(doc_id) -> list[DocumentChunk]:
    async with async_session_factory() as db:
        rows = await db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_id)
            .order_by(DocumentChunk.ordinal)
        )
        return list(rows)


async def test_upload_requires_auth_even_when_a_user_exists(client, owner):
    response = await client.post("/documents/upload", files={"file": ("a.txt", b"hello")})
    assert response.status_code == 401


async def test_upload_stores_original_and_queues_digest(
    client, auth_headers, owner, scheduled_digests
):
    response = await _upload(client, auth_headers)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "UPLOADED" and body["reindexable"] is True
    assert body["mime_type"] == "text/markdown" and body["size_bytes"] == len(MD)
    doc = await _doc(body["id"])
    assert doc.user_id == owner.id
    assert await get_file_store().get(doc.storage_key) == MD
    assert [str(i) for i in scheduled_digests] == [body["id"]]


async def test_digest_makes_document_ready_with_chunk_metadata(
    client, auth_headers, fake_embeddings
):
    doc_id = (await _upload(client, auth_headers)).json()["id"]

    await ingest.digest_document(doc_id)

    doc = await _doc(doc_id)
    assert doc.status == DocStatusEnum.READY and doc.error_message is None
    assert doc.chunk_count == 2 and doc.embedding_model == "custom"
    chunks = await _chunks(doc_id)
    assert [(c.ordinal, c.heading_path) for c in chunks] == [(0, "Lease"), (1, "Lease › Pets")]
    assert chunks[1].content == "One cat allowed with a deposit."
    assert chunks[1].token_count > 0


async def test_pdf_digest_keeps_pages(client, auth_headers, fake_embeddings):
    pdf = make_pdf(["Page one words", "Page two words"])
    doc_id = (await _upload(client, auth_headers, "scan.pdf", pdf)).json()["id"]

    await ingest.digest_document(doc_id)

    assert [c.page for c in await _chunks(doc_id)] == [1, 2]


async def test_digest_without_embedding_key_is_an_error(client, auth_headers):
    doc_id = (await _upload(client, auth_headers)).json()["id"]

    await ingest.digest_document(doc_id)

    doc = await _doc(doc_id)
    assert doc.status == DocStatusEnum.ERROR
    assert "OPENAI_API_KEY" in doc.error_message
    assert await _chunks(doc_id) == []


async def test_unexpected_digest_failure_is_recorded_without_internals(client, auth_headers):
    async def boom(texts):
        raise RuntimeError("secret connection string")

    embeddings.set_embedder(boom)
    doc_id = (await _upload(client, auth_headers)).json()["id"]

    await ingest.digest_document(doc_id)

    doc = await _doc(doc_id)
    assert doc.status == DocStatusEnum.ERROR
    assert doc.error_message == "Unexpected error while digesting the document."


async def test_chunk_cap_rejects_huge_documents(client, auth_headers, fake_embeddings, monkeypatch):
    monkeypatch.setattr(settings, "RAG_MAX_CHUNKS", 1)
    doc_id = (await _upload(client, auth_headers)).json()["id"]

    await ingest.digest_document(doc_id)

    doc = await _doc(doc_id)
    assert doc.status == DocStatusEnum.ERROR and "too large" in doc.error_message


async def test_upload_rejects_oversized_and_unsupported_files(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "RAG_MAX_UPLOAD_MB", 1)
    too_big = await _upload(client, auth_headers, "big.txt", b"a" * (1024 * 1024 + 1))
    binary = await _upload(client, auth_headers, "app.exe", b"MZ\x90\x00\x03\x00")
    fake_pdf = await _upload(client, auth_headers, "x.pdf", b"not a pdf")

    assert too_big.status_code == 413
    assert binary.status_code == 415
    assert fake_pdf.status_code == 415
    async with async_session_factory() as db:
        assert await db.scalar(select(func.count(Document.id))) == 0


async def test_sweep_resumes_waiting_and_stale_documents(
    client, auth_headers, scheduled_digests, fake_embeddings
):
    waiting = (await _upload(client, auth_headers, "a.md")).json()["id"]
    stale = (await _upload(client, auth_headers, "b.md")).json()["id"]
    fresh = (await _upload(client, auth_headers, "c.md")).json()["id"]
    async with async_session_factory() as db:
        for doc_id, age in ((stale, timedelta(minutes=30)), (fresh, timedelta(minutes=1))):
            doc = await db.get(Document, doc_id)
            doc.status = DocStatusEnum.DIGESTING
            doc.status_changed_at = utcnow() - age
        await db.commit()
    scheduled_digests.clear()

    assert await ingest.sweep_pending() == 2
    assert sorted(str(i) for i in scheduled_digests) == sorted([waiting, stale])


async def test_list_shows_only_own_documents(client, auth_headers, other_user):
    async with async_session_factory() as db:
        db.add(Document(user_id=other_user.id, filename="theirs.txt"))
        await db.commit()
    await _upload(client, auth_headers)

    response = await client.get("/documents", headers=auth_headers)

    assert [d["filename"] for d in response.json()] == ["lease.md"]


async def test_other_users_documents_are_not_found(client, auth_headers, other_user):
    async with async_session_factory() as db:
        theirs = Document(user_id=other_user.id, filename="theirs.txt", storage_key="k")
        db.add(theirs)
        await db.commit()

    reindex = await client.post(f"/documents/{theirs.id}/reindex", headers=auth_headers)
    delete = await client.delete(f"/documents/{theirs.id}", headers=auth_headers)

    assert reindex.status_code == 404 and delete.status_code == 404
    assert await _doc(theirs.id) is not None


async def test_delete_cascades_chunks_and_removes_original(client, auth_headers, fake_embeddings):
    doc_id = (await _upload(client, auth_headers)).json()["id"]
    await ingest.digest_document(doc_id)
    key = (await _doc(doc_id)).storage_key

    response = await client.delete(f"/documents/{doc_id}", headers=auth_headers)

    assert response.status_code == 204
    assert await _doc(doc_id) is None and await _chunks(doc_id) == []
    try:
        await get_file_store().get(key)
        raise AssertionError("original should be deleted")
    except FileNotFoundError:
        pass


async def test_reindex_requeues_and_replaces_chunks(
    client, auth_headers, fake_embeddings, scheduled_digests
):
    doc_id = (await _upload(client, auth_headers)).json()["id"]
    await ingest.digest_document(doc_id)
    first = {c.id for c in await _chunks(doc_id)}
    scheduled_digests.clear()

    response = await client.post(f"/documents/{doc_id}/reindex", headers=auth_headers)
    again = await client.post(f"/documents/{doc_id}/reindex", headers=auth_headers)
    await ingest.digest_document(doc_id)

    assert response.status_code == 202 and response.json()["status"] == "UPLOADED"
    assert again.status_code == 409
    assert [str(i) for i in scheduled_digests] == [doc_id]
    chunks = await _chunks(doc_id)
    assert len(chunks) == 2 and not first & {c.id for c in chunks}


async def test_reindex_of_legacy_document_is_a_conflict(client, auth_headers, owner):
    async with async_session_factory() as db:
        legacy = Document(user_id=owner.id, filename="old.txt", status=DocStatusEnum.READY)
        db.add(legacy)
        await db.commit()

    response = await client.post(f"/documents/{legacy.id}/reindex", headers=auth_headers)

    assert response.status_code == 409


async def test_url_ingest_fetches_and_titles_the_page(
    client, auth_headers, fake_embeddings, monkeypatch
):
    from src.services.rag import fetch

    body = "".join(f"<p>Paragraph {i} explaining sourdough starter care.</p>" for i in range(8))
    html = (
        "<html><head><title>Sourdough guide</title></head>"
        f"<body><article>{body}</article></body></html>"
    )

    async def fake_fetch(url):
        return fetch.Fetched(url, html.encode(), "text/html")

    monkeypatch.setattr(ingest, "fetch_url", fake_fetch)
    response = await client.post(
        "/documents/url", json={"url": "https://example.com/bread"}, headers=auth_headers
    )
    doc_id = response.json()["id"]

    await ingest.digest_document(doc_id)

    doc = await _doc(doc_id)
    assert response.status_code == 202
    assert doc.status == DocStatusEnum.READY and doc.filename == "Sourdough guide"
    assert doc.source_url == "https://example.com/bread" and doc.mime_type == "text/html"
    assert await get_file_store().get(doc.storage_key) == html.encode()


async def test_url_ingest_rejects_non_http_urls(client, auth_headers):
    response = await client.post(
        "/documents/url", json={"url": "file:///etc/passwd"}, headers=auth_headers
    )
    assert response.status_code == 422
