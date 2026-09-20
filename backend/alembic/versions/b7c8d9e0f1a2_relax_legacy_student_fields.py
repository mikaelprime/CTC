"""relax legacy student fields"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in ("email", "phone", "address", "education_level", "guardian_name", "guardian_dui", "guardian_relationship"):
        op.alter_column("students", name, existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    for name in ("email", "phone", "address", "education_level", "guardian_name", "guardian_dui", "guardian_relationship"):
        op.alter_column("students", name, existing_type=sa.String(), nullable=False)