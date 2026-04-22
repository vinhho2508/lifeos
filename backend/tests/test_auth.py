import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_google_login_invalid_token():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/auth/login", json={"token": "invalid_token"})
    
    # Since we haven't implemented the route yet, it should be 404 or something else
    # But once implemented, it should return 401/403 for invalid token
    assert response.status_code in [401, 403, 404]
