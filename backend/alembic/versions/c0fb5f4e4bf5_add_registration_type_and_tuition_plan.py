"""add registration_type and tuition_plan to enrollments

Revision ID: c0fb5f4e4bf5
Revises: 1257339aed12
Create Date: 2026-09-22 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0fb5f4e4bf5'
down_revision: Union[str, Sequence[str], None] = '1257339aed12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default asegura que las matriculas ya existentes queden con un
    # valor valido (COMPLETA/GRUPAL) sin que la columna pueda quedar nula.
    op.add_column(
        'enrollments',
        sa.Column('registration_type', sa.String(length=20), nullable=False, server_default='COMPLETA'),
    )
    op.add_column(
        'enrollments',
        sa.Column('tuition_plan', sa.String(length=20), nullable=False, server_default='GRUPAL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('enrollments', 'tuition_plan')
    op.drop_column('enrollments', 'registration_type')
