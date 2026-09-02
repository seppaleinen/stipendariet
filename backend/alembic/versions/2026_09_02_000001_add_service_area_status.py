"""Add service_area_status to foundations

Revision ID: 2026_09_02_000001
Revises: 2026_09_01_000001
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2026_09_02_000001'
down_revision: Union[str, None] = '2026_09_01_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def column_exists(table, column):
        columns = insp.get_columns(table)
        return any(c["name"] == column for c in columns)

    if not column_exists('foundations', 'service_area_status'):
        op.add_column(
            'foundations',
            sa.Column('service_area_status', sa.String(), nullable=True)
        )


def downgrade() -> None:
    op.drop_column('foundations', 'service_area_status')
