"""add_docx_to_document_type

Revision ID: 1ebc03d5a124
Revises: 58ecd0f5d8d3
Create Date: 2026-08-26 11:01:50.135764

"""

from collections.abc import Sequence

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "1ebc03d5a124"
down_revision: str | Sequence[str] | None = "58ecd0f5d8d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Extend DocumentType to include DOCX.

    SQLite stores the enum as plain VARCHAR with no CHECK constraint, so no
    DDL change is required.  This revision records the schema-version bump so
    Alembic's version table stays current.
    """


def downgrade() -> None:
    """No DDL to reverse — see upgrade() for rationale."""
