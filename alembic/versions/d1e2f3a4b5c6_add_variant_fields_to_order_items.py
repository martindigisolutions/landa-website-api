"""add_variant_fields_to_order_items

Revision ID: d1e2f3a4b5c6
Revises: c9d8e7f6a5b4
Create Date: 2025-12-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c9d8e7f6a5b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get existing columns in order_items table
    columns = [col['name'] for col in inspector.get_columns('order_items')]
    
    if 'variant_id' not in columns:
        op.add_column('order_items', sa.Column('variant_id', sa.Integer(), nullable=True))
    
    if 'variant_name' not in columns:
        op.add_column('order_items', sa.Column('variant_name', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('order_items')]
    
    if 'variant_name' in columns:
        op.drop_column('order_items', 'variant_name')
    
    if 'variant_id' in columns:
        op.drop_column('order_items', 'variant_id')

