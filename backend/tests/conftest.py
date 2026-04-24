import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Provide a session-scoped event loop so asyncpg connections stay valid across tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
