"""Add user_activities table for tracking user actions

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 's3t4u5v6w7x8'
down_revision: Union[str, None] = 'd698a66c483e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create user_activities table only if it doesn't exist
    if 'user_activities' not in existing_tables:
        op.create_table(
            'user_activities',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('session_id', sa.String(), nullable=True),
            sa.Column('method', sa.String(), nullable=False),
            sa.Column('endpoint', sa.String(), nullable=False),
            sa.Column('action_type', sa.String(), nullable=False),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('query_params', sa.JSON(), nullable=True),
            sa.Column('request_body', sa.JSON(), nullable=True),
            sa.Column('response_status', sa.Integer(), nullable=True),
            sa.Column('ip_address', sa.String(), nullable=True),
            sa.Column('user_agent', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index(op.f('ix_user_activities_id'), 'user_activities', ['id'], unique=False)
        op.create_index(op.f('ix_user_activities_user_id'), 'user_activities', ['user_id'], unique=False)
        op.create_index(op.f('ix_user_activities_session_id'), 'user_activities', ['session_id'], unique=False)
        op.create_index(op.f('ix_user_activities_endpoint'), 'user_activities', ['endpoint'], unique=False)
        op.create_index(op.f('ix_user_activities_action_type'), 'user_activities', ['action_type'], unique=False)
        op.create_index(op.f('ix_user_activities_created_at'), 'user_activities', ['created_at'], unique=False)
        
        # Create composite indexes
        op.create_index(
            'ix_user_activities_user_created',
            'user_activities',
            ['user_id', 'created_at'],
            unique=False
        )
        op.create_index(
            'ix_user_activities_session_created',
            'user_activities',
            ['session_id', 'created_at'],
            unique=False
        )
        op.create_index(
            'ix_user_activities_action_created',
            'user_activities',
            ['action_type', 'created_at'],
            unique=False
        )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_user_activities_action_created', table_name='user_activities')
    op.drop_index('ix_user_activities_session_created', table_name='user_activities')
    op.drop_index('ix_user_activities_user_created', table_name='user_activities')
    op.drop_index(op.f('ix_user_activities_created_at'), table_name='user_activities')
    op.drop_index(op.f('ix_user_activities_action_type'), table_name='user_activities')
    op.drop_index(op.f('ix_user_activities_endpoint'), table_name='user_activities')
    op.drop_index(op.f('ix_user_activities_session_id'), table_name='user_activities')
    op.drop_index(op.f('ix_user_activities_user_id'), table_name='user_activities')
    op.drop_index(op.f('ix_user_activities_id'), table_name='user_activities')
    
    # Drop table
    op.drop_table('user_activities')

