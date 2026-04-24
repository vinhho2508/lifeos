import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.mark.asyncio
async def test_chat_add_task_no_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/chat", json={"message": "Remind me to buy milk", "platform": "WEB"})
    
    # Unauthorized if no token
    assert response.status_code == 401
