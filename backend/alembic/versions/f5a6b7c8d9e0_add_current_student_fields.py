"""add current student model fields"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, column_type in (
        ("age", sa.Integer()),
        ("contact_phone", sa.String()),
        ("schooling", sa.String()),
        ("responsible_name", sa.String()),
        ("responsible_dui", sa.String()),
        ("responsible_kinship", sa.String()),
        ("responsible_email", sa.String()),
        ("responsible_whatsapp", sa.String()),
    ):
        op.add_column("students", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    for name in (
        "responsible_whatsapp", "responsible_email", "responsible_kinship",
        "responsible_dui", "responsible_name", "schooling", "contact_phone", "age",
    ):
        op.drop_column("students", name)