import enum
import uuid
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


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

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.TODO)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="tasks")

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[DocStatusEnum] = mapped_column(
        Enum(DocStatusEnum), default=DocStatusEnum.UPLOADED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1536)) # OpenAI size

    document: Mapped["Document"] = relationship(back_populates="chunks")

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    sender: Mapped[SenderEnum] = mapped_column(Enum(SenderEnum))
    platform: Mapped[PlatformEnum] = mapped_column(Enum(PlatformEnum))
    text: Mapped[str] = mapped_column(Text)
    content: Mapped[list[dict]] = mapped_column(JSON, default=list)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="messages")
