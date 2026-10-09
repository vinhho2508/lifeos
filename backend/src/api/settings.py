from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.all_models import User
from src.providers.models import AVAILABLE_PROVIDERS
from src.services.settings_service import (
    get_user_settings,
    is_valid_timezone,
    update_user_settings,
)

router = APIRouter()


class UpdateSettingsRequest(BaseModel):
    chat_provider: str | None = None
    chat_model: str | None = None
    timezone: str | None = None


@router.get("/")
async def get_settings(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401)

    settings = await get_user_settings(db, user.id)
    return {
        "settings": {
            "chat_provider": settings.chat_provider,
            "chat_model": settings.chat_model,
            "timezone": settings.timezone,
        },
        "available_providers": AVAILABLE_PROVIDERS,
    }


@router.put("/")
async def update_settings(req: UpdateSettingsRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401)

    update_data = {}
    if req.chat_provider is not None:
        if req.chat_provider not in AVAILABLE_PROVIDERS:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown provider: {req.chat_provider}",
            )
        update_data["chat_provider"] = req.chat_provider

    if req.chat_model is not None:
        provider_name = req.chat_provider
        if not provider_name:
            current = await get_user_settings(db, user.id)
            provider_name = current.chat_provider
        available = AVAILABLE_PROVIDERS.get(provider_name, {}).get("models", [])
        if req.chat_model not in available:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown model '{req.chat_model}' for provider '{provider_name}'",
            )
        update_data["chat_model"] = req.chat_model
        if req.chat_provider is None:
            update_data["chat_provider"] = provider_name

    if req.timezone is not None:
        if not is_valid_timezone(req.timezone):
            raise HTTPException(status_code=422, detail=f"Unknown timezone: {req.timezone}")
        update_data["timezone"] = req.timezone

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    settings = await update_user_settings(db, user.id, update_data)
    return {
        "settings": {
            "chat_provider": settings.chat_provider,
            "chat_model": settings.chat_model,
            "timezone": settings.timezone,
        },
        "available_providers": AVAILABLE_PROVIDERS,
    }
