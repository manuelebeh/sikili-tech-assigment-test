from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import OdooSyncStatus


class OrderCreate(BaseModel):
    """
    Payload for ``POST /clients/{client_id}/orders`` (client id comes from the path).
    """

    product_name: str = Field(..., max_length=512)
    amount: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    product_name: str
    amount: Decimal
    odoo_order_id: int | None
    odoo_sync_status: OdooSyncStatus
    created_at: datetime
