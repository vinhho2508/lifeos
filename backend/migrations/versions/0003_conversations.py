"""conversations: group messages into per-user conversations

Existing messages are moved into one "Previous chat" conversation per user.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"])
    op.add_column("messages", sa.Column("conversation_id", sa.Uuid(), nullable=True))

    # Backfill: one conversation per user that already has messages.
    op.execute(
        """
        INSERT INTO conversations (id, user_id, title, created_at, updated_at)
        SELECT gen_random_uuid(), user_id, 'Previous chat',
               MIN(timestamp) AT TIME ZONE 'UTC', MAX(timestamp) AT TIME ZONE 'UTC'
        FROM messages GROUP BY user_id
        """
    )
    op.execute(
        """
        UPDATE messages SET conversation_id = c.id
        FROM conversations c WHERE c.user_id = messages.user_id
        """
    )

    op.alter_column("messages", "conversation_id", nullable=False)
    op.create_foreign_key(
        "fk_messages_conversation_id",
        "messages",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_messages_conversation_timestamp", "messages", ["conversation_id", "timestamp"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_messages_conversation_timestamp", table_name="messages")
    op.drop_constraint("fk_messages_conversation_id", "messages", type_="foreignkey")
    op.drop_column("messages", "conversation_id")
    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_table("conversations")
