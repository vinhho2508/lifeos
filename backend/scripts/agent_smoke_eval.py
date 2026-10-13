"""Smoke eval: does each provider pick the right tools?

Runs a fixed set of chat turns through the real agent (real provider, real tools)
against an isolated *_test database, and checks the tool calls each turn makes.
Costs a few cents per provider. Providers without an API key are skipped.

    cd backend
    python -m scripts.agent_smoke_eval                 # all providers with a key
    python -m scripts.agent_smoke_eval openai gemini   # a subset
"""

import os
import sys

from tests.db_url import test_database_url

# Same isolation as the test suite: never touch the dev database.
os.environ["DATABASE_URL"] = test_database_url()

import asyncio  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from typing import Callable  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

from sqlalchemy import text  # noqa: E402

from src.agent import runner  # noqa: E402
from src.core.database import async_session_factory, engine  # noqa: E402
from src.core.migrations import run_migrations  # noqa: E402
from src.models.all_models import (  # noqa: E402
    DocStatusEnum,
    Document,
    DocumentChunk,
    PlatformEnum,
    User,
    UserSettings,
)
from src.providers.factory import get_chat_provider  # noqa: E402
from src.providers.models import AVAILABLE_PROVIDERS  # noqa: E402
from src.services import task_service  # noqa: E402
from src.services.rag.embeddings import embed  # noqa: E402

TIMEZONE = "Asia/Ho_Chi_Minh"


def next_friday_9am() -> str:
    now = datetime.now(ZoneInfo(TIMEZONE))
    days = (4 - now.weekday()) % 7 or 7
    return (now + timedelta(days=days)).strftime("%Y-%m-%dT09:00")


@dataclass
class Case:
    name: str
    message: str
    check: Callable[[list[dict]], str | None]  # returns a failure reason, or None


def calls(events: list[dict]) -> list[dict]:
    return [e for e in events if e["type"] == "tool_call"]


def no_tools(events):
    names = [c["name"] for c in calls(events)]
    return f"called {names}" if names else None


def creates_friday_task(events):
    created = [c for c in calls(events) if c["name"] == "create_task"]
    if len(created) != 1:
        return f"expected one create_task, got {[c['name'] for c in calls(events)]}"
    due = (created[0]["input"].get("due_date") or "")[:16]
    return None if due == next_friday_9am() else f"due_date {due!r} != {next_friday_9am()}"


def lists_overdue(events):
    listed = [c for c in calls(events) if c["name"] == "list_tasks"]
    if not listed or not listed[0]["input"].get("overdue_only"):
        return f"expected list_tasks(overdue_only=True), got {calls(events)}"
    return None


def searches_documents(events):
    names = [c["name"] for c in calls(events)]
    if "search_documents" not in names:
        return f"expected search_documents, got {names}"
    return None if any(e["type"] == "citation" for e in events) else "no citations"


def list_then_update(events):
    names = [c["name"] for c in calls(events)]
    if names[:1] != ["list_tasks"] or "update_task" not in names:
        return f"expected list_tasks then update_task, got {names}"
    failed = [e for e in events if e["type"] == "tool_result" and e["status"] == "error"]
    return f"tool errors: {[e['summary'] for e in failed]}" if failed else None


CASES = [
    Case("small talk", "hi! how's it going?", no_tools),
    Case("thanks", "thanks, that's all for now", no_tools),
    Case("create with date", "remind me to pay rent next Friday at 9am", creates_friday_task),
    Case("overdue", "what's overdue?", lists_overdue),
    Case("documents", "does my lease allow pets?", searches_documents),
    Case("chain", "what's overdue? mark the oldest one done", list_then_update),
]


async def reset_and_seed() -> User:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE document_chunks, documents, messages, tasks, user_settings, users "
                "RESTART IDENTITY CASCADE"
            )
        )
    async with async_session_factory() as db:
        user = User(email="eval@example.com")
        db.add(user)
        await db.flush()
        db.add(UserSettings(user_id=user.id, timezone=TIMEZONE))
        overdue = datetime.now(UTC) - timedelta(days=2)
        await task_service.create_task(db, user.id, "Renew passport", due_date=overdue)
        lease = Document(
            user_id=user.id, filename="lease.txt", status=DocStatusEnum.READY, chunk_count=1
        )
        db.add(lease)
        await db.flush()
        chunk = "Pets: tenants may keep one cat or dog with a $300 refundable pet deposit."
        db.add(
            DocumentChunk(document_id=lease.id, content=chunk, embedding=(await embed([chunk]))[0])
        )
        await db.commit()
        await db.refresh(user)
        return user


async def eval_provider(name: str) -> list[tuple[str, str | None]]:
    model = AVAILABLE_PROVIDERS[name]["default_model"]
    provider = get_chat_provider(name, model)
    runner.build_model = lambda _settings: provider.get_langchain_llm(streaming=True)
    results = []
    for case in CASES:
        # Each case starts from a fresh database so earlier turns can't help or hurt.
        user = await reset_and_seed()
        run = await runner.start_run(user.id, case.message, PlatformEnum.WEB)
        events = [e async for e in run.events()]
        error = next((e["message"] for e in events if e["type"] == "error"), None)
        results.append((case.name, error or case.check(events)))
    return results


async def main(selected: list[str]) -> int:
    await run_migrations()
    providers = selected or list(AVAILABLE_PROVIDERS)
    failures = 0
    for name in providers:
        model = AVAILABLE_PROVIDERS[name]["default_model"]
        if not get_chat_provider(name, model).api_key:
            print(f"\n{name}: skipped (no API key)")
            continue
        results = await eval_provider(name)
        passed = sum(1 for _, failure in results if failure is None)
        print(f"\n{name} ({model}): {passed}/{len(results)}")
        for case_name, failure in results:
            print(
                f"  {'PASS' if failure is None else 'FAIL'}  {case_name}"
                + (f": {failure}" if failure else "")
            )
        failures += len(results) - passed
    await engine.dispose()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
