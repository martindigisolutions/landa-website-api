"""Add shipping address fields to carts

Revision ID: l6m7n8o9p0q1
Revises: 711f865e4e76
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'l6m7n8o9p0q1'
down_revision: Union[str, None] = '711f865e4e76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check existing columns before adding
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('carts')]
    
    if 'shipping_street' not in columns:
        op.add_column('carts', sa.Column('shipping_street', sa.String(), nullable=True))
    if 'shipping_city' not in columns:
        op.add_column('carts', sa.Column('shipping_city', sa.String(), nullable=True))
    if 'shipping_state' not in columns:
        op.add_column('carts', sa.Column('shipping_state', sa.String(), nullable=True))
    if 'shipping_zipcode' not in columns:
        op.add_column('carts', sa.Column('shipping_zipcode', sa.String(), nullable=True))
    if 'is_pickup' not in columns:
        op.add_column('carts', sa.Column('is_pickup', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    op.drop_column('carts', 'is_pickup')
    op.drop_column('carts', 'shipping_zipcode')
    op.drop_column('carts', 'shipping_state')
    op.drop_column('carts', 'shipping_city')
    op.drop_column('carts', 'shipping_street')
