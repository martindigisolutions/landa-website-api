"""Add shipping contact fields to carts

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'm7n8o9p0q1r2'
down_revision: Union[str, None] = 'l6m7n8o9p0q1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check existing columns before adding
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('carts')]
    
    if 'shipping_first_name' not in columns:
        op.add_column('carts', sa.Column('shipping_first_name', sa.String(), nullable=True))
    if 'shipping_last_name' not in columns:
        op.add_column('carts', sa.Column('shipping_last_name', sa.String(), nullable=True))
    if 'shipping_phone' not in columns:
        op.add_column('carts', sa.Column('shipping_phone', sa.String(), nullable=True))
    if 'shipping_email' not in columns:
        op.add_column('carts', sa.Column('shipping_email', sa.String(), nullable=True))
    if 'shipping_country' not in columns:
        op.add_column('carts', sa.Column('shipping_country', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('carts', 'shipping_country')
    op.drop_column('carts', 'shipping_email')
    op.drop_column('carts', 'shipping_phone')
    op.drop_column('carts', 'shipping_last_name')
    op.drop_column('carts', 'shipping_first_name')
