"""OpenAI embeddings. There is no silent fallback: without a key, embedding fails loudly.

Tests (and evals) swap the implementation with set_embedder().
"""

from collections.abc import Awaitable, Callable

from src.core.database import settings

EMBEDDING_DIM = 1536
BATCH_SIZE = 100
MAX_RETRIES = 4  # the OpenAI client backs off exponentially on 429 / 5xx / timeouts

Embedder = Callable[[list[str]], Awaitable[list[list[float]]]]


class EmbeddingsNotConfigured(Exception):
    """No embedding provider is configured; the message is safe to show the user."""

    def __init__(self):
        super().__init__("Embeddings are not configured (OPENAI_API_KEY is not set).")


async def _openai_embed(texts: list[str]) -> list[list[float]]:
    if not settings.OPENAI_API_KEY:
        raise EmbeddingsNotConfigured()
    import openai

    client = openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY, max_retries=MAX_RETRIES, timeout=60.0
    )
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL, input=texts[start : start + BATCH_SIZE]
        )
        vectors.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))
    return vectors


_embedder: Embedder = _openai_embed


def set_embedder(embedder: Embedder | None) -> None:
    """Replace the embedding function (None restores OpenAI)."""
    global _embedder
    _embedder = embedder or _openai_embed


def model_name() -> str:
    return settings.EMBEDDING_MODEL if _embedder is _openai_embed else "custom"


async def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await _embedder(texts)
