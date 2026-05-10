from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums import OdooSyncStatus


class ClientCreate(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=64)


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str | None
    odoo_partner_id: int | None
    odoo_sync_status: OdooSyncStatus
    created_at: datetime
