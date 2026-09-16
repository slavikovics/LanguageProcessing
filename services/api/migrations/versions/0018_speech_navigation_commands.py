from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

speech_commands_table = sa.table(
    "speech_commands",
    sa.column("phrase", sa.String),
    sa.column("action", sa.String),
    sa.column("language", sa.String),
    sa.column("is_active", sa.Boolean),
)

# One phrase per Layout.tsx nav tab, mirrored client-side by
# commandDispatch.ts's NAVIGATE_TARGETS. Phrases are distinct enough after
# "go to " that none is a substring of another, so matchCommand's plain
# substring rule can't confuse them.
_SEED_COMMANDS = [
    ("go to crawling", "navigate_to_crawl"),
    ("go to collections", "navigate_to_collections"),
    ("go to search", "navigate_to_search"),
    ("go to metrics", "navigate_to_metrics"),
    ("go to language identification", "navigate_to_lang_id"),
    ("go to summarization", "navigate_to_summarization"),
    ("go to translation", "navigate_to_translation"),
    ("go to settings", "navigate_to_settings"),
    ("go to help", "navigate_to_help"),
]


def upgrade() -> None:
    op.bulk_insert(
        speech_commands_table,
        [
            {"phrase": phrase, "action": action, "language": "en", "is_active": True}
            for phrase, action in _SEED_COMMANDS
        ],
    )


def downgrade() -> None:
    table = speech_commands_table
    conn = op.get_bind()
    conn.execute(
        table.delete().where(
            table.c.action.in_([action for _phrase, action in _SEED_COMMANDS])
        )
    )
