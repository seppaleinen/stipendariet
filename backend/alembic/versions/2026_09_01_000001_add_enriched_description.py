"""Add enriched_description to foundations

Revision ID: 2026_09_01_000001
Revises: 49d90bcc1dd5
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2026_09_01_000001"
# Parent must be the current chain HEAD. Previously f7e3b1865c08 (which is on
# the OTHER branch — 93d610535c3d's other parent is d8c41e7a2b19, not us).
# That created two heads alongside 49d90bcc1dd5. Pointing to 49d90bcc1dd5 makes
# this the single new head and lets `alembic upgrade head` apply cleanly.
down_revision: Union[str, None] = "49d90bcc1dd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard against re-run on a database where create_tables() already added it
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not any(c["name"] == "enriched_description" for c in insp.get_columns("foundations")):
        op.add_column(
            "foundations",
            sa.Column("enriched_description", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("foundations", "enriched_description")
