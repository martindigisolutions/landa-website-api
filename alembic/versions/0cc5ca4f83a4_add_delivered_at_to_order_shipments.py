"""add_delivered_at_to_order_shipments

Revision ID: 0cc5ca4f83a4
Revises: 9edc4cb79819
Create Date: 2026-01-05 10:43:13.554745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cc5ca4f83a4'
down_revision: Union[str, None] = '9edc4cb79819'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add delivered_at column to order_shipments table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if column already exists (for local dev environments)
    columns = [col['name'] for col in inspector.get_columns('order_shipments')]
    
    if 'delivered_at' not in columns:
        op.add_column('order_shipments', sa.Column('delivered_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove delivered_at column from order_shipments table."""
    op.drop_column('order_shipments', 'delivered_at')
