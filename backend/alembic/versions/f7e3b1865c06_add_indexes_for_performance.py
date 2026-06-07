"""Add indexes for performance

Revision ID: f7e3b1865c06
Revises: f7e3b1865c05
Create Date: 2025-12-21 22:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f7e3b1865c06'
down_revision: Union[str, None] = 'f7e3b1865c05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Helper to check if an index exists
    bind = op.get_bind()
    insp = sa.inspect(bind)
    
    def index_exists(table, index):
        indexes = insp.get_indexes(table)
        return any(i["name"] == index for i in indexes)

    # Add indexes for frequently queried columns on foundations table
    if not index_exists('foundations', 'ix_foundations_category'):
        op.create_index('ix_foundations_category', 'foundations', ['category'])
    if not index_exists('foundations', 'ix_foundations_name'):
        op.create_index('ix_foundations_name', 'foundations', ['name'])
    if not index_exists('foundations', 'ix_foundations_county_code'):
        op.create_index('ix_foundations_county_code', 'foundations', ['county_code'])
    if not index_exists('foundations', 'ix_foundations_municipality_code'):
        op.create_index('ix_foundations_municipality_code', 'foundations', ['municipality_code'])
    
    # Add indexes for profiles table
    if not index_exists('profiles', 'ix_profiles_county_code'):
        op.create_index('ix_profiles_county_code', 'profiles', ['county_code'])
    if not index_exists('profiles', 'ix_profiles_municipality_code'):
        op.create_index('ix_profiles_municipality_code', 'profiles', ['municipality_code'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_foundations_category', 'foundations')
    op.drop_index('ix_foundations_name', 'foundations')
    op.drop_index('ix_foundations_county_code', 'foundations')
    op.drop_index('ix_foundations_municipality_code', 'foundations')
    op.drop_index('ix_profiles_county_code', 'profiles')
    op.drop_index('ix_profiles_municipality_code', 'profiles')
