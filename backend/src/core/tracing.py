"""LangSmith tracing.

LangChain/LangGraph and langsmith read LANGSMITH_* from the process environment, but
pydantic-settings keeps .env values on the Settings object. Export them so .env works.
"""

import os

from src.core.database import settings
from src.core.logging import logger


def setup_tracing() -> None:
    """Enable LangSmith tracing when LANGSMITH_TRACING and a key are set; else force it off."""
    if not (settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY):
        os.environ["LANGSMITH_TRACING"] = "false"
        return
    values = {
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_API_KEY": settings.LANGSMITH_API_KEY,
        "LANGSMITH_PROJECT": settings.LANGSMITH_PROJECT,
        "LANGSMITH_ENDPOINT": settings.LANGSMITH_ENDPOINT,
        "LANGSMITH_WORKSPACE_ID": settings.LANGSMITH_WORKSPACE_ID,
    }
    for key, value in values.items():
        if value:
            os.environ.setdefault(key, value)
    logger.info(f"LangSmith tracing enabled (project={os.environ['LANGSMITH_PROJECT']})")
