"""Add tax rate cache table

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'n8o9p0q1r2s3'
down_revision: Union[str, None] = 'm7n8o9p0q1r2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'tax_rate_cache' not in inspector.get_table_names():
        op.create_table(
            'tax_rate_cache',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('street_name', sa.String(), nullable=True),
            sa.Column('city', sa.String(), nullable=False),
            sa.Column('state', sa.String(), nullable=False),
            sa.Column('zipcode', sa.String(), nullable=False),
            sa.Column('tax_rate', sa.Float(), nullable=False),
            sa.Column('county', sa.String(), nullable=True),
            sa.Column('location_code', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_tax_cache_address', 'tax_rate_cache', ['street_name', 'city', 'state', 'zipcode'])
        op.create_index('ix_tax_rate_cache_id', 'tax_rate_cache', ['id'])
    else:
        # If table exists, check if street_name column exists
        columns = [c['name'] for c in inspector.get_columns('tax_rate_cache')]
        if 'street_name' not in columns:
            op.add_column('tax_rate_cache', sa.Column('street_name', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_index('ix_tax_cache_address', table_name='tax_rate_cache')
    op.drop_index('ix_tax_rate_cache_id', table_name='tax_rate_cache')
    op.drop_table('tax_rate_cache')
