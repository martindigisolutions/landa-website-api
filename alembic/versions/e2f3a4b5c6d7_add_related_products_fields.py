"""add_related_products_fields

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2025-12-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get existing columns in products table
    columns = [col['name'] for col in inspector.get_columns('products')]
    
    if 'similar_products' not in columns:
        op.add_column('products', sa.Column('similar_products', sa.JSON(), nullable=True))
    
    if 'frequently_bought_together' not in columns:
        op.add_column('products', sa.Column('frequently_bought_together', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('products')]
    
    if 'frequently_bought_together' in columns:
        op.drop_column('products', 'frequently_bought_together')
    
    if 'similar_products' in columns:
        op.drop_column('products', 'similar_products')

