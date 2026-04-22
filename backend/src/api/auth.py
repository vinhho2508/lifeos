from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db, settings
from src.core.auth import create_access_token, is_authorized_user
from src.models.all_models import User

router = APIRouter()

class TokenRequest(BaseModel):
    token: str

@router.post("/login")
async def login(req: TokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        from src.core.logging import logger
        logger.info(f"Attempting to verify token for Client ID: {settings.GOOGLE_CLIENT_ID}")
        
        # Verify Google Token
        idinfo = id_token.verify_oauth2_token(req.token, requests.Request(), settings.GOOGLE_CLIENT_ID)
        
        email = idinfo['email']
        
        if not is_authorized_user(email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not authorized"
            )
        
        # Check if user exists, or create
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(email=email)
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
