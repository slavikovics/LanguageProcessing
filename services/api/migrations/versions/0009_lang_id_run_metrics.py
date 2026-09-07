"""LR2: persist aggregate accuracy/precision/recall/F1 per lang-id run.

Adds `lang_id_run_metrics`, mirroring `metric_results` for search — one
(run_id, metric_name, value) row per macro-averaged classification metric,
replaced each time a run's summary is (re)computed.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lang_id_run_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id", sa.Integer(), sa.ForeignKey("lang_id_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("metric_name", sa.String(50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lang_id_run_metrics")
