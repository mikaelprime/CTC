"""cash_registers amounts float to numeric

Revision ID: 1257339aed12
Revises: 6140d97e3e02
Create Date: 2026-09-22 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1257339aed12'
down_revision: Union[str, Sequence[str], None] = '6140d97e3e02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ["initial_amount", "system_expected_amount", "real_physical_amount", "difference"]


def upgrade() -> None:
    for column in _COLUMNS:
        op.alter_column(
            'cash_registers', column,
            type_=sa.Numeric(10, 2),
            existing_type=sa.Float(),
        )


def downgrade() -> None:
    for column in _COLUMNS:
        op.alter_column(
            'cash_registers', column,
            type_=sa.Float(),
            existing_type=sa.Numeric(10, 2),
        )
