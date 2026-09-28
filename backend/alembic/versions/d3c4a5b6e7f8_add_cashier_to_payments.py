"""add cashier ownership to payments"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d3c4a5b6e7f8"
down_revision: Union[str, Sequence[str], None] = "cf3160d0b64d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("cashier_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_payments_cashier_id_users", "payments", "users", ["cashier_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_payments_cashier_id_users", "payments", type_="foreignkey")
    op.drop_column("payments", "cashier_id")