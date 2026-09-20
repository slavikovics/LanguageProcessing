from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

speech_commands_table = sa.table(
    "speech_commands",
    sa.column("phrase", sa.String),
    sa.column("action", sa.String),
    sa.column("language", sa.String),
    sa.column("is_active", sa.Boolean),
)

# Mirrors the English seeds of 0016/0018; phrases must stay distinct so the substring matcher can't confuse them.
_SEED_COMMANDS = [
    ("найди", "navigate_search"),
    ("очисти запрос", "clear_query"),
    ("прочитай это", "read_document"),
    ("хватит читать", "stop_speaking"),
    ("перейди к краулингу", "navigate_to_crawl"),
    ("перейди к коллекциям", "navigate_to_collections"),
    ("перейди к поиску", "navigate_to_search"),
    ("перейди к метрикам", "navigate_to_metrics"),
    ("перейди к определению языка", "navigate_to_lang_id"),
    ("перейди к реферированию", "navigate_to_summarization"),
    ("перейди к переводу", "navigate_to_translation"),
    ("перейди к настройкам", "navigate_to_settings"),
    ("перейди к справке", "navigate_to_help"),
]


def upgrade() -> None:
    op.bulk_insert(
        speech_commands_table,
        [
            {"phrase": phrase, "action": action, "language": "ru", "is_active": True}
            for phrase, action in _SEED_COMMANDS
        ],
    )


def downgrade() -> None:
    table = speech_commands_table
    conn = op.get_bind()
    conn.execute(
        table.delete().where(
            sa.and_(
                table.c.language == "ru",
                table.c.phrase.in_([phrase for phrase, _action in _SEED_COMMANDS]),
            )
        )
    )
