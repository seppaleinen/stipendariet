"""Add enriched_description to foundations

Revision ID: 2026_09_01_000001
Revises: f7e3b1865c08
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2026_09_01_000001"
down_revision: Union[str, None] = "f7e3b1865c08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "foundations",
        sa.Column("enriched_description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("foundations", "enriched_description")
