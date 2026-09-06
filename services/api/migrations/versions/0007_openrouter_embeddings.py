"""Switch dense-embedding model to OpenRouter-hosted Qwen3-Embedding-8B.

Replaces the locally-run intfloat/multilingual-e5-small model with
Qwen3-Embedding-8B served through OpenRouter's hosted embeddings API (see
services/nlp-service/app/embeddings.py) — ranked #1 on the MTEB multilingual
leaderboard, a 32K-token context (vs. e5-small's 512), and no local CPU
inference or model download. Its native vector is 4096-dim (vs. e5-small's
384), so `document_chunk_embeddings.embedding` is widened to match the new
MAX_EMBEDDING_DIM (see ips_db.models) — a different, incompatible embedding
space from e5-small either way, so existing dense-embedding chunk vectors
are dropped; collections need reindexing under the new model. TF-IDF search
and its vectors are untouched.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_MAX_EMBEDDING_DIM = 1024
NEW_MAX_EMBEDDING_DIM = 4096


def upgrade() -> None:
    op.execute("TRUNCATE TABLE document_chunk_embeddings")
    op.drop_column("document_chunk_embeddings", "embedding")
    op.add_column(
        "document_chunk_embeddings",
        sa.Column("embedding", Vector(NEW_MAX_EMBEDDING_DIM), nullable=False),
    )
    op.execute(
        """
        UPDATE search_models
        SET key = 'qwen3-embedding-8b',
            label = 'Qwen3 Embedding 8B via OpenRouter (эмбеддинги)',
            dimension = 4096
        WHERE kind = 'dense_embedding'
        """
    )


def downgrade() -> None:
    op.execute("TRUNCATE TABLE document_chunk_embeddings")
    op.drop_column("document_chunk_embeddings", "embedding")
    op.add_column(
        "document_chunk_embeddings",
        sa.Column("embedding", Vector(OLD_MAX_EMBEDDING_DIM), nullable=False),
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
