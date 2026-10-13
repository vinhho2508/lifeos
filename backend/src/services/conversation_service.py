import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.all_models import DEFAULT_CONVERSATION_TITLE, Conversation, utcnow

TITLE_MAX_CHARS = 60


class ConversationNotFound(LookupError):
    pass


def title_from_text(text: str) -> str:
    title = " ".join(text.split())
    return title if len(title) <= TITLE_MAX_CHARS else title[: TITLE_MAX_CHARS - 1] + "…"


async def get_conversation(
    db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID
) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise ConversationNotFound(str(conversation_id))
    return conversation


async def latest_conversation(db: AsyncSession, user_id: uuid.UUID) -> Conversation | None:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_conversation(db: AsyncSession, user_id: uuid.UUID) -> Conversation:
    conversation = Conversation(user_id=user_id, title=DEFAULT_CONVERSATION_TITLE)
    db.add(conversation)
    await db.flush()
    return conversation


async def resolve_conversation(
    db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID | None
) -> Conversation:
    """The requested conversation, else the user's latest one, else a new one."""
    if conversation_id is not None:
        return await get_conversation(db, user_id, conversation_id)
    return await latest_conversation(db, user_id) or await create_conversation(db, user_id)


def touch(conversation: Conversation, first_user_text: str | None = None) -> None:
    conversation.updated_at = utcnow()
    if first_user_text and conversation.title == DEFAULT_CONVERSATION_TITLE:
        conversation.title = title_from_text(first_user_text)
