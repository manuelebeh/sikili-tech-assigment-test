"""Initial clients and orders tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    sync_enum = postgresql.ENUM(
        "pending",
        "synced",
        "failed",
        name="odoo_sync_status",
    )
    sync_enum.create(bind, checkfirst=True)

    sync_enum_col = postgresql.ENUM(
        "pending",
        "synced",
        "failed",
        name="odoo_sync_status",
        create_type=False,
    )

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("odoo_partner_id", sa.Integer(), nullable=True),
        sa.Column(
            "odoo_sync_status",
            sync_enum_col,
            nullable=False,
            server_default=sa.text("'pending'::odoo_sync_status"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=512), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("odoo_order_id", sa.Integer(), nullable=True),
        sa.Column(
            "odoo_sync_status",
            sync_enum_col,
            nullable=False,
            server_default=sa.text("'pending'::odoo_sync_status"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_client_id"), "orders", ["client_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_client_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_table("clients")
    op.execute(sa.text("DROP TYPE IF EXISTS odoo_sync_status"))
