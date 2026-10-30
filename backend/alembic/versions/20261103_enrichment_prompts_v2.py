"""Alter enrichment_prompts table: replace unique(name) with unique(name, version).

Revision ID: 20261103_enrichment_prompts_v2
Revises: 20261030_source_url
Create Date: 2026-11-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20261103_enrichment_prompts_v2'
down_revision: Union[str, None] = '20261030_source_url'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def index_exists(table, index_name):
        return index_name in insp.get_indexes(table)

    # Drop the old unique index on 'name' if it exists
    old_index = "uq_prompt_name"
    if index_exists("enrichment_prompts", old_index):
        op.drop_index(old_index, table_name="enrichment_prompts")

    # Create the new composite unique constraint on (name, version)
    op.create_unique_constraint(
        "uq_prompt_name_version",
        "enrichment_prompts",
        ["name", "version"],
    )


def downgrade() -> None:
    # Drop the composite unique constraint
    op.drop_constraint("uq_prompt_name_version", "enrichment_prompts", type_="unique")

    # Re-create the old unique index on 'name'
    op.create_index("uq_prompt_name", "enrichment_prompts", ["name"], unique=True)