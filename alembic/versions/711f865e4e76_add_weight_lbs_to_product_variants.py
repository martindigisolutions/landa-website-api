"""add weight_lbs to product_variants

Revision ID: 711f865e4e76
Revises: k5l6m7n8o9p0
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '711f865e4e76'
down_revision: Union[str, None] = 'k5l6m7n8o9p0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column already exists before adding
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('product_variants')]
    
    if 'weight_lbs' not in columns:
        op.add_column('product_variants', sa.Column('weight_lbs', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove weight_lbs column from product_variants table
    op.drop_column('product_variants', 'weight_lbs')
