from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.models import Client
from app.clients.schemas import ClientCreate
from app.enums import OdooSyncStatus
from app.services.odoo_service import OdooError, create_partner
from app.services.odoo_sync_support import (
    http_detail_for_odoo_exception,
    log_odoo_sync_failure,
)


def create_client(db: Session, data: ClientCreate) -> Client:
    row = Client(name=data.name, email=str(data.email), phone=data.phone)
    db.add(row)
    db.flush()

    try:
        partner_id = create_partner(row.name, row.email, row.phone)
    except Exception as exc:
        row.odoo_sync_status = OdooSyncStatus.failed
        db.commit()
        db.refresh(row)
        log_odoo_sync_failure(
            event="client_odoo_partner_sync_failed",
            entity_type="client",
            entity_id=row.id,
            exc=exc,
            odoo_error_type=type(exc).__name__,
            is_odoo_error=isinstance(exc, OdooError),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=http_detail_for_odoo_exception(exc),
        ) from exc

    row.odoo_partner_id = partner_id
    row.odoo_sync_status = OdooSyncStatus.synced
    db.commit()
    db.refresh(row)
    return row


def list_clients(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Client]:
    stmt = (
        select(Client).order_by(Client.id).offset(skip).limit(limit)
    )
    return list(db.scalars(stmt).all())
