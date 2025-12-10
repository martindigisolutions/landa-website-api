"""add_categories_tables

Revision ID: b8c7d6e5f4a3
Revises: d0bfed9cad13
Create Date: 2025-12-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c7d6e5f4a3'
down_revision: Union[str, None] = 'd0bfed9cad13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Create category_groups table
    if 'category_groups' not in tables:
        op.create_table('category_groups',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('name_en', sa.String(), nullable=True),
            sa.Column('slug', sa.String(), nullable=False),
            sa.Column('icon', sa.String(), nullable=True),
            sa.Column('show_in_filters', sa.Boolean(), nullable=True, default=True),
            sa.Column('display_order', sa.Integer(), nullable=True, default=0),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_category_groups_id'), 'category_groups', ['id'], unique=False)
        op.create_index(op.f('ix_category_groups_slug'), 'category_groups', ['slug'], unique=True)
    
    # Create categories table
    if 'categories' not in tables:
        op.create_table('categories',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('group_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('name_en', sa.String(), nullable=True),
            sa.Column('slug', sa.String(), nullable=False),
            sa.Column('color', sa.String(), nullable=True),
            sa.Column('icon', sa.String(), nullable=True),
            sa.Column('display_order', sa.Integer(), nullable=True, default=0),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['group_id'], ['category_groups.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_categories_id'), 'categories', ['id'], unique=False)
        op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)
    
    # Create product_categories junction table
    if 'product_categories' not in tables:
        op.create_table('product_categories',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('category_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_product_categories_id'), 'product_categories', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Drop product_categories table
    if 'product_categories' in tables:
        op.drop_index(op.f('ix_product_categories_id'), table_name='product_categories')
        op.drop_table('product_categories')
    
    # Drop categories table
    if 'categories' in tables:
        op.drop_index(op.f('ix_categories_slug'), table_name='categories')
        op.drop_index(op.f('ix_categories_id'), table_name='categories')
        op.drop_table('categories')
    
    # Drop category_groups table
    if 'category_groups' in tables:
        op.drop_index(op.f('ix_category_groups_slug'), table_name='category_groups')
        op.drop_index(op.f('ix_category_groups_id'), table_name='category_groups')
        op.drop_table('category_groups')

