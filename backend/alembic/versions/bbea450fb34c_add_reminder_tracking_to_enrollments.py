"""add last_reminder_due_date to enrollments

Revision ID: bbea450fb34c
Revises: 6477d6e55c1f
Create Date: 2026-09-22 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbea450fb34c'
down_revision: Union[str, Sequence[str], None] = '6477d6e55c1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('enrollments', sa.Column('last_reminder_due_date', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('enrollments', 'last_reminder_due_date')
