from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MAX_EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.drop_table("document_embeddings")

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    op.create_table(
        "document_chunk_embeddings",
        sa.Column(
            "chunk_id",
            sa.Integer(),
            sa.ForeignKey("document_chunks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "search_model_id",
            sa.Integer(),
            sa.ForeignKey("search_models.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", Vector(MAX_EMBEDDING_DIM), nullable=False),
    )

    op.execute(
        """
        UPDATE search_models
        SET key = 'multilingual-e5-small',
            label = 'Multilingual E5 Small (эмбеддинги)',
            dimension = 384
        WHERE kind = 'dense_embedding'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE search_models
        SET key = 'gte-multilingual-base',
            label = 'Alibaba GTE Multilingual Base (эмбеддинги)',
            dimension = 768
        WHERE kind = 'dense_embedding'
        """
    )
    op.drop_table("document_chunk_embeddings")
    op.drop_table("document_chunks")
    op.create_table(
        "document_embeddings",
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "search_model_id",
            sa.Integer(),
            sa.ForeignKey("search_models.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", Vector(MAX_EMBEDDING_DIM), nullable=False),
    )
