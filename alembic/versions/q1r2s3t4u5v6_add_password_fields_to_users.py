"""Add password management fields to users

Revision ID: q1r2s3t4u5v6
Revises: p0q1r2s3t4u5
Create Date: 2026-01-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'q1r2s3t4u5v6'
down_revision: Union[str, None] = 'p0q1r2s3t4u5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add password_requires_update column
    op.add_column('users', sa.Column('password_requires_update', sa.Boolean(), nullable=True, server_default='0'))
    
    # Add password_last_updated column
    op.add_column('users', sa.Column('password_last_updated', sa.DateTime(), nullable=True))
    
    # Note: SQLite doesn't support ALTER COLUMN, so we can't change hashed_password to nullable
    # In production (PostgreSQL), you may need to run this manually if needed:
    # ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;


def downgrade() -> None:
    op.drop_column('users', 'password_last_updated')
    op.drop_column('users', 'password_requires_update')

