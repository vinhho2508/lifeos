import enum
import uuid
from datetime import UTC, datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class StatusEnum(enum.Enum):
    TODO = "TODO"
    WORKING = "WORKING"
    DONE = "DONE"


class DocStatusEnum(enum.Enum):
    UPLOADED = "UPLOADED"
    DIGESTING = "DIGESTING"
    READY = "READY"
    ERROR = "ERROR"


class SenderEnum(enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class PlatformEnum(enum.Enum):
    WEB = "WEB"
    SLACK = "SLACK"
    CHROME_EXTENSION = "CHROME_EXTENSION"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tasks: Mapped[List["Task"]] = relationship(back_populates="user")
    documents: Mapped[List["Document"]] = relationship(back_populates="user")
    messages: Mapped[List["Message"]] = relationship(back_populates="user")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="user")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.TODO)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="tasks")


class DocSourceEnum(enum.Enum):
    FILE = "FILE"
    URL = "URL"


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[DocStatusEnum] = mapped_column(
        Enum(DocStatusEnum), default=DocStatusEnum.UPLOADED
    )
    source_type: Mapped[DocSourceEnum] = mapped_column(
        Enum(DocSourceEnum), default=DocSourceEnum.FILE, server_default="FILE"
    )
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    # Key of the original in the file store; None for legacy docs, which cannot be re-indexed.
    storage_key: Mapped[Optional[str]] = mapped_column(String(512))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_document_ordinal", "document_id", "ordinal"),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_document_chunks_content_tsv", "content_tsv", postgresql_using="gin"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    ordinal: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    content: Mapped[str] = mapped_column(Text)
    page: Mapped[Optional[int]] = mapped_column(Integer)
    heading_path: Mapped[Optional[str]] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1536))  # OpenAI size
    content_tsv: Mapped[Optional[str]] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', content)", persisted=True)
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")


DEFAULT_CONVERSATION_TITLE = "New chat"


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default=DEFAULT_CONVERSATION_TITLE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", passive_deletes=True
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_timestamp", "conversation_id", "timestamp"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    sender: Mapped[SenderEnum] = mapped_column(Enum(SenderEnum))
    platform: Mapped[PlatformEnum] = mapped_column(Enum(PlatformEnum))
    text: Mapped[str] = mapped_column(Text)
    content: Mapped[list[dict]] = mapped_column(JSON, default=list)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="messages")
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class UserSettings(Base):
    __tablename__ = "user_settings"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    chat_provider: Mapped[str] = mapped_column(String(50), default="openai")
    chat_model: Mapped[str] = mapped_column(String(100), default="gpt-5.4-nano")
    # IANA zone name; relative dates in chat ("Friday 9am") resolve in this zone.
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
