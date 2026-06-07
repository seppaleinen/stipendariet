"""Add translated_purpose column to foundations table

Revision ID: f7e3b1865c01
Revises: 
Create Date: 2025-12-13 16:21:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7e3b1865c01'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the translated_purpose column to the foundations table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('foundations')]
    
    if 'translated_purpose' not in columns:
        op.add_column('foundations', sa.Column('translated_purpose', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove the translated_purpose column from the foundations table if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('foundations')]
    
    if 'translated_purpose' in columns:
        op.drop_column('foundations', 'translated_purpose')