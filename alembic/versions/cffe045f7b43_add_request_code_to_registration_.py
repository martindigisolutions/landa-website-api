"""add_request_code_to_registration_requests

Revision ID: cffe045f7b43
Revises: 4e7e7ce16973
Create Date: 2026-01-19 22:32:55.570586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cffe045f7b43'
down_revision: Union[str, None] = '4e7e7ce16973'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add request_code column to registration_requests table."""
    import secrets
    import string
    
    # Add column as nullable first (with a default to handle NOT NULL constraint)
    op.add_column('registration_requests', sa.Column('request_code', sa.String(), nullable=True))
    
    # Generate codes for existing records
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id FROM registration_requests WHERE request_code IS NULL"))
    rows = result.fetchall()
    
    chars = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'  # No confusing chars
    used_codes = set()
    
    for row in rows:
        # Generate unique code
        for _ in range(10):
            code = 'REQ-' + ''.join(secrets.choice(chars) for _ in range(6))
            if code not in used_codes:
                used_codes.add(code)
                break
        
        conn.execute(
            sa.text("UPDATE registration_requests SET request_code = :code WHERE id = :id"),
            {"code": code, "id": row[0]}
        )
    
    # For SQLite: use batch_alter_table to change column to NOT NULL
    with op.batch_alter_table('registration_requests') as batch_op:
        batch_op.alter_column('request_code', nullable=False)
    
    # Add unique index
    op.create_index('ix_registration_requests_request_code', 'registration_requests', ['request_code'], unique=True)


def downgrade() -> None:
    """Remove request_code column from registration_requests table."""
    op.drop_index('ix_registration_requests_request_code', table_name='registration_requests')
    op.drop_column('registration_requests', 'request_code')
