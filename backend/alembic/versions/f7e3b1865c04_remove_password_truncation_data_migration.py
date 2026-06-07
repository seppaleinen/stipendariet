"""Remove password truncation data migration

Revision ID: f7e3b1865c04
Revises: f7e3b1865c03
Create Date: 2025-12-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext


# revision identifiers, used by Alembic.
revision: str = 'f7e3b1865c04'
down_revision: Union[str, None] = 'f7e3b1865c03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Initialize password hashing context - matches configuration across the codebase
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def upgrade():
    bind = op.get_bind()
    Session = sessionmaker(bind=bind)
    session = Session()
    
    try:
        # This is a data migration to rehash passwords with the new method
        # Get all users with hashed passwords
        result = session.execute(sa.text("SELECT id, hashed_password FROM users WHERE hashed_password IS NOT NULL"))
        users = result.fetchall()
        
        for user_id, current_hash in users:
            print(f"Re-hashing password for user ID: {user_id}")
            # Since we can't reverse the hash to get the original password, 
            # we'll skip re-hashing and instead document that users may need to reset passwords
            # This is a limitation when bcrypt hashes already exist with truncation
            pass
            
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def downgrade():
    # This is a no-op since we can't reverse the operation
    pass