from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import OdooSyncStatus

_odoo_sync_enum = PG_ENUM(
    OdooSyncStatus,
    name="odoo_sync_status",
    create_type=False,
)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    odoo_partner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
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

    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="client",
    )
