"""Add source_url column to enrichment_data for per-source extraction tracking

Revision ID: 20261030_source_url
Revises: 20261029_enrichment_prompts
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20261030_source_url'
down_revision: Union[str, None] = '20261029_enrichment_prompts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def column_exists(table, column):
        return any(c["name"] == column for c in insp.get_columns(table))

    if not column_exists('enrichment_data', 'source_url'):
        op.add_column(
            'enrichment_data',
            sa.Column('source_url', sa.String(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column('enrichment_data', 'source_url')
