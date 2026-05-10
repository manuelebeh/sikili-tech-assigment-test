from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.models import Client
from app.orders.models import Order
from app.orders.schemas import OrderCreate


def create_order(db: Session, data: OrderCreate) -> Order:
    if db.get(Client, data.client_id) is None:
        raise HTTPException(status_code=404, detail="Client not found")
    row = Order(
        client_id=data.client_id,
        product_name=data.product_name,
        amount=data.amount,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_orders(db: Session, *, skip: int = 0, limit: int = 100) -> list[Order]:
    stmt = select(Order).order_by(Order.id).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())
