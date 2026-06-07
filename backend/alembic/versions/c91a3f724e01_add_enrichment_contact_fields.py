"""Add enrichment contact and applicant fields to foundations

Revision ID: c91a3f724e01
Revises: b64ec2432846
Create Date: 2026-04-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c91a3f724e01'
down_revision: Union[str, None] = 'b64ec2432846'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def column_exists(table, column):
        return any(c["name"] == column for c in insp.get_columns(table))

    if not column_exists('foundations', 'contact_email'):
        op.add_column('foundations', sa.Column('contact_email', sa.String(), nullable=True))
    if not column_exists('foundations', 'contact_phone'):
        op.add_column('foundations', sa.Column('contact_phone', sa.String(), nullable=True))
    if not column_exists('foundations', 'who_can_apply'):
        op.add_column('foundations', sa.Column('who_can_apply', sa.Text(), nullable=True))
    if not column_exists('foundations', 'enrichment_notes'):
        op.add_column('foundations', sa.Column('enrichment_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('foundations', 'enrichment_notes')
    op.drop_column('foundations', 'who_can_apply')
    op.drop_column('foundations', 'contact_phone')
    op.drop_column('foundations', 'contact_email')
