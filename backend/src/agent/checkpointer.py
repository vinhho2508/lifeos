"""LangGraph checkpointer lifecycle.

One short-lived thread per run (thread_id = run_id). The messages table stays the
conversation history; checkpoints only exist so a paused run (human approval, planned)
can resume after a restart. Threads older than RETENTION_DAYS are pruned daily.
"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from src.core.database import settings
from src.core.logging import logger

RETENTION_DAYS = 7

_pool: AsyncConnectionPool | None = None
_saver: AsyncPostgresSaver | None = None


def _psycopg_url() -> str:
    # The app uses asyncpg through SQLAlchemy; psycopg wants a plain libpq URL.
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def open_checkpointer() -> None:
    global _pool, _saver
    _pool = AsyncConnectionPool(
        _psycopg_url(),
        min_size=1,
        max_size=2,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    await _pool.open()
    _saver = AsyncPostgresSaver(_pool)
    await _saver.setup()
    logger.info("Agent checkpointer ready")


async def close_checkpointer() -> None:
    global _pool, _saver
    if _pool is not None:
        await _pool.close()
    _pool = _saver = None


def get_checkpointer() -> AsyncPostgresSaver | None:
    """None when not opened (tests, scripts); the agent then runs without checkpoints."""
    return _saver


async def prune_old_threads() -> int:
    if _saver is None or _pool is None:
        return 0
    async with _pool.connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT DISTINCT thread_id FROM checkpoints "
                "WHERE (checkpoint->>'ts')::timestamptz < now() - make_interval(days => %s)",
                (RETENTION_DAYS,),
            )
        ).fetchall()
    for row in rows:
        await _saver.adelete_thread(row["thread_id"])
    if rows:
        logger.info(f"Pruned {len(rows)} agent checkpoint thread(s)")
    return len(rows)
