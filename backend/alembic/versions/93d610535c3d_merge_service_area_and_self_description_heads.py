"""merge service_area and self_description heads

Revision ID: 93d610535c3d
Revises: f7e3b1865c08, d8c41e7a2b19
Create Date: 2026-08-27 17:18:56.826657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93d610535c3d'
down_revision: Union[str, Sequence[str], None] = ('f7e3b1865c08', 'd8c41e7a2b19')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
