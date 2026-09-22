"""add institution_config table

Revision ID: 6140d97e3e02
Revises: b7c8d9e0f1a2
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6140d97e3e02'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'institution_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('institution_name', sa.String(length=150), nullable=False),
        sa.Column('late_fee', sa.Numeric(10, 2), nullable=False),
        sa.Column('payment_cycle_days', sa.Integer(), nullable=False),
        sa.Column('alert_days_before', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    # Fila única con los valores por defecto que antes vivían hardcodeados
    # en un diccionario de Python.
    op.execute(
        "INSERT INTO institution_config (id, institution_name, late_fee, "
        "payment_cycle_days, alert_days_before) "
        "VALUES (1, 'CTC El Salvador', 3.00, 28, 7)"
    )


def downgrade() -> None:
    op.drop_table('institution_config')
