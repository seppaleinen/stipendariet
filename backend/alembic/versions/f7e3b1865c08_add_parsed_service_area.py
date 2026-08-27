"""Add parsed_service_area to foundations

Revision ID: f7e3b1865c08
Revises: f7e3b1865c07
Create Date: 2026-08-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f7e3b1865c08'
down_revision: Union[str, None] = 'f7e3b1865c07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def column_exists(table, column):
        columns = insp.get_columns(table)
        return any(c["name"] == column for c in columns)

    if not column_exists('foundations', 'parsed_service_area'):
        op.add_column(
            'foundations',
            sa.Column('parsed_service_area', sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    op.drop_column('foundations', 'parsed_service_area')
