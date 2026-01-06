"""add stripe payment fields to orders

Revision ID: a1b2c3d4e5f6
Revises: 50c420a644d8
Create Date: 2024-12-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '50c420a644d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Stripe payment fields to orders table."""
    # Check if columns exist before adding them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    order_columns = [col['name'] for col in inspector.get_columns('orders')]
    
    # Add columns only if they don't exist
    if 'stripe_payment_intent_id' not in order_columns:
        op.add_column('orders', sa.Column('stripe_payment_intent_id', sa.String(), nullable=True))
    
    if 'payment_status' not in order_columns:
        op.add_column('orders', sa.Column('payment_status', sa.String(), nullable=True, server_default='pending'))
    
    if 'paid_at' not in order_columns:
        op.add_column('orders', sa.Column('paid_at', sa.DateTime(), nullable=True))
    
    # Create index on stripe_payment_intent_id for faster lookups (if column exists and index doesn't)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('orders')]
    if 'stripe_payment_intent_id' in order_columns and 'ix_orders_stripe_payment_intent_id' not in existing_indexes:
        try:
            op.create_index('ix_orders_stripe_payment_intent_id', 'orders', ['stripe_payment_intent_id'])
        except Exception:
            # Index might already exist, ignore
            pass


def downgrade() -> None:
    """Remove Stripe payment fields from orders table."""
    op.drop_index('ix_orders_stripe_payment_intent_id', table_name='orders')
    op.drop_column('orders', 'paid_at')
    op.drop_column('orders', 'payment_status')
    op.drop_column('orders', 'stripe_payment_intent_id')

