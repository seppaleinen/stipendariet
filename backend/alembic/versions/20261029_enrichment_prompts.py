"""Create enrichment_prompts table

Revision ID: 20261029_enrichment_prompts
Revises: 2026_09_02_000001
Create Date: 2026-10-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20261029_enrichment_prompts'
down_revision: Union[str, None] = '2026_09_02_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def table_exists(table):
        return table in insp.get_table_names()

    if not table_exists('enrichment_prompts'):
        op.create_table(
            'enrichment_prompts',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('name', sa.String(), nullable=False, unique=True, index=True),
            sa.Column('version', sa.String(), nullable=False),
            sa.Column('template', sa.Text(), nullable=False),
            sa.Column('variables', sa.JSON(), nullable=True),
            sa.Column('is_production', sa.Boolean(), default=False, nullable=False),
            sa.Column('metrics', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('created_by', sa.String(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table('enrichment_prompts')