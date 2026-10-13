"""rag hardening: document metadata, chunk metadata, hybrid-search indexes

Chunks stored with the old mock embedding ([0.1] * 1536) are deleted; documents left
without chunks are marked ERROR so the user re-uploads them.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MOCK_VECTOR = "[" + ",".join(["0.1"] * 1536) + "]"


def upgrade() -> None:
    """Upgrade schema."""
    docsource = sa.Enum("FILE", "URL", name="docsourceenum")
    docsource.create(op.get_bind())
    op.add_column(
        "documents",
        sa.Column("source_type", docsource, nullable=False, server_default="FILE"),
    )
    op.add_column("documents", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("mime_type", sa.String(length=100), nullable=True))
    op.add_column("documents", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("documents", sa.Column("storage_key", sa.String(length=512), nullable=True))
    op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("embedding_model", sa.String(length=100), nullable=True))
    op.add_column(
        "documents", sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "documents",
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.add_column(
        "document_chunks", sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("document_chunks", sa.Column("page", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("heading_path", sa.Text(), nullable=True))
    op.add_column(
        "document_chunks",
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "content_tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', content)", persisted=True),
            nullable=True,
        ),
    )

    # Purge mock-embedded chunks, then flag the documents they emptied.
    op.get_bind().execute(
        sa.text("DELETE FROM document_chunks WHERE embedding = CAST(:mock AS vector)"),
        {"mock": _MOCK_VECTOR},
    )
    op.execute(
        """
        UPDATE documents SET status = 'ERROR',
               error_message = 'Indexed without embeddings; please re-upload.'
        WHERE NOT EXISTS (SELECT 1 FROM document_chunks c WHERE c.document_id = documents.id)
        """
    )
    op.execute(
        """
        UPDATE document_chunks SET ordinal = n.rn
        FROM (SELECT id, row_number() OVER (PARTITION BY document_id ORDER BY id) - 1 AS rn
              FROM document_chunks) n
        WHERE n.id = document_chunks.id
        """
    )
    op.execute(
        """
        UPDATE documents SET chunk_count = c.n, embedding_model = 'text-embedding-3-small'
        FROM (SELECT document_id, count(*) AS n FROM document_chunks GROUP BY document_id) c
        WHERE c.document_id = documents.id
        """
    )

    op.drop_constraint("document_chunks_document_id_fkey", "document_chunks", type_="foreignkey")
    op.create_foreign_key(
        "document_chunks_document_id_fkey",
        "document_chunks",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_document_chunks_document_ordinal", "document_chunks", ["document_id", "ordinal"]
    )
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_document_chunks_content_tsv",
        "document_chunks",
        ["content_tsv"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_document_chunks_content_tsv", table_name="document_chunks")
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_ordinal", table_name="document_chunks")
    op.drop_constraint("document_chunks_document_id_fkey", "document_chunks", type_="foreignkey")
    op.create_foreign_key(
        "document_chunks_document_id_fkey",
        "document_chunks",
        "documents",
        ["document_id"],
        ["id"],
    )
    for column in ("content_tsv", "token_count", "heading_path", "page", "ordinal"):
        op.drop_column("document_chunks", column)
    for column in (
        "status_changed_at",
        "chunk_count",
        "embedding_model",
        "error_message",
        "storage_key",
        "size_bytes",
        "mime_type",
        "source_url",
        "source_type",
    ):
        op.drop_column("documents", column)
    sa.Enum(name="docsourceenum").drop(op.get_bind())
