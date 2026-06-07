"""Add new profile fields to profiles table

Revision ID: f7e3b1865c02
Revises: f7e3b1865c01
Create Date: 2025-12-13 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7e3b1865c02'
down_revision: Union[str, None] = 'f7e3b1865c01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to profiles table if they don't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('profiles')]
    
    if 'name' not in columns:
        op.add_column('profiles', sa.Column('name', sa.String(), nullable=True))
    if 'education' not in columns:
        op.add_column('profiles', sa.Column('education', sa.Text(), nullable=True))
    if 'field_of_study' not in columns:
        op.add_column('profiles', sa.Column('field_of_study', sa.String(), nullable=True))
    if 'current_work' not in columns:
        op.add_column('profiles', sa.Column('current_work', sa.Text(), nullable=True))
    if 'professional_experience' not in columns:
        op.add_column('profiles', sa.Column('professional_experience', sa.Text(), nullable=True))
    if 'area_of_interest' not in columns:
        op.add_column('profiles', sa.Column('area_of_interest', sa.String(), nullable=True))
    if 'needs' not in columns:
        op.add_column('profiles', sa.Column('needs', sa.Text(), nullable=True))
    if 'challenges' not in columns:
        op.add_column('profiles', sa.Column('challenges', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove new columns from profiles table if they exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('profiles')]
    
    if 'challenges' in columns:
        op.drop_column('profiles', 'challenges')
    if 'needs' in columns:
        op.drop_column('profiles', 'needs')
    if 'area_of_interest' in columns:
        op.drop_column('profiles', 'area_of_interest')
    if 'professional_experience' in columns:
        op.drop_column('profiles', 'professional_experience')
    if 'current_work' in columns:
        op.drop_column('profiles', 'current_work')
    if 'field_of_study' in columns:
        op.drop_column('profiles', 'field_of_study')
    if 'education' in columns:
        op.drop_column('profiles', 'education')
    if 'name' in columns:
        op.drop_column('profiles', 'name')