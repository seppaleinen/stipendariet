"""Restore performance indexes dropped by multi-profile migration

Revision ID: a3d92f4c81e7
Revises: c91a3f724e01
Create Date: 2026-08-24 00:00:00.000000

Migration b64ec2432846 (multi-profile support) dropped the performance
indexes on the foundations and profiles tables in its upgrade path but
only recreated them in downgrade(). This migration restores all 7
indexes (the 6 from issue #8 plus ix_foundations_enrichment_status,
which was originally added by f7e3b1865c07 to speed up enrichment
queue queries).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3d92f4c81e7'
down_revision: Union[str, Sequence[str], None] = 'c91a3f724e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEXES = [
    ('foundations', 'ix_foundations_category', ['category']),
    ('foundations', 'ix_foundations_name', ['name']),
    ('foundations', 'ix_foundations_county_code', ['county_code']),
    ('foundations', 'ix_foundations_municipality_code', ['municipality_code']),
    ('foundations', 'ix_foundations_enrichment_status', ['enrichment_status']),
    ('profiles', 'ix_profiles_county_code', ['county_code']),
    ('profiles', 'ix_profiles_municipality_code', ['municipality_code']),
]


def index_exists(table: str, index: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(i["name"] == index for i in insp.get_indexes(table))


def upgrade() -> None:
    for table, name, columns in INDEXES:
        if not index_exists(table, name):
            op.create_index(name, table, columns)


def downgrade() -> None:
    for table, name, _columns in reversed(INDEXES):
        if index_exists(table, name):
            op.drop_index(name, table_name=table)
