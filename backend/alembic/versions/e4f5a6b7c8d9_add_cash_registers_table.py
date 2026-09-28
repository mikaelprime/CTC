"""add cash register table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3c4a5b6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cash_registers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cashier_id", sa.Integer(), nullable=False),
        sa.Column("initial_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("system_expected_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("real_physical_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("difference", sa.Float(), nullable=False, server_default="0"),
        sa.Column("audit_explanation", sa.String(), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"]),
    )
    op.create_index("ix_cash_registers_id", "cash_registers", ["id"])


def downgrade() -> None:
    op.drop_index("ix_cash_registers_id", table_name="cash_registers")
    op.drop_table("cash_registers")