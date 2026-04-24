import uuid
import pytest
import asyncpg
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.core.database import settings


@pytest.mark.asyncio
async def test_chat_stream():
    """Test streaming endpoint with and without a user in the DB."""
    conn = await asyncpg.connect(dsn=settings.DATABASE_URL)
    try:
        await conn.execute(
            "TRUNCATE TABLE document_chunks, documents, messages, tasks, users RESTART IDENTITY CASCADE"
        )
    finally:
        await conn.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # No user in DB -> 401
        response = await ac.post(
            "/chat/stream",
            json={"message": "Hello", "platform": "WEB"},
        )
        assert response.status_code == 401

        # Seed a user directly
        conn = await asyncpg.connect(dsn=settings.DATABASE_URL)
        try:
            await conn.execute(
                "INSERT INTO users (id, email, created_at) VALUES ($1, $2, NOW())",
                uuid.uuid4(),
                "stream-test@example.com",
            )
        finally:
            await conn.close()

        # With a user -> stream reply
        response = await ac.post(
            "/chat/stream",
            json={"message": "Remind me to buy milk", "platform": "WEB"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        body = response.text
        assert len(body) > 0
        assert "buy milk" in body.lower() or "noted" in body.lower() or "remind" in body.lower()
