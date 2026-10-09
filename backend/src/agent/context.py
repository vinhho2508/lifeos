import uuid
from dataclasses import dataclass

from src.models.all_models import PlatformEnum


@dataclass(frozen=True)
class AgentContext:
    """Server-side facts injected into every tool call and the system prompt.

    Never exposed to the model as tool parameters, so the model cannot act as
    another user or pick its own timezone.
    """

    user_id: uuid.UUID
    timezone: str
    platform: PlatformEnum
    run_id: uuid.UUID
