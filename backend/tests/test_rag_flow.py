import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_upload_document_no_auth():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/documents/upload", files={"file": ("test.txt", b"test content")})
    
    assert response.status_code == 401
