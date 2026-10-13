from datetime import UTC, datetime, timedelta

import pytest
from langchain_core.messages import AIMessage

from src.core.database import async_session_factory
from src.models.all_models import DocStatusEnum, Document, DocumentChunk
from src.services import task_service
from tests.agent_helpers import call, run_turn, tasks_of, use_script
from tests.conftest import set_timezone
from tests.rag_helpers import fake_vector


def test_parse_due_date_reads_naive_values_in_user_timezone():
    due = task_service.parse_due_date("2026-10-10T09:00", "Asia/Ho_Chi_Minh")
    assert due == datetime(2026, 10, 10, 2, 0, tzinfo=UTC)


def test_parse_due_date_keeps_explicit_offsets():
    due = task_service.parse_due_date("2026-10-10T09:00+00:00", "Asia/Ho_Chi_Minh")
    assert due == datetime(2026, 10, 10, 9, 0, tzinfo=UTC)


def test_parse_due_date_bare_date_means_9am_local():
    due = task_service.parse_due_date("2026-10-10", "America/New_York")
    assert due == datetime(2026, 10, 10, 13, 0, tzinfo=UTC)


def test_parse_due_date_rejects_garbage():
    with pytest.raises(ValueError):
        task_service.parse_due_date("next friday", "UTC")


async def test_create_task_resolves_due_date_in_user_timezone(owner, monkeypatch):
    await set_timezone(owner, "Asia/Ho_Chi_Minh")
    model = use_script(
        monkeypatch,
        call("create_task", "c1", title="Pay rent", due_date="2026-10-10T09:00"),
        AIMessage(content="Added."),
    )

    events = await run_turn(owner, "remind me to pay rent Friday 9am")

    system_prompt = model.calls[0][0].content
    assert "(Asia/Ho_Chi_Minh)" in system_prompt and "+0700" in system_prompt

    [task] = await tasks_of(owner)
    assert task.due_date == datetime(2026, 10, 10, 2, 0, tzinfo=UTC)
    result = next(e for e in events if e["type"] == "tool_result")
    # Shown back to the model and UI in local time.
    assert result["output"]["due_date"] == "2026-10-10T09:00+07:00"
    assert result["summary"] == "Created 'Pay rent' due 2026-10-10T09:00+07:00"


async def test_invalid_due_date_is_a_tool_error(owner, monkeypatch):
    use_script(
        monkeypatch,
        call("create_task", "c1", title="Pay rent", due_date="friday-ish"),
        AIMessage(content="When exactly?"),
    )

    events = await run_turn(owner, "remind me to pay rent friday-ish")

    result = next(e for e in events if e["type"] == "tool_result")
    assert result["status"] == "error"
    assert "not ISO-8601" in result["summary"]
    assert await tasks_of(owner) == []


async def test_tools_only_see_the_current_users_tasks(owner, other_user, monkeypatch):
    async with async_session_factory() as db:
        theirs = await task_service.create_task(db, other_user.id, "Their secret task")
        await task_service.create_task(db, owner.id, "My task")

    use_script(
        monkeypatch,
        call("list_tasks", "c1"),
        call("update_task", "c2", task_id=str(theirs.id), status="DONE"),
        AIMessage(content="ok"),
    )

    events = await run_turn(owner, "list and finish tasks")

    listed, updated = [e for e in events if e["type"] == "tool_result"]
    assert [t["title"] for t in listed["output"]] == ["My task"]
    assert updated["status"] == "error"
    assert "no task with id" in updated["summary"]
    [task] = await tasks_of(other_user)
    assert task.status.value == "TODO"


async def test_list_tasks_overdue_only(owner, monkeypatch):
    now = datetime.now(UTC)
    async with async_session_factory() as db:
        await task_service.create_task(db, owner.id, "Late", due_date=now - timedelta(days=1))
        await task_service.create_task(db, owner.id, "Future", due_date=now + timedelta(days=1))
        done = await task_service.create_task(
            db, owner.id, "Late but done", due_date=now - timedelta(days=2)
        )
        await task_service.update_task(db, done, status=task_service.StatusEnum.DONE)

    use_script(monkeypatch, call("list_tasks", "c1", overdue_only=True), AIMessage(content="ok"))

    events = await run_turn(owner, "what's overdue?")

    result = next(e for e in events if e["type"] == "tool_result")
    assert [t["title"] for t in result["output"]] == ["Late"]
    assert result["summary"] == "1 overdue task"


async def test_search_documents_emits_citations_for_own_documents_only(
    owner, other_user, monkeypatch, fake_embeddings
):
    async with async_session_factory() as db:
        mine = Document(user_id=owner.id, filename="lease.pdf", status=DocStatusEnum.READY)
        theirs = Document(user_id=other_user.id, filename="theirs.txt")
        db.add_all([mine, theirs])
        await db.flush()
        db.add_all(
            [
                DocumentChunk(
                    document_id=mine.id,
                    content="Pets allowed with deposit.",
                    page=4,
                    heading_path="Rules › Pets",
                    embedding=fake_vector("Pets allowed with deposit."),
                ),
                DocumentChunk(
                    document_id=theirs.id,
                    content="Their private pets text.",
                    embedding=fake_vector("Their private pets text."),
                ),
            ]
        )
        await db.commit()

    model = use_script(
        monkeypatch,
        call("search_documents", "c1", query="pets"),
        AIMessage(content="Pets are allowed with a deposit (lease.pdf, p.4)."),
    )

    events = await run_turn(owner, "does my lease allow pets?")

    citations = [e for e in events if e["type"] == "citation"]
    assert [c["source_name"] for c in citations] == ["lease.pdf"]
    assert citations[0]["chunk_text"] == "Pets allowed with deposit."
    tool_message = model.calls[1][-1].content
    assert "Their private" not in tool_message
    assert "[1] lease.pdf · p.4 · Rules › Pets" in tool_message
    result = next(e for e in events if e["type"] == "tool_result")
    assert result["summary"] == "1 passage found"
    assert result["output"][0]["page"] == 4


async def test_search_documents_without_embedding_key_is_a_tool_error(owner, monkeypatch):
    use_script(
        monkeypatch, call("search_documents", "c1", query="pets"), AIMessage(content="Sorry.")
    )

    events = await run_turn(owner, "does my lease allow pets?")

    result = next(e for e in events if e["type"] == "tool_result")
    assert result["status"] == "error"
    assert "not configured" in result["summary"]


async def test_list_documents_returns_own_documents(owner, other_user, monkeypatch):
    async with async_session_factory() as db:
        db.add_all(
            [
                Document(
                    user_id=owner.id,
                    filename="lease.pdf",
                    status=DocStatusEnum.READY,
                    chunk_count=3,
                ),
                Document(user_id=owner.id, filename="draft.md", status=DocStatusEnum.ERROR),
                Document(user_id=other_user.id, filename="theirs.txt"),
            ]
        )
        await db.commit()
    use_script(monkeypatch, call("list_documents", "c1"), AIMessage(content="You have two."))

    events = await run_turn(owner, "what documents do I have?")

    result = next(e for e in events if e["type"] == "tool_result")
    assert sorted(d["name"] for d in result["output"]) == ["draft.md", "lease.pdf"]
    assert result["summary"] == "2 documents (1 searchable)"


async def test_generate_image_url_never_reaches_the_model(owner, monkeypatch):
    from src.services.image_generation import image_service

    data_url = "data:image/png;base64," + "A" * 10_000

    async def fake_generate(prompt):
        return data_url

    monkeypatch.setattr(image_service, "generate_image", fake_generate)
    model = use_script(
        monkeypatch, call("generate_image", "c1", prompt="a cat"), AIMessage(content="Here!")
    )

    events = await run_turn(owner, "draw a cat")

    image = next(e for e in events if e["type"] == "image")
    assert image == {"type": "image", "url": data_url, "alt": "a cat"}
    assert data_url not in model.calls[1][-1].content
    result = next(e for e in events if e["type"] == "tool_result")
    assert data_url not in str(result["output"])
