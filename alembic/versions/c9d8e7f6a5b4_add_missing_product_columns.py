"""add_missing_product_columns

Revision ID: c9d8e7f6a5b4
Revises: b8c7d6e5f4a3
Create Date: 2025-12-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d8e7f6a5b4'
down_revision: Union[str, None] = 'b8c7d6e5f4a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get existing columns in products table
    product_columns = [col['name'] for col in inspector.get_columns('products')]
    
    # Add missing columns to products table
    if 'seller_sku' not in product_columns:
        op.add_column('products', sa.Column('seller_sku', sa.String(), nullable=True))
        op.create_index(op.f('ix_products_seller_sku'), 'products', ['seller_sku'], unique=True)
    
    if 'name_en' not in product_columns:
        op.add_column('products', sa.Column('name_en', sa.String(), nullable=True))
    
    if 'short_description_en' not in product_columns:
        op.add_column('products', sa.Column('short_description_en', sa.String(), nullable=True))
    
    if 'description_en' not in product_columns:
        op.add_column('products', sa.Column('description_en', sa.String(), nullable=True))
    
    if 'tags' not in product_columns:
        op.add_column('products', sa.Column('tags', sa.String(), nullable=True))
    
    if 'tags_en' not in product_columns:
        op.add_column('products', sa.Column('tags_en', sa.String(), nullable=True))
    
    if 'gallery' not in product_columns:
        op.add_column('products', sa.Column('gallery', sa.JSON(), nullable=True))
    
    if 'created_at' not in product_columns:
        op.add_column('products', sa.Column('created_at', sa.DateTime(), nullable=True))
    
    if 'updated_at' not in product_columns:
        op.add_column('products', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    product_columns = [col['name'] for col in inspector.get_columns('products')]
    
    if 'updated_at' in product_columns:
        op.drop_column('products', 'updated_at')
    
    if 'created_at' in product_columns:
        op.drop_column('products', 'created_at')
    
    if 'gallery' in product_columns:
        op.drop_column('products', 'gallery')
    
    if 'tags_en' in product_columns:
        op.drop_column('products', 'tags_en')
    
    if 'tags' in product_columns:
        op.drop_column('products', 'tags')
    
    if 'description_en' in product_columns:
        op.drop_column('products', 'description_en')
    
    if 'short_description_en' in product_columns:
        op.drop_column('products', 'short_description_en')
    
    if 'name_en' in product_columns:
        op.drop_column('products', 'name_en')
    
    if 'seller_sku' in product_columns:
        op.drop_index(op.f('ix_products_seller_sku'), table_name='products')
        op.drop_column('products', 'seller_sku')

