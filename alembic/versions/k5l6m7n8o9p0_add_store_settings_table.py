"""Add store settings table

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2024-12-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k5l6m7n8o9p0'
down_revision: Union[str, None] = 'j4k5l6m7n8o9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create store_settings table only if it doesn't exist
    if 'store_settings' not in existing_tables:
        op.create_table(
            'store_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('key', sa.String(), nullable=False),
            sa.Column('value', sa.String(), nullable=True),
            sa.Column('value_type', sa.String(), nullable=True, server_default='string'),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index(op.f('ix_store_settings_id'), 'store_settings', ['id'], unique=False)
        op.create_index(op.f('ix_store_settings_key'), 'store_settings', ['key'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_store_settings_key'), table_name='store_settings')
    op.drop_index(op.f('ix_store_settings_id'), table_name='store_settings')
    
    # Drop table
    op.drop_table('store_settings')
