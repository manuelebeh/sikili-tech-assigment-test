from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import OdooSyncStatus

_odoo_sync_enum = PG_ENUM(
    OdooSyncStatus,
    name="odoo_sync_status",
    create_type=False,
)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(512), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    odoo_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    odoo_sync_status: Mapped[OdooSyncStatus] = mapped_column(
        _odoo_sync_enum,
        nullable=False,
        default=OdooSyncStatus.pending,
        server_default=OdooSyncStatus.pending.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    client: Mapped[Client] = relationship("Client", back_populates="orders")


if TYPE_CHECKING:
    from app.clients.models import Client
