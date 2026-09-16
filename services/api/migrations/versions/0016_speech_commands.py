from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

speech_commands_table = sa.table(
    "speech_commands",
    sa.column("phrase", sa.String),
    sa.column("action", sa.String),
    sa.column("language", sa.String),
    sa.column("is_active", sa.Boolean),
)

_SEED_COMMANDS = [
    ("search for", "navigate_search"),
    ("clear search", "clear_query"),
    ("read this", "read_document"),
    ("stop reading", "stop_speaking"),
]


def upgrade() -> None:
    op.create_table(
        "speech_commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phrase", sa.String(200), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.bulk_insert(
        speech_commands_table,
        [
            {"phrase": phrase, "action": action, "language": "en", "is_active": True}
            for phrase, action in _SEED_COMMANDS
        ],
    )


def downgrade() -> None:
    op.drop_table("speech_commands")
