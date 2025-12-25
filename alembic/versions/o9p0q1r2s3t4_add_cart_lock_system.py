"""Add cart lock system for checkout

Revision ID: o9p0q1r2s3t4
Revises: n8o9p0q1r2s3
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'o9p0q1r2s3t4'
down_revision: Union[str, None] = 'n8o9p0q1r2s3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Add payment_method to carts table
    if 'carts' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('carts')]
        if 'payment_method' not in columns:
            op.add_column('carts', sa.Column('payment_method', sa.String(), nullable=True))
    
    # Create cart_locks table
    if 'cart_locks' not in existing_tables:
        op.create_table(
            'cart_locks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('cart_id', sa.Integer(), nullable=False),
            sa.Column('token', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=True, default='active'),
            sa.Column('stripe_payment_intent_id', sa.String(), nullable=True),
            sa.Column('subtotal', sa.Float(), nullable=True),
            sa.Column('shipping_fee', sa.Float(), nullable=True),
            sa.Column('tax', sa.Float(), nullable=True),
            sa.Column('total', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('used_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_cart_locks_id', 'cart_locks', ['id'])
        op.create_index('ix_cart_locks_token', 'cart_locks', ['token'], unique=True)
        op.create_index('ix_cart_locks_status', 'cart_locks', ['status'])
        op.create_index('ix_cart_locks_stripe_payment_intent_id', 'cart_locks', ['stripe_payment_intent_id'])
    
    # Create stock_reservations table
    if 'stock_reservations' not in existing_tables:
        op.create_table(
            'stock_reservations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('lock_id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('variant_id', sa.Integer(), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('unit_price', sa.Float(), nullable=False),
            sa.ForeignKeyConstraint(['lock_id'], ['cart_locks.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_stock_reservations_id', 'stock_reservations', ['id'])


def downgrade() -> None:
    op.drop_table('stock_reservations')
    op.drop_table('cart_locks')
    op.drop_column('carts', 'payment_method')
