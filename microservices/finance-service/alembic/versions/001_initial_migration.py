"""Initial migration — all finance tables.

Revision ID: 001
Revises:
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── expenses ──────────────────────────────────────────────────────────────
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("expense_type", sa.String(20), nullable=False, server_default="personal"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("merchant_name", sa.String(200), nullable=True),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("recurrence_pattern", sa.String(20), nullable=True),
        sa.Column("recurrence_day", sa.Integer(), nullable=True),
        sa.Column("next_occurrence_date", sa.Date(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_from", sa.String(50), nullable=True),
        sa.Column("receipt_image_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expenses_user_id", "expenses", ["user_id"])
    op.create_index("ix_expenses_category", "expenses", ["category"])
    op.create_index("ix_expenses_transaction_date", "expenses", ["transaction_date"])
    op.create_index("ix_expenses_deleted_at", "expenses", ["deleted_at"])

    # ── savings_goals ─────────────────────────────────────────────────────────
    op.create_table(
        "savings_goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("goal_type", sa.String(50), nullable=False, server_default="general"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("current_amount", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("progress", sa.Numeric(precision=5, scale=2), server_default="0.00", nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("auto_deposit_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("auto_deposit_amount", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("auto_deposit_frequency", sa.String(20), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("priority", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_savings_goals_user_id", "savings_goals", ["user_id"])
    op.create_index("ix_savings_goals_status", "savings_goals", ["status"])

    # ── savings_transactions ──────────────────────────────────────────────────
    op.create_table(
        "savings_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("goal_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("transaction_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["savings_goals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_savings_transactions_goal_id", "savings_transactions", ["goal_id"])
    op.create_index("ix_savings_transactions_user_id", "savings_transactions", ["user_id"])

    # ── cash_savings ──────────────────────────────────────────────────────────
    op.create_table(
        "cash_savings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("location", sa.String(50), nullable=True),
        sa.Column("location_description", sa.String(500), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("purpose", sa.String(100), nullable=True),
        sa.Column("last_counted_date", sa.Date(), nullable=True),
        sa.Column("denomination_breakdown", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cash_savings_user_id", "cash_savings", ["user_id"])

    # ── budgets ───────────────────────────────────────────────────────────────
    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("spent_amount", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("remaining_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PKR"),
        sa.Column("period", sa.String(20), nullable=False, server_default="monthly"),
        sa.Column("period_start_date", sa.Date(), nullable=False),
        sa.Column("period_end_date", sa.Date(), nullable=False),
        sa.Column("alert_threshold", sa.Numeric(precision=5, scale=2), server_default="80.00", nullable=False),
        sa.Column("alert_sent", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("alert_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exceeded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("exceeded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("rollover_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("rollover_amount", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])
    op.create_index("ix_budgets_category", "budgets", ["category"])
    op.create_index("ix_budgets_period", "budgets", ["period"])

    # ── spending_limits ───────────────────────────────────────────────────────
    op.create_table(
        "spending_limits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("daily_limit", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("weekly_limit", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("monthly_limit", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("daily_spent", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("weekly_spent", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("monthly_spent", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("daily_reset_date", sa.Date(), nullable=True),
        sa.Column("weekly_reset_date", sa.Date(), nullable=True),
        sa.Column("monthly_reset_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(3), server_default="PKR", nullable=False),
        sa.Column("alert_on_approach", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("alert_on_exceed", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_spending_limits_user_id"),
    )

    # ── zakat_records ─────────────────────────────────────────────────────────
    op.create_table(
        "zakat_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("calculation_date", sa.Date(), nullable=False),
        sa.Column("hijri_year", sa.String(20), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("cash_in_hand", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("bank_balance", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("gold_value", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("silver_value", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("investments", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("business_assets", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("receivables", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("other_assets", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("total_assets", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("immediate_debts", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("other_liabilities", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("total_liabilities", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("zakatable_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("nisab_threshold", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("nisab_met", sa.Boolean(), nullable=False),
        sa.Column("zakat_rate", sa.Numeric(precision=5, scale=2), server_default="2.5"),
        sa.Column("zakat_due", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("payment_status", sa.String(50), server_default="pending"),
        sa.Column("amount_paid", sa.Numeric(precision=15, scale=2), server_default="0.00"),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_zakat_records_user_id", "zakat_records", ["user_id"])
    op.create_index("ix_zakat_records_calculation_date", "zakat_records", ["calculation_date"])
    op.create_index("ix_zakat_records_payment_status", "zakat_records", ["payment_status"])

    # ── qurbani_savings ───────────────────────────────────────────────────────
    op.create_table(
        "qurbani_savings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_year", sa.Integer(), nullable=False),
        sa.Column("hijri_year", sa.String(20), nullable=True),
        sa.Column("target_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("current_amount", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("progress", sa.Numeric(precision=5, scale=2), server_default="0.00", nullable=False),
        sa.Column("animal_type", sa.String(50), nullable=True),
        sa.Column("animal_shares", sa.Integer(), server_default="1", nullable=False),
        sa.Column("estimated_cost_per_share", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("status", sa.String(50), server_default="saving", nullable=False),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("monthly_contribution", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("auto_save_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("currency", sa.String(10), server_default="USD", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("group_purchase", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qurbani_savings_user_id", "qurbani_savings", ["user_id"])
    op.create_index("ix_qurbani_savings_target_year", "qurbani_savings", ["target_year"])
    op.create_index("ix_qurbani_savings_status", "qurbani_savings", ["status"])


def downgrade() -> None:
    op.drop_table("qurbani_savings")
    op.drop_table("zakat_records")
    op.drop_table("spending_limits")
    op.drop_table("budgets")
    op.drop_table("cash_savings")
    op.drop_table("savings_transactions")
    op.drop_table("savings_goals")
    op.drop_table("expenses")
