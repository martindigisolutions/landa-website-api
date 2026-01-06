"""add_order_combination_support

Revision ID: d698a66c483e
Revises: 0cc5ca4f83a4
Create Date: 2026-01-05 12:30:53.088418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd698a66c483e'
down_revision: Union[str, None] = '0cc5ca4f83a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add order combination support."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Add columns to orders table
    orders_columns = [col['name'] for col in inspector.get_columns('orders')]
    
    if 'combined_group_id' not in orders_columns:
        op.add_column('orders', sa.Column('combined_group_id', sa.String(), nullable=True))
        # Check if index exists before creating it
        indexes = [idx['name'] for idx in inspector.get_indexes('orders')]
        if 'ix_orders_combined_group_id' not in indexes:
            op.create_index('ix_orders_combined_group_id', 'orders', ['combined_group_id'])
    
    if 'combined' not in orders_columns:
        op.add_column('orders', sa.Column('combined', sa.Boolean(), nullable=True, server_default='0'))
    
    # Add column to order_shipments table
    shipments_columns = [col['name'] for col in inspector.get_columns('order_shipments')]
    
    if 'combined_group_id' not in shipments_columns:
        op.add_column('order_shipments', sa.Column('combined_group_id', sa.String(), nullable=True))
        # Check if index exists before creating it
        shipment_indexes = [idx['name'] for idx in inspector.get_indexes('order_shipments')]
        if 'ix_order_shipments_combined_group_id' not in shipment_indexes:
            op.create_index('ix_order_shipments_combined_group_id', 'order_shipments', ['combined_group_id'])
    
    # Create combined_orders table
    tables = inspector.get_table_names()
    if 'combined_orders' not in tables:
        op.create_table(
            'combined_orders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('combined_group_id', sa.String(), nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_combined_orders_combined_group_id', 'combined_orders', ['combined_group_id'])
        op.create_index('ix_combined_orders_order_id', 'combined_orders', ['order_id'])


def downgrade() -> None:
    """Remove order combination support."""
    op.drop_index('ix_combined_orders_order_id', table_name='combined_orders')
    op.drop_index('ix_combined_orders_combined_group_id', table_name='combined_orders')
    op.drop_table('combined_orders')
    
    op.drop_index('ix_order_shipments_combined_group_id', table_name='order_shipments')
    op.drop_column('order_shipments', 'combined_group_id')
    
    op.drop_index('ix_orders_combined_group_id', table_name='orders')
    op.drop_column('orders', 'combined')
    op.drop_column('orders', 'combined_group_id')
