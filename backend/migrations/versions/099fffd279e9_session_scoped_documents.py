"""session_scoped_documents

Revision ID: 099fffd279e9
Revises: 15150a31fc09
Create Date: 2026-08-27 13:07:19.257260

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "099fffd279e9"
down_revision: str | Sequence[str] | None = "15150a31fc09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_constraint("uq_documents_content_hash", type_="unique")
        batch_op.add_column(sa.Column("session_id", sa.Uuid(), nullable=False))
        # Depending on how the old unique constraint was named, we drop it.
        # But wait, it's a destructive reset, we don't have to worry about old data.
        # But batch_alter_table takes care of this by redefining the table.
        batch_op.create_unique_constraint(
            "uq_document_content_hash_session_id", ["content_hash", "session_id"]
        )
        batch_op.create_foreign_key(
            "fk_documents_session_id",
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_constraint("fk_documents_session_id", type_="foreignkey")
        batch_op.drop_constraint("uq_document_content_hash_session_id", type_="unique")
        batch_op.drop_column("session_id")
