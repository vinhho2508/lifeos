"""Retrieval eval: does search find the right passage? Compares vector-only and hybrid.

Digests a small fixture corpus (scripts/rag_eval_corpus/) with real OpenAI embeddings into
the isolated *_test database, runs labeled queries, and prints recall@k and MRR. A hit is
a returned passage from the expected document whose heading path ends with the expected
heading. Costs well under a cent. Needs OPENAI_API_KEY.

    cd backend
    python -m scripts.rag_eval
"""

import os
import sys
import tempfile

from tests.db_url import test_database_url

# Same isolation as the test suite: never touch the dev database or real uploads.
os.environ["DATABASE_URL"] = test_database_url()
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="lifeos-rag-eval-")
os.environ["S3_BUCKET_NAME"] = ""

import asyncio  # noqa: E402
import json  # noqa: E402
import uuid  # noqa: E402
from pathlib import Path  # noqa: E402

from sqlalchemy import text  # noqa: E402

from src.core.database import async_session_factory, engine, settings  # noqa: E402
from src.core.migrations import run_migrations  # noqa: E402
from src.models.all_models import DocStatusEnum, Document, User  # noqa: E402
from src.services.rag import ingest, parsers  # noqa: E402
from src.services.rag.search import Hit, hybrid_search  # noqa: E402
from src.services.rag.storage import get_file_store, storage_key  # noqa: E402

CORPUS = Path(__file__).parent / "rag_eval_corpus"
K = 5


async def seed() -> uuid.UUID:
    await run_migrations()
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE document_chunks, documents, users CASCADE"))
    async with async_session_factory() as db:
        user = User(email="rag-eval@example.com")
        db.add(user)
        await db.flush()
        docs = []
        for path in sorted(CORPUS.iterdir()):
            if path.suffix == ".json":
                continue
            data = path.read_bytes()
            doc = Document(
                id=uuid.uuid4(),
                user_id=user.id,
                filename=path.name,
                mime_type=parsers.detect_type(path.name, data[:4096]),
                size_bytes=len(data),
            )
            doc.storage_key = storage_key(user.id, doc.id)
            await get_file_store().put(doc.storage_key, data, doc.mime_type)
            docs.append(doc)
        db.add_all(docs)
        await db.commit()
    for doc in docs:
        await ingest.digest_document(doc.id)
    async with async_session_factory() as db:
        for doc in docs:
            stored = await db.get(Document, doc.id)
            if stored.status != DocStatusEnum.READY:
                sys.exit(f"{doc.filename}: {stored.status.value} {stored.error_message}")
    return user.id


def rank_of(hits: list[Hit], case: dict) -> int | None:
    for i, hit in enumerate(hits, 1):
        if hit.source_name == case["doc"] and (hit.heading_path or "").endswith(case["heading"]):
            return i
    return None


async def main() -> None:
    if not settings.OPENAI_API_KEY:
        sys.exit("OPENAI_API_KEY is not set")
    user_id = await seed()
    cases = json.loads((CORPUS / "queries.json").read_text())

    scores = {}
    for mode in ("vector", "hybrid"):
        ranks = [rank_of(await hybrid_search(user_id, c["query"], K, mode=mode), c) for c in cases]
        misses = [c["query"] for c, r in zip(cases, ranks, strict=True) if r is None]
        recall = sum(r is not None for r in ranks) / len(cases)
        mrr = sum(1 / r for r in ranks if r) / len(cases)
        scores[mode] = (recall, mrr)
        print(f"{mode:>7}: recall@{K} {recall:.2f}  MRR {mrr:.2f}")
        for query in misses:
            print(f"         miss: {query}")
    await engine.dispose()
    if scores["hybrid"][0] < scores["vector"][0]:
        sys.exit("hybrid recall is below vector-only")


if __name__ == "__main__":
    asyncio.run(main())
