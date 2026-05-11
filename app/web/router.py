"""Minimal HTML UI: forms and lists with visible errors (no styling polish)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.clients.models import Client
from app.clients.schemas import ClientCreate
from app.clients.service import create_client as svc_create_client
from app.clients.service import list_clients as svc_list_clients
from app.database import get_db
from app.orders.schemas import OrderCreate
from app.orders.service import create_order as svc_create_order
from app.orders.service import list_orders_for_client as svc_list_orders_for_client

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(prefix="/ui", tags=["ui"])

_OK_LABELS = {
    "client_saved": (
        "Client saved. Check sync status in the table (synced / failed / pending)."
    ),
    "order_saved": (
        "Order saved. Check sync status on the orders list."
    ),
}


def _flash_ok(raw: str | None) -> str | None:
    if raw is None:
        return None
    return _OK_LABELS.get(raw, raw)


def _detail(exc: HTTPException) -> str:
    d = exc.detail
    if isinstance(d, str):
        return d
    if isinstance(d, list):
        return "; ".join(
            str(x.get("msg", x)) if isinstance(x, dict) else str(x) for x in d
        )
    return str(d)


@router.get("/clients", response_class=HTMLResponse)
def ui_clients_list(
    request: Request,
    db: Session = Depends(get_db),
    ok: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    rows = svc_list_clients(db)
    return templates.TemplateResponse(
        request,
        "clients_list.html",
        {
            "request": request,
            "clients": rows,
            "ok_message": _flash_ok(ok),
            "error_message": error,
        },
    )


@router.get("/clients/new", response_class=HTMLResponse)
def ui_client_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "clients_form.html",
        {
            "request": request,
            "name": "",
            "email": "",
            "phone": "",
            "error": None,
        },
    )


@router.post("/clients", response_model=None)
def ui_client_create(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
) -> RedirectResponse | HTMLResponse:
    phone_clean = phone.strip() or None
    try:
        data = ClientCreate(name=name, email=email, phone=phone_clean)
    except ValidationError as e:
        errs = e.errors()
        parts = [
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in errs
        ]
        msg = "; ".join(parts)
        return templates.TemplateResponse(
            request,
            "clients_form.html",
            {
                "request": request,
                "name": name,
                "email": email,
                "phone": phone,
                "error": msg,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        svc_create_client(db, data)
    except HTTPException as e:
        return templates.TemplateResponse(
            request,
            "clients_form.html",
            {
                "request": request,
                "name": name,
                "email": email,
                "phone": phone,
                "error": _detail(e),
            },
            status_code=e.status_code,
        )

    return RedirectResponse(
        url="/ui/clients?ok=client_saved",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/clients/{client_id}/orders", response_class=HTMLResponse)
def ui_orders_list(
    request: Request,
    client_id: int,
    db: Session = Depends(get_db),
    ok: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    rows = svc_list_orders_for_client(db, client_id)
    return templates.TemplateResponse(
        request,
        "orders_list.html",
        {
            "request": request,
            "client": client,
            "orders": rows,
            "ok_message": _flash_ok(ok),
            "error_message": error,
        },
    )


@router.get("/clients/{client_id}/orders/new", response_class=HTMLResponse)
def ui_order_form(request: Request, client_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return templates.TemplateResponse(
        request,
        "orders_form.html",
        {
            "request": request,
            "client": client,
            "product_name": "",
            "amount": "",
            "error": None,
        },
    )


@router.post("/clients/{client_id}/orders", response_model=None)
def ui_order_create(
    request: Request,
    client_id: int,
    db: Session = Depends(get_db),
    product_name: str = Form(""),
    amount: str = Form(""),
) -> RedirectResponse | HTMLResponse:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    try:
        amount_dec = Decimal(amount.strip())
    except (InvalidOperation, ValueError, ArithmeticError):
        return templates.TemplateResponse(
            request,
            "orders_form.html",
            {
                "request": request,
                "client": client,
                "product_name": product_name,
                "amount": amount,
                "error": "Invalid amount (use a decimal number, e.g. 12.50).",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        data = OrderCreate(product_name=product_name.strip(), amount=amount_dec)
    except ValidationError as e:
        parts = [
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in e.errors()
        ]
        msg = "; ".join(parts)
        return templates.TemplateResponse(
            request,
            "orders_form.html",
            {
                "request": request,
                "client": client,
                "product_name": product_name,
                "amount": amount,
                "error": msg,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        svc_create_order(db, client_id, data)
    except HTTPException as e:
        return templates.TemplateResponse(
            request,
            "orders_form.html",
            {
                "request": request,
                "client": client,
                "product_name": product_name,
                "amount": amount,
                "error": _detail(e),
            },
            status_code=e.status_code,
        )

    return RedirectResponse(
        url=f"/ui/clients/{client_id}/orders?ok=order_saved",
        status_code=status.HTTP_303_SEE_OTHER,
    )
