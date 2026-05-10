from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.models import Client
from app.clients.schemas import ClientCreate


def create_client(db: Session, data: ClientCreate) -> Client:
    row = Client(name=data.name, email=str(data.email), phone=data.phone)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_clients(db: Session, *, skip: int = 0, limit: int = 100) -> list[Client]:
    stmt = (
        select(Client).order_by(Client.id).offset(skip).limit(limit)
    )
    return list(db.scalars(stmt).all())
