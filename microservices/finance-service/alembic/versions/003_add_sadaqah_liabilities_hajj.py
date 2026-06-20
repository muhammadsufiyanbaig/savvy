"""Add sadaqah_records, liabilities, hajj_umrah_plans, hajj_umrah_deposits tables.

Revision ID: 003
Revises: 002
Create Date: 2026-06-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── sadaqah_records ───────────────────────────────────────────────────────
    op.create_table(
        "sadaqah_records",
        sa.Column("id",         sa.Integer(),                  nullable=False),
        sa.Column("user_id",    sa.Integer(),                  nullable=False),
        sa.Column("amount",     sa.Numeric(15, 2),             nullable=False),
        sa.Column("currency",   sa.String(10),                 server_default="USD"),
        sa.Column("category",   sa.String(50),                 nullable=False),
        sa.Column("recipient",  sa.String(255),                nullable=True),
        sa.Column("date",       sa.Date(),                     nullable=False),
        sa.Column("notes",      sa.Text(),                     nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),    server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),    nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True),    nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sadaqah_records_id",      "sadaqah_records", ["id"],       unique=False)
    op.create_index("ix_sadaqah_records_user_id", "sadaqah_records", ["user_id"],  unique=False)
    op.create_index("ix_sadaqah_records_date",    "sadaqah_records", ["date"],     unique=False)

    # ── liabilities ───────────────────────────────────────────────────────────
    op.create_table(
        "liabilities",
        sa.Column("id",                  sa.Integer(),               nullable=False),
        sa.Column("user_id",             sa.Integer(),               nullable=False),
        sa.Column("name",                sa.String(255),             nullable=False),
        sa.Column("category",            sa.String(50),              nullable=False),
        sa.Column("currency",            sa.String(10),              server_default="USD"),
        sa.Column("original_amount",     sa.Numeric(15, 2),          nullable=True),
        sa.Column("amount_owed",         sa.Numeric(15, 2),          nullable=False),
        sa.Column("monthly_payment",     sa.Numeric(15, 2),          nullable=True),
        sa.Column("due_date",            sa.Date(),                  nullable=True),
        sa.Column("lender",              sa.String(255),             nullable=True),
        sa.Column("is_interest_bearing", sa.Boolean(),               server_default="false"),
        sa.Column("notes",               sa.Text(),                  nullable=True),
        sa.Column("is_active",           sa.Boolean(),               server_default="true"),
        sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at",          sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_liabilities_id",      "liabilities", ["id"],      unique=False)
    op.create_index("ix_liabilities_user_id", "liabilities", ["user_id"], unique=False)

    # ── hajj_umrah_plans ──────────────────────────────────────────────────────
    op.create_table(
        "hajj_umrah_plans",
        sa.Column("id",             sa.Integer(),               nullable=False),
        sa.Column("user_id",        sa.Integer(),               nullable=False),
        sa.Column("plan_type",      sa.String(20),              nullable=False),
        sa.Column("title",          sa.String(255),             nullable=True),
        sa.Column("target_year",    sa.Integer(),               nullable=False),
        sa.Column("num_persons",    sa.Integer(),               server_default="1"),
        sa.Column("departure_city", sa.String(100),             nullable=True),
        sa.Column("package_type",   sa.String(20),              server_default="standard"),
        sa.Column("estimated_cost", sa.Numeric(15, 2),          nullable=False),
        sa.Column("current_amount", sa.Numeric(15, 2),          server_default="0"),
        sa.Column("currency",       sa.String(10),              server_default="USD"),
        sa.Column("notes",          sa.Text(),                  nullable=True),
        sa.Column("is_active",      sa.Boolean(),               server_default="true"),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at",     sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hajj_umrah_plans_id",      "hajj_umrah_plans", ["id"],      unique=False)
    op.create_index("ix_hajj_umrah_plans_user_id", "hajj_umrah_plans", ["user_id"], unique=False)

    # ── hajj_umrah_deposits ───────────────────────────────────────────────────
    op.create_table(
        "hajj_umrah_deposits",
        sa.Column("id",         sa.Integer(),               nullable=False),
        sa.Column("plan_id",    sa.Integer(),               nullable=False),
        sa.Column("user_id",    sa.Integer(),               nullable=False),
        sa.Column("amount",     sa.Numeric(15, 2),          nullable=False),
        sa.Column("note",       sa.String(255),             nullable=True),
        sa.Column("date",       sa.Date(),                  nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["plan_id"], ["hajj_umrah_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hajj_umrah_deposits_id",      "hajj_umrah_deposits", ["id"],      unique=False)
    op.create_index("ix_hajj_umrah_deposits_user_id", "hajj_umrah_deposits", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("hajj_umrah_deposits")
    op.drop_table("hajj_umrah_plans")
    op.drop_table("liabilities")
    op.drop_table("sadaqah_records")
