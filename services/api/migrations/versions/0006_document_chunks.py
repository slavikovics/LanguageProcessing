"""Chunked dense embeddings + faster multilingual embedding model.

Replaces the one-vector-per-document `document_embeddings` table with
`document_chunks` + `document_chunk_embeddings`: a document is split into
model-context-sized pieces (see api's app.domain.indexing.chunk_text) so a
long document's tail is represented across several chunk vectors instead of
being silently discarded by the encoder's truncation. Search then ranks a
document by its single best-matching chunk (ChunkEmbeddingRepository.
nearest_documents).

Also swaps the registered dense-embedding model from Alibaba GTE
Multilingual Base (768-dim, 8192-token context, very slow on CPU for long
documents) to intfloat/multilingual-e5-small (384-dim, 512-token context,
tens of times faster) — see services/nlp-service/app/embeddings.py. Old
768-dim vectors are a different, incompatible embedding space, so they're
dropped along with the table that held them; collections need reindexing
under the new model.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-06

"""
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
