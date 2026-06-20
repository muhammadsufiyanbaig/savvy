"""Add assets table.

Revision ID: 002
Revises: 001
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("ticker_symbol", sa.String(20), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True, server_default="USD"),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=False, server_default="1"),
        sa.Column("purchase_price_per_unit", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("current_price_per_unit", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("last_price_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("location_detail", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_id"), "assets", ["id"], unique=False)
    op.create_index(op.f("ix_assets_user_id"), "assets", ["user_id"], unique=False)
    op.create_index(op.f("ix_assets_category"), "assets", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assets_category"), table_name="assets")
    op.drop_index(op.f("ix_assets_user_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_id"), table_name="assets")
    op.drop_table("assets")
