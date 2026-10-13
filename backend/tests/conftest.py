"""Test setup: an isolated *_test database, no network, migrations applied once.

The database URL comes from TEST_DATABASE_URL, or DATABASE_URL (env or .env) with
"_test" appended to the database name. Tests refuse to run against any database
whose name does not end in "_test", because they truncate tables.
"""

import os

from tests.db_url import is_test_database, test_database_url

# Must happen before anything imports src.core.database (it builds the engine on import).
os.environ["DATABASE_URL"] = test_database_url()
for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "S3_BUCKET_NAME"):
    os.environ[key] = ""
os.environ["SECRET_KEY"] = "test-secret-key"  # noqa: S105
os.environ["SLACK_SERVICE_TOKEN"] = "test-service-token"  # noqa: S105
os.environ["ALLOWED_USER_EMAIL"] = "owner@example.com"

if not is_test_database(os.environ["DATABASE_URL"]):
    raise RuntimeError("Refusing to run tests against a non-*_test database")

import uuid  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.core.auth import create_access_token  # noqa: E402
from src.core.database import async_session_factory, engine  # noqa: E402
from src.models.all_models import User, UserSettings  # noqa: E402

OWNER_EMAIL = "owner@example.com"
_TABLES = "document_chunks, documents, messages, conversations, tasks, user_settings, users"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _migrated_schema():
    from src.core.migrations import run_migrations

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await run_migrations()
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {_TABLES} RESTART IDENTITY CASCADE"))
    yield


@pytest_asyncio.fixture
async def owner() -> User:
    async with async_session_factory() as db:
        user = User(email=OWNER_EMAIL)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


@pytest_asyncio.fixture
async def other_user() -> User:
    async with async_session_factory() as db:
        user = User(email=f"other-{uuid.uuid4().hex[:6]}@example.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def set_timezone(user: User, tz: str) -> None:
    async with async_session_factory() as db:
        db.add(
            UserSettings(
                user_id=user.id, chat_provider="openai", chat_model="gpt-5.4-nano", timezone=tz
            )
        )
        await db.commit()


@pytest.fixture
def auth_headers(owner) -> dict:
    token = create_access_token({"sub": owner.email, "user_id": str(owner.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    from src.main import app

    # ASGITransport does not run the lifespan: no cron, no checkpointer (runs use none).
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
