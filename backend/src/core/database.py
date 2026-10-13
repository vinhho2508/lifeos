from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    PORT: int = 8000
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/lifeos"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    ALLOWED_USER_EMAIL: str = "vinhho2508@gmail.com"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    SLACK_BOT_TOKEN: str = ""
    SLACK_DM_USER_ID: str = ""
    SLACK_SIGNING_SECRET: str = ""
    # Shared secret the Slack bot sends as X-Service-Token; empty disables service auth.
    SLACK_SERVICE_TOKEN: str = ""
    S3_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"
    # Read from .env here because boto3 only sees the process environment; empty
    # falls back to boto3's default chain (env vars, ~/.aws, instance role).
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    # S3-compatible storage (Cloudflare R2, MinIO): the API endpoint, e.g.
    # https://<account_id>.r2.cloudflarestorage.com (use AWS_REGION=auto for R2).
    S3_ENDPOINT_URL: str = ""
    # Public base URL for generated image links (R2 custom domain or r2.dev URL);
    # empty means https://<bucket>.s3.<region>.amazonaws.com.
    S3_PUBLIC_URL: str = ""
    # RAG: originals go to S3 when S3_BUCKET_NAME is set, else to UPLOAD_DIR.
    UPLOAD_DIR: str = "data/uploads"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    RAG_MAX_UPLOAD_MB: int = 20
    RAG_MAX_CHUNKS: int = 2000
    RAG_DIGEST_CONCURRENCY: int = 2
    RAG_MIN_SIMILARITY: float = 0.25
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 1 day

    @property
    def async_database_url(self) -> str:
        # Ensures the URL starts with postgresql+asyncpg://
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

from src.core.logging import logger  # noqa: E402

_db_host = (
    settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
)
logger.info(f"Connecting to database at: ...@{_db_host}")

engine = create_async_engine(settings.async_database_url)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_factory() as session:
        yield session
