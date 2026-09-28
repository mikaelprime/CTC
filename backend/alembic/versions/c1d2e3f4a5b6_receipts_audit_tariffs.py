"""comprobantes correlativos, bitácora, tarifario configurable y limpieza

- receipts: comprobante de cada cobro (número correlativo R-000001).
- payments.receipt_id / payments.cash_register_id: cada cuota sabe en qué
  comprobante y en qué caja entró. Los pagos ya existentes se asignan a la
  caja que el cajero tenía abierta cuando se registraron.
- cash_registers.cash_count: arqueo por denominación.
- audit_logs: bitácora de operaciones sensibles.
- users: contraseña temporal y bloqueo por intentos fallidos persistente.
- institution_config: tarifario (antes fijo en el código).
- Se eliminan diplomas.registration_fee / monthly_fee (el sistema nunca los
  usó para cobrar: el tarifario es institucional) y students.dui (la
  propuesta solo pide el DUI del responsable y el escritorio nunca lo pidió).

Revision ID: c1d2e3f4a5b6
Revises: bbea450fb34c
Create Date: 2026-09-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "bbea450fb34c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), sa.ForeignKey("enrollments.id"), nullable=False),
        sa.Column("cashier_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cash_register_id", sa.Integer(), sa.ForeignKey("cash_registers.id"), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("payment_type", sa.String(length=30), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("cash_received", sa.Numeric(10, 2), nullable=False),
        sa.Column("change", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("void_reason", sa.String(length=200), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_receipts_id", "receipts", ["id"])

    with op.batch_alter_table("payments") as batch:
        batch.add_column(sa.Column("receipt_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cash_register_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_payments_receipt_id", "receipts", ["receipt_id"], ["id"])
        batch.create_foreign_key("fk_payments_cash_register_id", "cash_registers", ["cash_register_id"], ["id"])
        batch.create_index("ix_payments_receipt_id", ["receipt_id"])
        batch.create_index("ix_payments_cash_register_id", ["cash_register_id"])

    # Antes la caja sumaba "los pagos del cajero desde que abrió": se asigna
    # cada pago existente a la caja que su cajero tenía abierta en ese momento.
    op.execute(
        """
        UPDATE payments SET cash_register_id = (
            SELECT cr.id FROM cash_registers cr
            WHERE cr.cashier_id = payments.cashier_id
              AND payments.created_at >= cr.opened_at
              AND (cr.closed_at IS NULL OR payments.created_at <= cr.closed_at)
            ORDER BY cr.opened_at DESC
            LIMIT 1
        )
        WHERE payments.cashier_id IS NOT NULL AND payments.cash_register_id IS NULL
        """
    )

    op.add_column("cash_registers", sa.Column("cash_count", sa.Text(), nullable=True))

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("institution_config") as batch:
        batch.add_column(sa.Column("registration_full_fee", sa.Numeric(10, 2), nullable=False, server_default="20.00"))
        batch.add_column(sa.Column("registration_promo_fee", sa.Numeric(10, 2), nullable=False, server_default="10.00"))
        batch.add_column(sa.Column("tuition_group_fee", sa.Numeric(10, 2), nullable=False, server_default="25.00"))
        batch.add_column(sa.Column("tuition_private_fee", sa.Numeric(10, 2), nullable=False, server_default="55.00"))
        batch.add_column(sa.Column("tuition_online_fee", sa.Numeric(10, 2), nullable=False, server_default="70.00"))

    with op.batch_alter_table("diplomas") as batch:
        batch.drop_column("registration_fee")
        batch.drop_column("monthly_fee")

    with op.batch_alter_table("students") as batch:
        batch.drop_column("dui")


def downgrade() -> None:
    with op.batch_alter_table("students") as batch:
        batch.add_column(sa.Column("dui", sa.String(), nullable=True))

    with op.batch_alter_table("diplomas") as batch:
        batch.add_column(sa.Column("monthly_fee", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("registration_fee", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("institution_config") as batch:
        for column in ("tuition_online_fee", "tuition_private_fee", "tuition_group_fee",
                       "registration_promo_fee", "registration_full_fee"):
            batch.drop_column(column)

    with op.batch_alter_table("users") as batch:
        batch.drop_column("locked_until")
        batch.drop_column("failed_login_attempts")
        batch.drop_column("must_change_password")

    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_column("cash_registers", "cash_count")

    with op.batch_alter_table("payments") as batch:
        batch.drop_index("ix_payments_cash_register_id")
        batch.drop_index("ix_payments_receipt_id")
        batch.drop_constraint("fk_payments_cash_register_id", type_="foreignkey")
        batch.drop_constraint("fk_payments_receipt_id", type_="foreignkey")
        batch.drop_column("cash_register_id")
        batch.drop_column("receipt_id")

    op.drop_index("ix_receipts_id", table_name="receipts")
    op.drop_table("receipts")
