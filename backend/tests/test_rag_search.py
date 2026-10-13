import pytest

from src.core.database import async_session_factory
from src.models.all_models import DocStatusEnum, Document, DocumentChunk
from src.services.rag import fetch
from src.services.rag.search import hybrid_search
from tests.rag_helpers import fake_vector


async def _doc(
    user, name, chunks: list[str], vector_text: str | None = None, headings=None
) -> Document:
    """A ready document; vector_text overrides what the chunk vectors are built from."""
    async with async_session_factory() as db:
        doc = Document(
            user_id=user.id, filename=name, status=DocStatusEnum.READY, chunk_count=len(chunks)
        )
        db.add(doc)
        await db.flush()
        db.add_all(
            DocumentChunk(
                document_id=doc.id,
                ordinal=i,
                content=text,
                heading_path=headings[i] if headings else None,
                embedding=fake_vector(vector_text or text),
            )
            for i, text in enumerate(chunks)
        )
        await db.commit()
        return doc


async def test_keyword_only_match_is_found_by_full_text(owner, fake_embeddings):
    # The vectors carry no signal for the rare token; only full-text search can find it.
    await _doc(owner, "router.md", ["The router serial is XK-99871Q."], vector_text="unrelated")
    await _doc(owner, "notes.md", ["Shopping list: eggs and milk."], vector_text="unrelated")

    hits = await hybrid_search(owner.id, "XK-99871Q serial", k=3)
    vector_only = await hybrid_search(owner.id, "XK-99871Q serial", k=3, mode="vector")

    assert hits[0].source_name == "router.md"
    assert all(h.source_name != "router.md" for h in vector_only)


async def test_semantic_match_and_floor(owner, fake_embeddings):
    await _doc(owner, "lease.md", ["pets allowed with deposit"])
    await _doc(owner, "garden.md", ["tomatoes need morning water"])

    hits = await hybrid_search(owner.id, "pets deposit", k=5)

    assert [h.source_name for h in hits] == ["lease.md"]


async def test_search_is_scoped_to_user_and_document_ids(owner, other_user, fake_embeddings):
    mine = await _doc(owner, "a.md", ["budget for travel"])
    other = await _doc(owner, "b.md", ["budget for food"])
    await _doc(other_user, "theirs.md", ["budget secrets"])

    everything = await hybrid_search(owner.id, "budget", k=5)
    scoped = await hybrid_search(owner.id, "budget", k=5, document_ids=[other.id])

    assert sorted(h.source_name for h in everything) == ["a.md", "b.md"]
    assert [h.document_id for h in scoped] == [other.id]
    assert mine.id not in {h.document_id for h in scoped}


async def test_adjacent_chunks_are_merged(owner, fake_embeddings):
    await _doc(
        owner,
        "guide.md",
        ["kayak launch steps begin here", "here kayak launch steps continue", "unrelated end"],
    )

    hits = await hybrid_search(owner.id, "kayak launch steps", k=5)

    assert len(hits) == 1
    assert hits[0].content == "kayak launch steps begin here kayak launch steps continue"
    assert sorted(hits[0].ordinals) == [0, 1] and hits[0].ordinal == 0


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "::1"])
async def test_url_fetch_refuses_private_addresses(monkeypatch, address):
    async def resolve(host):
        return [address]

    monkeypatch.setattr(fetch, "_resolve", resolve)

    with pytest.raises(fetch.FetchError, match="private or local"):
        await fetch.fetch_url("http://internal.example/")


async def test_chunks_of_different_sections_are_not_merged(owner, fake_embeddings):
    await _doc(
        owner,
        "lease.md",
        ["deposit is two months rent", "pet deposit is three million"],
        headings=["Deposit", "Pets"],
    )

    hits = await hybrid_search(owner.id, "pet deposit", k=5)

    assert [h.heading_path for h in hits] == ["Pets", "Deposit"]
