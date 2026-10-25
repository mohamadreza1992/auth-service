"""add password and account lifecycle timestamps

Revision ID: 156f8193e82b
Revises: 7f33f3316e99
Create Date: 2026-10-25 13:18:19.653770
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "156f8193e82b"
down_revision: str | Sequence[str] | None = "7f33f3316e99"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add password and account lifecycle timestamps to users."""
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove password and account lifecycle timestamps from users."""
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "password_changed_at")
