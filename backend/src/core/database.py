import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pydantic_settings import BaseSettings

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/lifeos"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    ALLOWED_USER_EMAIL: str = "vinhho2508@gmail.com"
    OPENAI_API_KEY: str = ""
    SLACK_BOT_TOKEN: str = ""
    SLACK_DM_USER_ID: str = ""
    SLACK_SIGNING_SECRET: str = ""
    S3_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 1 day

    @property
    def async_database_url(self) -> str:
        # Ensures the URL starts with postgresql+asyncpg://
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()

from src.core.logging import logger
masked_url = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
logger.info(f"Connecting to database at: ...@{masked_url}")

engine = create_async_engine(settings.async_database_url)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session_factory() as session:
        yield session
