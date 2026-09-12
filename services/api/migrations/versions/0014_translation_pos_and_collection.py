from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ANY_POS = "*"


def upgrade() -> None:
    op.execute(
        f"UPDATE translation_dictionary_entries SET pos = '{ANY_POS}' WHERE pos IS NULL"
    )
    op.alter_column(
        "translation_dictionary_entries",
        "pos",
        existing_type=sa.String(10),
        nullable=False,
        server_default=ANY_POS,
    )

    op.add_column(
        "translation_runs",
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE translation_runs
        SET collection_id = documents.collection_id
        FROM documents
        WHERE translation_runs.document_id = documents.id
        """
    )
    op.create_index(
        "ix_translation_runs_collection_id", "translation_runs", ["collection_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_translation_runs_collection_id", table_name="translation_runs")
    op.drop_column("translation_runs", "collection_id")
    op.alter_column(
        "translation_dictionary_entries",
        "pos",
        existing_type=sa.String(10),
        nullable=True,
        server_default=None,
    )
