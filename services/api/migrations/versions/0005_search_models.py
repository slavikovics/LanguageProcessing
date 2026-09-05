"""Pluggable search models: registry table + dense-vector storage.

Adds `search_models` (a small registry of pluggable search algorithms —
schema never changes again when a new model is added, only a new seeded
row via a future migration), `document_embeddings` (pgvector storage for
dense models, fixed-width column shared by any number of models via
zero-padding — see ips_db.models.MAX_EMBEDDING_DIM), and a `model_id`
column on `search_runs` so existing/new runs are tagged with the model
that produced them. Existing rows are backfilled to the "tfidf" model.

No ANN index (ivfflat/hnsw) is created — collection sizes here are course-
project scale, so an exact brute-force `ORDER BY embedding <=> :qvec` is
adequate. Add one later if a collection ever grows large enough to need it.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MAX_EMBEDDING_DIM = 1024

search_models_table = sa.table(
    "search_models",
    sa.column("key", sa.String),
    sa.column("label", sa.String),
    sa.column("kind", sa.String),
    sa.column("dimension", sa.Integer),
    sa.column("is_active", sa.Boolean),
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "search_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.bulk_insert(
        search_models_table,
        [
            {
                "key": "tfidf",
                "label": "TF-IDF + косинусная мера",
                "kind": "tfidf",
                "dimension": None,
                "is_active": True,
            },
            {
                "key": "gte-multilingual-base",
                "label": "Alibaba GTE Multilingual Base (эмбеддинги)",
                "kind": "dense_embedding",
                "dimension": 768,
                "is_active": True,
            },
        ],
    )

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

    op.add_column(
        "search_runs",
        sa.Column(
            "model_id",
            sa.Integer(),
            sa.ForeignKey("search_models.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.execute("UPDATE search_runs SET model_id = (SELECT id FROM search_models WHERE key = 'tfidf')")
    op.alter_column("search_runs", "model_id", nullable=False)


def downgrade() -> None:
    op.drop_column("search_runs", "model_id")
    op.drop_table("document_embeddings")
    op.drop_table("search_models")
    # The `vector` extension is left installed — harmless to keep.
