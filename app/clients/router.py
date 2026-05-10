from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.clients import schemas, service
from app.database import get_db

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
