"""add_order_shipments_table

Revision ID: 9edc4cb79819
Revises: r2s3t4u5v6w7
Create Date: 2026-01-05 10:20:13.241804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9edc4cb79819'
down_revision: Union[str, None] = 'r2s3t4u5v6w7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create order_shipments table for tracking multiple packages per order."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if table already exists (for local dev environments)
    tables = inspector.get_table_names()
    
    if 'order_shipments' not in tables:
        op.create_table(
            'order_shipments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('tracking_number', sa.String(), nullable=False),
            sa.Column('tracking_url', sa.String(), nullable=True),
            sa.Column('carrier', sa.String(), nullable=True),
            sa.Column('shipped_at', sa.DateTime(), nullable=True),
            sa.Column('estimated_delivery', sa.DateTime(), nullable=True),
            sa.Column('notes', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_order_shipments_order_id'), 'order_shipments', ['order_id'], unique=False)


def downgrade() -> None:
    """Drop order_shipments table."""
    op.drop_index(op.f('ix_order_shipments_order_id'), table_name='order_shipments')
    op.drop_table('order_shipments')
