"""allow students without birth date"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("students", "birth_date", existing_type=sa.Date(), nullable=True)


def downgrade() -> None:
    op.alter_column("students", "birth_date", existing_type=sa.Date(), nullable=False)