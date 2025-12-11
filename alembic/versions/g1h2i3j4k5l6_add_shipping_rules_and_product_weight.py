"""add_shipping_rules_and_product_weight

Revision ID: g1h2i3j4k5l6
Revises: e2f3a4b5c6d7
Create Date: 2025-12-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add weight_lbs column to products table (if not exists)
    # SQLite doesn't support IF NOT EXISTS for ADD COLUMN, so we check first
    conn = op.get_bind()
    columns = [col['name'] for col in conn.execute(sa.text("PRAGMA table_info(products)")).mappings()]
    if 'weight_lbs' not in columns:
        op.add_column('products', sa.Column('weight_lbs', sa.Float(), nullable=True, server_default='0.0'))
    
    # Create shipping_rules table (if not exists)
    tables = [t[0] for t in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
    if 'shipping_rules' not in tables:
        op.create_table(
            'shipping_rules',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('rule_type', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('selected_products', sa.JSON(), nullable=True),  # Array of seller_sku
            sa.Column('selected_categories', sa.JSON(), nullable=True),  # Array of category slugs
            sa.Column('product_quantity', sa.Integer(), nullable=True),
            sa.Column('free_weight_lbs', sa.Float(), nullable=True),
            sa.Column('minimum_weight_lbs', sa.Float(), nullable=True),
            sa.Column('charge_amount', sa.Float(), nullable=True),
            sa.Column('rate_per_lb', sa.Float(), nullable=True),
            sa.Column('priority', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_shipping_rules_id'), 'shipping_rules', ['id'], unique=False)
        op.create_index(op.f('ix_shipping_rules_rule_type'), 'shipping_rules', ['rule_type'], unique=False)


def downgrade() -> None:
    # Drop shipping_rules table if exists
    conn = op.get_bind()
    tables = [t[0] for t in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
    if 'shipping_rules' in tables:
        # Try to drop indexes first (ignore if they don't exist)
        try:
            op.drop_index(op.f('ix_shipping_rules_rule_type'), table_name='shipping_rules')
        except Exception:
            pass
        try:
            op.drop_index(op.f('ix_shipping_rules_id'), table_name='shipping_rules')
        except Exception:
            pass
        op.drop_table('shipping_rules')
    
    # Drop weight_lbs column from products (SQLite doesn't support DROP COLUMN easily)
    # For SQLite, this would require recreating the table, so we skip it in downgrade
    pass
