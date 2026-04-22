import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_get_tasks_no_auth():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/tasks")
    
    assert response.status_code == 401
