"""Hybrid retrieval: pgvector cosine + Postgres full-text, fused with Reciprocal Rank Fusion."""

import re
import uuid
from dataclasses import dataclass, field
from typing import Literal

from pgvector.sqlalchemy import Vector
from sqlalchemy import bindparam, text

from src.core.database import async_session_factory, settings
from src.services.rag.embeddings import EMBEDDING_DIM, embed

CANDIDATES = 30  # per retriever
RRF_K = 60
MAX_MERGED_CHUNKS = 3

# Kept tiny on purpose: the 'simple' FTS config does no stemming or stopword removal (so it
# works for any language), and these words would otherwise match nearly every chunk.
_STOPWORDS = frozenset(
    "a an and are as at be by can could did do does for from had has have how i if in is it "
    "its me my of on or our should so than that the their them then there these they this "
    "to was we were what when where which who why will with would you your".split()
)
_TOKEN = re.compile(r"\w+", re.UNICODE)

_SQL = """
WITH vec AS (
    SELECT c.id, row_number() OVER (ORDER BY c.embedding <=> :qvec) AS rank
    FROM document_chunks c JOIN documents d ON d.id = c.document_id
    WHERE d.user_id = :user_id {doc_filter}
    ORDER BY c.embedding <=> :qvec
    LIMIT :candidates
),
fts AS (
    SELECT c.id,
           row_number() OVER (
               ORDER BY ts_rank_cd(c.content_tsv, to_tsquery('simple', :tsquery)) DESC
           ) AS rank
    FROM document_chunks c JOIN documents d ON d.id = c.document_id
    WHERE :use_fts AND d.user_id = :user_id {doc_filter}
      AND c.content_tsv @@ to_tsquery('simple', :tsquery)
    ORDER BY ts_rank_cd(c.content_tsv, to_tsquery('simple', :tsquery)) DESC
    LIMIT :candidates
)
SELECT c.document_id, d.filename, c.content, c.page, c.heading_path, c.ordinal,
       1 - (c.embedding <=> :qvec) AS similarity,
       vec.rank AS vector_rank, fts.rank AS text_rank,
       COALESCE(1.0 / (:rrf_k + vec.rank), 0) + COALESCE(1.0 / (:rrf_k + fts.rank), 0) AS rrf
FROM vec FULL OUTER JOIN fts ON vec.id = fts.id
JOIN document_chunks c ON c.id = COALESCE(vec.id, fts.id)
JOIN documents d ON d.id = c.document_id
ORDER BY rrf DESC
"""


@dataclass
class Hit:
    document_id: uuid.UUID
    source_name: str
    content: str
    page: int | None
    heading_path: str | None
    ordinal: int
    similarity: float
    score: float
    ordinals: list[int] = field(default_factory=list)

    def as_citation(self) -> dict:
        return {
            "document_id": str(self.document_id),
            "source_name": self.source_name,
            "chunk_text": self.content,
            "score": round(self.similarity, 3),
            "page": self.page,
            "heading_path": self.heading_path,
            "ordinal": self.ordinal,
        }


def to_tsquery(query: str) -> str:
    """OR of the query's meaningful words, safe to pass to to_tsquery('simple', ...)."""
    words = [w.lower() for w in _TOKEN.findall(query)]
    keep = dict.fromkeys(w for w in words if len(w) > 1 and w not in _STOPWORDS)
    return " | ".join(keep)


async def hybrid_search(
    user_id: uuid.UUID,
    query: str,
    k: int = 5,
    document_ids: list[uuid.UUID] | None = None,
    mode: Literal["hybrid", "vector"] = "hybrid",
) -> list[Hit]:
    [qvec] = await embed([query])
    tsquery = to_tsquery(query) if mode == "hybrid" else ""
    doc_filter = "AND d.id = ANY(:doc_ids)" if document_ids else ""
    params = {
        "qvec": list(qvec),
        "user_id": user_id,
        "candidates": CANDIDATES,
        "tsquery": tsquery or "x",
        "use_fts": bool(tsquery),
        "rrf_k": RRF_K,
    }
    if document_ids:
        params["doc_ids"] = list(document_ids)
    async with async_session_factory() as db:
        sql = text(_SQL.format(doc_filter=doc_filter)).bindparams(
            bindparam("qvec", type_=Vector(EMBEDDING_DIM))
        )
        rows = (await db.execute(sql, params)).all()

    candidates = [
        Hit(
            document_id=r.document_id,
            source_name=r.filename,
            content=r.content,
            page=r.page,
            heading_path=r.heading_path,
            ordinal=r.ordinal,
            similarity=float(r.similarity or 0.0),
            score=float(r.rrf),
            ordinals=[r.ordinal],
        )
        for r in rows
        # A chunk only the vector leg found must at least be somewhat similar.
        if r.text_rank is not None or float(r.similarity or 0.0) >= settings.RAG_MIN_SIMILARITY
    ]
    return merge_adjacent(candidates, k)


def merge_adjacent(candidates: list[Hit], k: int) -> list[Hit]:
    """Fold neighbouring chunks of one section (same document, heading and page) together."""
    results: list[Hit] = []
    for hit in candidates:
        target = next(
            (
                r
                for r in results
                if r.document_id == hit.document_id
                and r.heading_path == hit.heading_path
                and r.page == hit.page
                and len(r.ordinals) < MAX_MERGED_CHUNKS
                and (hit.ordinal == min(r.ordinals) - 1 or hit.ordinal == max(r.ordinals) + 1)
            ),
            None,
        )
        if target is not None:
            if hit.ordinal < min(target.ordinals):
                target.content = join_overlapping(hit.content, target.content)
                target.ordinal = hit.ordinal
            else:
                target.content = join_overlapping(target.content, hit.content)
            target.ordinals.append(hit.ordinal)
            target.similarity = max(target.similarity, hit.similarity)
        elif len(results) < k:
            results.append(hit)
    return results


def join_overlapping(first: str, second: str, max_overlap: int = 2000) -> str:
    """Concatenate two consecutive chunks, dropping the text they share."""
    for size in range(min(len(first), len(second), max_overlap), 0, -1):
        if first.endswith(second[:size]):
            return first + second[size:]
    return f"{first}\n{second}"
