"""add_registration_requests_table

Revision ID: 4fdb23e67477
Revises: x9y0z1a2b3c4
Create Date: 2026-01-19 21:29:00.379030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fdb23e67477'
down_revision: Union[str, None] = 'x9y0z1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create registration_requests table for wholesale mode."""
    op.create_table(
        'registration_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('whatsapp_phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('birthdate', sa.Date(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, default='pending'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('rejection_reason', sa.String(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_registration_requests_id'), 'registration_requests', ['id'], unique=False)
    op.create_index(op.f('ix_registration_requests_email'), 'registration_requests', ['email'], unique=False)
    op.create_index(op.f('ix_registration_requests_status'), 'registration_requests', ['status'], unique=False)


def downgrade() -> None:
    """Drop registration_requests table."""
    op.drop_index(op.f('ix_registration_requests_status'), table_name='registration_requests')
    op.drop_index(op.f('ix_registration_requests_email'), table_name='registration_requests')
    op.drop_index(op.f('ix_registration_requests_id'), table_name='registration_requests')
    op.drop_table('registration_requests')
