"""Profile matching redesign

Revision ID: f7e3b1865c05
Revises: f7e3b1865c04
Create Date: 2025-12-21 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f7e3b1865c05'
down_revision: Union[str, None] = 'f7e3b1865c04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Helper to check if a column exists
    bind = op.get_bind()
    insp = sa.inspect(bind)
    
    def column_exists(table, column):
        columns = insp.get_columns(table)
        return any(c["name"] == column for c in columns)

    # Add new structured profile columns
    if not column_exists('profiles', 'county_code'):
        op.add_column('profiles', sa.Column('county_code', sa.String(), nullable=True))
    if not column_exists('profiles', 'municipality_code'):
        op.add_column('profiles', sa.Column('municipality_code', sa.String(), nullable=True))
    if not column_exists('profiles', 'life_situations'):
        op.add_column('profiles', sa.Column('life_situations', sa.JSON(), nullable=True))
    if not column_exists('profiles', 'health_conditions'):
        op.add_column('profiles', sa.Column('health_conditions', sa.JSON(), nullable=True))
    if not column_exists('profiles', 'health_details'):
        op.add_column('profiles', sa.Column('health_details', sa.Text(), nullable=True))
    if not column_exists('profiles', 'occupations'):
        op.add_column('profiles', sa.Column('occupations', sa.JSON(), nullable=True))
    if not column_exists('profiles', 'support_purposes'):
        op.add_column('profiles', sa.Column('support_purposes', sa.JSON(), nullable=True))
    if not column_exists('profiles', 'legacy_data'):
        op.add_column('profiles', sa.Column('legacy_data', sa.JSON(), nullable=True))
    
    # Migrate existing data to legacy_data column (only if legacy_data exists and has not been filled)
    if column_exists('profiles', 'legacy_data'):
        # Only migrate if we have some old columns to migrate from
        old_columns_to_migrate = [
            'name', 'contact_information', 'personal_description', 'education', 
            'field_of_study', 'current_work', 'professional_experience', 
            'area_of_interest', 'goals', 'achievements', 'needs', 
            'challenges', 'family_members', 'economic_situation', 
            'living_situation', 'additional_notes'
        ]
        available_columns = [col for col in old_columns_to_migrate if column_exists('profiles', col)]
        
        if available_columns:
            # Build the jsonb_build_object arguments dynamically
            # format: 'col1', col1, 'col2', col2...
            json_build_args = ", ".join([f"'{col}', {col}" for col in available_columns])
            
            # Use the first available column for the WHERE clause to check for non-nullness
            where_clause = " OR ".join([f"{col} IS NOT NULL" for col in available_columns])
            
            op.execute(f"""
                UPDATE profiles 
                SET legacy_data = jsonb_build_object({json_build_args})
                WHERE {where_clause}
            """)
    
    # Drop old columns
    old_columns = [
        'name', 'contact_information', 'personal_description', 'education', 
        'field_of_study', 'current_work', 'professional_experience', 
        'area_of_interest', 'goals', 'achievements', 'needs', 
        'challenges', 'family_members', 'economic_situation', 
        'living_situation', 'additional_notes'
    ]
    for col in old_columns:
        if column_exists('profiles', col):
            op.drop_column('profiles', col)


def downgrade() -> None:
    # Re-add old columns
    op.add_column('profiles', sa.Column('name', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('contact_information', sa.JSON(), nullable=True))
    op.add_column('profiles', sa.Column('personal_description', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('education', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('field_of_study', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('current_work', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('professional_experience', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('area_of_interest', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('goals', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('achievements', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('needs', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('challenges', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('family_members', sa.JSON(), nullable=True))
    op.add_column('profiles', sa.Column('economic_situation', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('living_situation', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('additional_notes', sa.Text(), nullable=True))
    
    # Restore data from legacy_data
    op.execute("""
        UPDATE profiles 
        SET 
            name = legacy_data->>'name',
            contact_information = (legacy_data->'contact_information')::jsonb,
            personal_description = legacy_data->>'personal_description',
            education = legacy_data->>'education',
            field_of_study = legacy_data->>'field_of_study',
            current_work = legacy_data->>'current_work',
            professional_experience = legacy_data->>'professional_experience',
            area_of_interest = legacy_data->>'area_of_interest',
            goals = legacy_data->>'goals',
            achievements = legacy_data->>'achievements',
            needs = legacy_data->>'needs',
            challenges = legacy_data->>'challenges',
            family_members = (legacy_data->'family_members')::jsonb,
            economic_situation = legacy_data->>'economic_situation',
            living_situation = legacy_data->>'living_situation',
            additional_notes = legacy_data->>'additional_notes'
        WHERE legacy_data IS NOT NULL
    """)
    
    # Drop new columns
    op.drop_column('profiles', 'county_code')
    op.drop_column('profiles', 'municipality_code')
    op.drop_column('profiles', 'life_situations')
    op.drop_column('profiles', 'health_conditions')
    op.drop_column('profiles', 'health_details')
    op.drop_column('profiles', 'occupations')
    op.drop_column('profiles', 'support_purposes')
    op.drop_column('profiles', 'legacy_data')
