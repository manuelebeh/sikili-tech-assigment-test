from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.clients import schemas, service
from app.database import get_db
from app.orders import service as orders_service
from app.orders.schemas import OrderCreate, OrderRead

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get(
    "",
    response_model=list[schemas.ClientRead],
    summary="List clients",
)
def list_clients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[schemas.ClientRead]:
    """Return clients ordered by id with optional pagination."""
    rows = service.list_clients(db, skip=skip, limit=limit)
    return [schemas.ClientRead.model_validate(r) for r in rows]


@router.post(
    "",
    response_model=schemas.ClientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create client",
    description=(
        "Insert the client in the database, call Odoo XML-RPC "
        "(``odoo_service.create_partner``) for ``res.partner``, then set "
        "``odoo_partner_id`` and ``odoo_sync_status=synced`` on success."
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": (
                "Odoo sync failed after the row was saved with "
                "``odoo_sync_status=failed``."
            ),
        },
    },
)
def create_client(
    body: schemas.ClientCreate,
    db: Session = Depends(get_db),
) -> schemas.ClientRead:
    """Create locally and sync to Odoo; see router description for the flow."""
    row = service.create_client(db, body)
    return schemas.ClientRead.model_validate(row)


@router.get(
    "/{client_id}/orders",
    response_model=list[OrderRead],
    summary="List orders for a client",
    tags=["orders"],
)
def list_client_orders(
    client_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[OrderRead]:
    """Orders for ``client_id``, increasing id (pagination)."""
    rows = orders_service.list_orders_for_client(
        db, client_id, skip=skip, limit=limit
    )
    return [OrderRead.model_validate(r) for r in rows]


@router.post(
    "/{client_id}/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create order for a client",
    description=(
        "Persist the order, call Odoo XML-RPC (``odoo_service.create_sale_order``), "
        "then set ``odoo_order_id`` and ``odoo_sync_status=synced`` on success."
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": (
                "Odoo sync failed after the row was saved with "
                "``odoo_sync_status=failed``."
            ),
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Client exists but is not linked to Odoo yet.",
        },
    },
    tags=["orders"],
)
def create_client_order(
    client_id: int,
    body: OrderCreate,
    db: Session = Depends(get_db),
) -> OrderRead:
    """Create locally and sync to Odoo; see router description."""
    row = orders_service.create_order(db, client_id, body)
    return OrderRead.model_validate(row)
