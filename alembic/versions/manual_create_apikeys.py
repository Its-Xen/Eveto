"""create apikeys table

Revision ID: c1d2e3f4g5h6
Revises: 6ad84cb6be31
Create Date: 2026-11-03

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, None] = "6ad84cb6be31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "apikeys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("partner_name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("rate_limit_tier", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_apikeys_key_hash", "apikeys", ["key_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_apikeys_key_hash", table_name="apikeys")
    op.drop_table("apikeys")
