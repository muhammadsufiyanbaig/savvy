"""Initial migration — bank_accounts + bank_statements.

Revision ID: 001
Revises:
Create Date: 2026-05-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── bank_accounts ─────────────────────────────────────────────────────────
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column("bank_name", sa.String(255), nullable=False),
        sa.Column("account_number", sa.String(100), nullable=True),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("balance", sa.Numeric(15, 2), server_default="0.00", nullable=False),
        sa.Column("currency", sa.String(10), server_default="USD", nullable=False),
        sa.Column("credit_limit", sa.Numeric(15, 2), nullable=True),
        sa.Column("interest_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bank_accounts_user_id", "bank_accounts", ["user_id"])
    op.create_index("ix_bank_accounts_account_type", "bank_accounts", ["account_type"])
    op.create_index("ix_bank_accounts_is_active", "bank_accounts", ["is_active"])

    # ── bank_statements ───────────────────────────────────────────────────────
    op.create_table(
        "bank_statements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("statement_period_start", sa.Date(), nullable=True),
        sa.Column("statement_period_end", sa.Date(), nullable=True),
        sa.Column("statement_month", sa.String(7), nullable=True),
        sa.Column("processing_status", sa.String(50), server_default="uploaded", nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("total_transactions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_income", sa.Numeric(15, 2), server_default="0.00", nullable=False),
        sa.Column("total_expenses", sa.Numeric(15, 2), server_default="0.00", nullable=False),
        sa.Column("s3_bucket", sa.String(255), nullable=True),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["bank_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bank_statements_user_id", "bank_statements", ["user_id"])
    op.create_index("ix_bank_statements_account_id", "bank_statements", ["account_id"])
    op.create_index("ix_bank_statements_processing_status", "bank_statements", ["processing_status"])
    op.create_index("ix_bank_statements_statement_month", "bank_statements", ["statement_month"])
    op.create_index(
        "ix_bank_statements_period",
        "bank_statements",
        ["statement_period_start", "statement_period_end"],
    )


def downgrade() -> None:
    op.drop_table("bank_statements")
    op.drop_table("bank_accounts")
