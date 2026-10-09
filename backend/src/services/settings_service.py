import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.models.all_models import User, UserSettings
from src.providers.models import AVAILABLE_PROVIDERS


def is_valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


async def get_user_settings(db: AsyncSession, user_id: uuid.UUID | None = None) -> UserSettings:
    """Return the user's settings, creating defaults on first use.

    Without `user_id`, falls back to the first user (routers that are not yet authenticated).
    """
    if user_id is None:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("No user found")
        user_id = user.id

    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()

    if not settings:
        default_provider = "openai"
        default_model = AVAILABLE_PROVIDERS["openai"]["default_model"]
        settings = UserSettings(
            user_id=user_id,
            chat_provider=default_provider,
            chat_model=default_model,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        logger.info(f"Created default settings for user {user_id}")

    return settings


async def update_user_settings(db: AsyncSession, user_id: uuid.UUID, data: dict) -> UserSettings:
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)

    if "chat_provider" in data:
        provider = data["chat_provider"]
        if provider not in AVAILABLE_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        settings.chat_provider = provider

    if "chat_model" in data:
        provider_name = data.get("chat_provider", settings.chat_provider)
        available_models = AVAILABLE_PROVIDERS.get(provider_name, {}).get("models", [])
        if data["chat_model"] not in available_models:
            raise ValueError(f"Unknown model '{data['chat_model']}' for provider '{provider_name}'")
        settings.chat_model = data["chat_model"]

    if "timezone" in data:
        if not is_valid_timezone(data["timezone"]):
            raise ValueError(f"Unknown timezone: {data['timezone']}")
        settings.timezone = data["timezone"]

    await db.commit()
    await db.refresh(settings)
    logger.info(f"Updated settings for user {user_id}")
    return settings
