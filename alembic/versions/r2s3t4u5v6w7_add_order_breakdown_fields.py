"""Add subtotal, tax, shipping_fee to orders

Revision ID: r2s3t4u5v6w7
Revises: q1r2s3t4u5v6
Create Date: 2026-01-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'r2s3t4u5v6w7'
down_revision: Union[str, None] = 'q1r2s3t4u5v6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add subtotal column
    op.add_column('orders', sa.Column('subtotal', sa.Float(), nullable=True))
    
    # Add tax column
    op.add_column('orders', sa.Column('tax', sa.Float(), nullable=True))
    
    # Add shipping_fee column
    op.add_column('orders', sa.Column('shipping_fee', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'shipping_fee')
    op.drop_column('orders', 'tax')
    op.drop_column('orders', 'subtotal')

