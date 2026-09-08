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
