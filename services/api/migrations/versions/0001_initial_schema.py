from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("clean_text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("published_date", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("collection_id", "url", name="uq_document_collection_url"),
    )
    op.create_index("ix_documents_collection_id", "documents", ["collection_id"])

    op.create_table(
        "terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lemma", sa.String(200), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.UniqueConstraint("lemma", "language", name="uq_term_lemma_language"),
    )

    op.create_table(
        "document_terms",
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "term_id", sa.Integer(), sa.ForeignKey("terms.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("tf", sa.Integer(), nullable=False),
    )

    op.create_table(
        "term_weights",
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "term_id", sa.Integer(), sa.ForeignKey("terms.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("weight", sa.Float(), nullable=False),
    )

    op.create_table(
        "queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "search_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "query_id", sa.Integer(), sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("executed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "search_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "search_run_id",
            sa.Integer(),
            sa.ForeignKey("search_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
    )

    op.create_table(
        "relevance_judgments",
        sa.Column(
            "query_id", sa.Integer(), sa.ForeignKey("queries.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("is_relevant", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "metric_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "search_run_id",
            sa.Integer(),
            sa.ForeignKey("search_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_name", sa.String(50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
    )

    op.create_table(
        "crawl_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seed_urls", sa.JSON(), nullable=False),
        sa.Column("max_documents", sa.Integer(), nullable=False),
        sa.Column("max_depth", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("documents_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("urls_queued", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("urls_visited", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("urls_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "crawl_urls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id", sa.Integer(), sa.ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "discovered_from_id",
            sa.Integer(),
            sa.ForeignKey("crawl_urls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("job_id", "url", name="uq_crawl_url_job_url"),
    )
    op.create_index("ix_crawl_urls_job_id_status", "crawl_urls", ["job_id", "status"])


def downgrade() -> None:
    op.drop_table("crawl_urls")
    op.drop_table("crawl_jobs")
    op.drop_table("metric_results")
    op.drop_table("relevance_judgments")
    op.drop_table("search_results")
    op.drop_table("search_runs")
    op.drop_table("queries")
    op.drop_table("term_weights")
    op.drop_table("document_terms")
    op.drop_table("terms")
    op.drop_table("documents")
    op.drop_table("collections")
