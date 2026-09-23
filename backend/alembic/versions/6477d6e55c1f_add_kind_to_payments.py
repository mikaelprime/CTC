"""add kind to payments

Revision ID: 6477d6e55c1f
Revises: c0fb5f4e4bf5
Create Date: 2026-09-22 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6477d6e55c1f'
down_revision: Union[str, Sequence[str], None] = 'c0fb5f4e4bf5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'payments',
        sa.Column('kind', sa.String(length=20), nullable=False, server_default='COLEGIATURA'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('payments', 'kind')
