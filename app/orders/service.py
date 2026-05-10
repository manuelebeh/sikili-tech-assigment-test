from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.models import Client
from app.enums import OdooSyncStatus
from app.orders.models import Order
from app.orders.schemas import OrderCreate
from app.services.odoo_service import OdooError, create_sale_order
from app.services.odoo_sync_support import (
    http_detail_for_odoo_exception,
    log_odoo_sync_failure,
)


def create_order(db: Session, data: OrderCreate) -> Order:
    client = db.get(Client, data.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    row = Order(
        client_id=data.client_id,
        product_name=data.product_name,
        amount=data.amount,
    )
    db.add(row)
    db.flush()

    if (
        client.odoo_partner_id is None
        or client.odoo_sync_status != OdooSyncStatus.synced
    ):
        row.odoo_sync_status = OdooSyncStatus.failed
        db.commit()
        db.refresh(row)
        log_odoo_sync_failure(
            event="order_odoo_blocked_client_not_synced",
            entity_type="order",
            entity_id=row.id,
            exc=RuntimeError("client_missing_odoo_partner"),
            client_id=client.id,
            client_odoo_sync_status=client.odoo_sync_status.value,
            client_odoo_partner_id=client.odoo_partner_id,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "This client is not linked to Odoo. Sync the customer before "
                "creating orders."
            ),
        )

    try:
        order_oid = create_sale_order(
            client.odoo_partner_id,
            data.product_name,
            data.amount,
        )
    except Exception as exc:
        row.odoo_sync_status = OdooSyncStatus.failed
        db.commit()
        db.refresh(row)
        log_odoo_sync_failure(
            event="order_odoo_sale_order_sync_failed",
            entity_type="order",
            entity_id=row.id,
            exc=exc,
            client_id=client.id,
            odoo_partner_id=client.odoo_partner_id,
            odoo_error_type=type(exc).__name__,
            is_odoo_error=isinstance(exc, OdooError),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=http_detail_for_odoo_exception(exc),
        ) from exc

    row.odoo_order_id = order_oid
    row.odoo_sync_status = OdooSyncStatus.synced
    db.commit()
    db.refresh(row)
    return row


def list_orders(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Order]:
    stmt = select(Order).order_by(Order.id).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())
