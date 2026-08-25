"""Add self_description to profiles

Revision ID: d8c41e7a2b19
Revises: a3d92f4c81e7
Create Date: 2026-08-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd8c41e7a2b19'
down_revision: Union[str, None] = 'a3d92f4c81e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def column_exists(table, column):
        return any(c["name"] == column for c in insp.get_columns(table))

    if not column_exists('profiles', 'self_description'):
        op.add_column('profiles', sa.Column('self_description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('profiles', 'self_description')
