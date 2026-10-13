import json
import uuid

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import select

from src.core.database import async_session_factory
from src.models.all_models import Conversation, Message
from tests.agent_helpers import use_script


async def _say(client, headers, text, conversation_id=None):
    body = {"message": text}
    if conversation_id:
        body["conversation_id"] = conversation_id
    response = await client.post("/chat/stream", json=body, headers=headers)
    assert response.status_code == 200
    [json.loads(line) for line in response.text.splitlines()]  # drain
    return response.headers["x-conversation-id"]


async def test_crud(client, auth_headers):
    created = await client.post("/chat/conversations", headers=auth_headers)
    assert created.status_code == 201
    cid = created.json()["id"]
    assert created.json()["title"] == "New chat"

    renamed = await client.patch(
        f"/chat/conversations/{cid}", json={"title": "Trip"}, headers=auth_headers
    )
    assert renamed.json()["title"] == "Trip"

    listed = await client.get("/chat/conversations", headers=auth_headers)
    assert [c["id"] for c in listed.json()] == [cid]

    deleted = await client.delete(f"/chat/conversations/{cid}", headers=auth_headers)
    assert deleted.status_code == 204
    assert (await client.get("/chat/conversations", headers=auth_headers)).json() == []


async def test_ai_and_ui_only_see_their_conversation(client, auth_headers, monkeypatch):
    model = use_script(
        monkeypatch, AIMessage(content="A1"), AIMessage(content="B1"), AIMessage(content="A2")
    )
    a = (await client.post("/chat/conversations", headers=auth_headers)).json()["id"]
    b = (await client.post("/chat/conversations", headers=auth_headers)).json()["id"]

    await _say(client, auth_headers, "secret apples", a)
    await _say(client, auth_headers, "hello from b", b)
    await _say(client, auth_headers, "more apples", a)

    seen_by_b = [m.content for m in model.calls[1] if isinstance(m, HumanMessage)]
    assert seen_by_b == ["hello from b"]
    seen_by_a = [m.content for m in model.calls[2] if isinstance(m, HumanMessage)]
    assert seen_by_a == ["secret apples", "more apples"]

    msgs = (await client.get(f"/chat/conversations/{b}/messages", headers=auth_headers)).json()
    assert [m["text"] for m in msgs if m["sender"] == "USER"] == ["hello from b"]


async def test_other_users_conversation_is_404(client, auth_headers, other_user):
    async with async_session_factory() as db:
        theirs = Conversation(user_id=other_user.id)
        db.add(theirs)
        await db.commit()
        cid = str(theirs.id)

    for call in (
        client.get(f"/chat/conversations/{cid}/messages", headers=auth_headers),
        client.patch(f"/chat/conversations/{cid}", json={"title": "x"}, headers=auth_headers),
        client.delete(f"/chat/conversations/{cid}", headers=auth_headers),
        client.post(
            "/chat/stream", json={"message": "hi", "conversation_id": cid}, headers=auth_headers
        ),
        client.get(f"/chat/history?conversation_id={cid}", headers=auth_headers),
        client.get(f"/chat/conversations/{uuid.uuid4()}/messages", headers=auth_headers),
    ):
        assert (await call).status_code == 404


async def test_default_conversation_is_latest_and_auto_titled(client, auth_headers, monkeypatch):
    use_script(monkeypatch, AIMessage(content="one"), AIMessage(content="two"))
    first = await _say(client, auth_headers, "plan my week " + "x" * 100)
    second = await _say(client, auth_headers, "and also this")
    assert first == second

    [conv] = (await client.get("/chat/conversations", headers=auth_headers)).json()
    assert conv["title"].startswith("plan my week") and len(conv["title"]) <= 60
    history = (await client.get("/chat/history", headers=auth_headers)).json()
    assert len(history) == 4


async def test_delete_cascades_messages(client, auth_headers, monkeypatch):
    use_script(monkeypatch, AIMessage(content="ok"))
    cid = await _say(client, auth_headers, "hi")
    await client.delete(f"/chat/conversations/{cid}", headers=auth_headers)
    async with async_session_factory() as db:
        assert (await db.execute(select(Message))).scalars().all() == []
