"""Add enrichment fields to foundations

Revision ID: f7e3b1865c07
Revises: f7e3b1865c06
Create Date: 2025-12-23 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f7e3b1865c07'
down_revision: Union[str, None] = 'f7e3b1865c06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Helper to check if a column exists
    bind = op.get_bind()
    insp = sa.inspect(bind)
    
    def column_exists(table, column):
        columns = insp.get_columns(table)
        return any(c["name"] == column for c in columns)

    def index_exists(table, index):
        indexes = insp.get_indexes(table)
        return any(i["name"] == index for i in indexes)

    # Enrichment job control columns
    if not column_exists('foundations', 'enrichment_status'):
        op.add_column('foundations', sa.Column('enrichment_status', sa.String(), server_default='UNPROCESSED'))
    if not column_exists('foundations', 'enrichment_last_run'):
        op.add_column('foundations', sa.Column('enrichment_last_run', sa.DateTime(), nullable=True))
    if not column_exists('foundations', 'enrichment_error'):
        op.add_column('foundations', sa.Column('enrichment_error', sa.Text(), nullable=True))
    
    # Enriched data columns (extracted by LLM from scraped website)
    if not column_exists('foundations', 'website_url'):
        op.add_column('foundations', sa.Column('website_url', sa.String(), nullable=True))
    if not column_exists('foundations', 'application_deadline'):
        op.add_column('foundations', sa.Column('application_deadline', sa.String(), nullable=True))
    if not column_exists('foundations', 'application_start'):
        op.add_column('foundations', sa.Column('application_start', sa.String(), nullable=True))
    if not column_exists('foundations', 'application_method'):
        op.add_column('foundations', sa.Column('application_method', sa.String(), nullable=True))
    
    # Add index for enrichment status to speed up queue queries
    if not index_exists('foundations', 'ix_foundations_enrichment_status'):
        op.create_index('ix_foundations_enrichment_status', 'foundations', ['enrichment_status'])


def downgrade() -> None:
    op.drop_index('ix_foundations_enrichment_status', 'foundations')
    op.drop_column('foundations', 'application_method')
    op.drop_column('foundations', 'application_start')
    op.drop_column('foundations', 'application_deadline')
    op.drop_column('foundations', 'website_url')
    op.drop_column('foundations', 'enrichment_error')
    op.drop_column('foundations', 'enrichment_last_run')
    op.drop_column('foundations', 'enrichment_status')
