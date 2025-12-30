"""add active to products

Revision ID: p0q1r2s3t4u5
Revises: o9p0q1r2s3t4
Create Date: 2025-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p0q1r2s3t4u5'
down_revision: Union[str, None] = 'o9p0q1r2s3t4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add active column to products table with default True
    # Works on both SQLite and PostgreSQL
    op.add_column('products', sa.Column('active', sa.Boolean(), 
                                        nullable=False, 
                                        server_default=sa.text('TRUE')))


def downgrade() -> None:
    op.drop_column('products', 'active')
