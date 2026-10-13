import json

from jose import jwt
from langchain_core.messages import AIMessage

from src.core.auth import create_access_token
from tests.agent_helpers import use_script

BODY = {"message": "hi", "platform": "WEB"}


async def test_stream_requires_auth(client, owner):
    response = await client.post("/chat/stream", json=BODY)
    assert response.status_code == 401


async def test_history_requires_auth(client, owner):
    response = await client.get("/chat/history")
    assert response.status_code == 401


async def test_bad_jwt_is_rejected(client, owner):
    forged = jwt.encode({"sub": owner.email}, "wrong-secret", algorithm="HS256")
    response = await client.post(
        "/chat/stream", json=BODY, headers={"Authorization": f"Bearer {forged}"}
    )
    assert response.status_code == 401


async def test_jwt_for_unauthorized_email_is_rejected(client, owner):
    token = create_access_token({"sub": "intruder@example.com"})
    response = await client.post(
        "/chat/stream", json=BODY, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_bad_service_token_is_rejected(client, owner):
    response = await client.post("/chat/stream", json=BODY, headers={"X-Service-Token": "guess"})
    assert response.status_code == 401


async def test_jwt_streams_ndjson(client, auth_headers, monkeypatch):
    use_script(monkeypatch, AIMessage(content="Hello there."))

    response = await client.post("/chat/stream", json=BODY, headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]["type"] == "done"
    assert "".join(e["delta"] for e in events if e["type"] == "text") == "Hello there."


async def test_service_token_acts_as_allowed_user(client, owner, monkeypatch):
    use_script(monkeypatch, AIMessage(content="Hi Slack."))

    response = await client.post(
        "/chat/stream",
        json={"message": "hi", "platform": "SLACK"},
        headers={"X-Service-Token": "test-service-token"},
    )

    assert response.status_code == 200
    history = await client.get("/chat/history", headers={"X-Service-Token": "test-service-token"})
    assert [m["platform"] for m in history.json()] == ["SLACK", "SLACK"]


async def test_non_streaming_chat_endpoint_is_gone(client, auth_headers):
    response = await client.post("/chat/", json=BODY, headers=auth_headers)
    assert response.status_code in (404, 405)
