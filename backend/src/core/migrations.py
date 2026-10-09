"""Run Alembic migrations at startup (and from the test suite)."""

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from src.core.database import engine
from src.core.logging import logger

BASELINE_REVISION = "0001"
_BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "migrations"))
    # Keep the app's logging setup instead of alembic.ini's.
    cfg.attributes["configure_logger"] = False
    return cfg


async def _needs_baseline_stamp() -> bool:
    """Databases created before migrations existed have tables but no alembic_version."""
    async with engine.connect() as conn:
        users = await conn.scalar(text("SELECT to_regclass('public.users')"))
        version = await conn.scalar(text("SELECT to_regclass('public.alembic_version')"))
    return users is not None and version is None


async def run_migrations() -> None:
    cfg = _alembic_config()
    if await _needs_baseline_stamp():
        logger.info("Existing schema without migration history; stamping baseline.")
        await asyncio.to_thread(command.stamp, cfg, BASELINE_REVISION)
    # env.py calls asyncio.run(), so it must run outside this event loop.
    await asyncio.to_thread(command.upgrade, cfg, "head")
