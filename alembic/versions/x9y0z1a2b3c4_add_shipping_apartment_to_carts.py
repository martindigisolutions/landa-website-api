"""Add shipping_apartment to carts

Revision ID: x9y0z1a2b3c4
Revises: s3t4u5v6w7x8
Create Date: 2026-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'x9y0z1a2b3c4'
down_revision: Union[str, None] = 's3t4u5v6w7x8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check existing columns before adding
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('carts')]
    
    if 'shipping_apartment' not in columns:
        op.add_column('carts', sa.Column('shipping_apartment', sa.String(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('carts')]
    
    if 'shipping_apartment' in columns:
        op.drop_column('carts', 'shipping_apartment')
