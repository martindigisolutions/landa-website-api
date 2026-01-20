"""add_business_info_to_registration_requests

Revision ID: da34f6cdc22d
Revises: 4fdb23e67477
Create Date: 2026-01-19 21:37:02.713056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da34f6cdc22d'
down_revision: Union[str, None] = '4fdb23e67477'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add business info columns to registration_requests table."""
    op.add_column('registration_requests', sa.Column('estimated_monthly_purchase', sa.Float(), nullable=True))
    op.add_column('registration_requests', sa.Column('notes', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove business info columns from registration_requests table."""
    op.drop_column('registration_requests', 'notes')
    op.drop_column('registration_requests', 'estimated_monthly_purchase')
