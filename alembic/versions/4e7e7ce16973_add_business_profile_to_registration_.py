"""add_business_profile_to_registration_requests

Revision ID: 4e7e7ce16973
Revises: da34f6cdc22d
Create Date: 2026-01-19 22:16:13.523220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e7e7ce16973'
down_revision: Union[str, None] = 'da34f6cdc22d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add business profile columns to registration_requests table."""
    op.add_column('registration_requests', sa.Column('business_types', sa.JSON(), nullable=True))
    op.add_column('registration_requests', sa.Column('services_offered', sa.JSON(), nullable=True))
    op.add_column('registration_requests', sa.Column('frequent_products', sa.JSON(), nullable=True))
    op.add_column('registration_requests', sa.Column('team_size', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove business profile columns from registration_requests table."""
    op.drop_column('registration_requests', 'team_size')
    op.drop_column('registration_requests', 'frequent_products')
    op.drop_column('registration_requests', 'services_offered')
    op.drop_column('registration_requests', 'business_types')
