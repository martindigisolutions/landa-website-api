"""Add bestseller_order and recommended_order to products

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2024-12-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'i3j4k5l6m7n8'
down_revision = 'h2i3j4k5l6m7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add bestseller_order and recommended_order columns to products table
    op.add_column('products', sa.Column('bestseller_order', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('recommended_order', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('products', 'recommended_order')
    op.drop_column('products', 'bestseller_order')
