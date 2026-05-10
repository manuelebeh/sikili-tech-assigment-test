from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clients import schemas, service
from app.database import get_db

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=schemas.ClientRead)
def create_client(
    body: schemas.ClientCreate,
    db: Session = Depends(get_db),
) -> schemas.ClientRead:
    return service.create_client(db, body)


@router.get("", response_model=list[schemas.ClientRead])
def list_clients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[schemas.ClientRead]:
    return service.list_clients(db, skip=skip, limit=limit)
