import hmac
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db, settings
from src.models.all_models import User


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set; refusing to issue an unverifiable token")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def is_authorized_user(email: str) -> bool:
    return email == settings.ALLOWED_USER_EMAIL


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _email_from_jwt(token: str) -> str:
    # An empty SECRET_KEY would let anyone mint tokens, so refuse JWT auth entirely.
    if not settings.SECRET_KEY:
        raise _unauthorized("JWT auth is not configured")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise _unauthorized("Invalid token")
    email = payload.get("sub")
    if not email:
        raise _unauthorized("Invalid token")
    return email


def _is_valid_service_token(token: str) -> bool:
    expected = settings.SLACK_SERVICE_TOKEN
    return bool(expected) and hmac.compare_digest(token.encode(), expected.encode())


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_service_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate with a bearer JWT (web, extension) or X-Service-Token (Slack bot)."""
    if x_service_token is not None:
        if not _is_valid_service_token(x_service_token):
            raise _unauthorized("Invalid service token")
        email = settings.ALLOWED_USER_EMAIL
    elif authorization and authorization.lower().startswith("bearer "):
        email = _email_from_jwt(authorization[7:].strip())
    else:
        raise _unauthorized()

    if not is_authorized_user(email):
        raise _unauthorized("User not authorized")

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise _unauthorized("Unknown user")
    return user
