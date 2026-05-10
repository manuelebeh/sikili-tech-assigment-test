from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.orders import schemas, service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=schemas.OrderRead)
def create_order(
    body: schemas.OrderCreate,
    db: Session = Depends(get_db),
) -> schemas.OrderRead:
    return service.create_order(db, body)


@router.get("", response_model=list[schemas.OrderRead])
def list_orders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[schemas.OrderRead]:
    return service.list_orders(db, skip=skip, limit=limit)
