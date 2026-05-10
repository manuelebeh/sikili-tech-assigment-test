"""Structured logging and safe HTTP messages for Odoo ↔ DB sync."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.odoo_service import (
    OdooAuthenticationError,
    OdooError,
    OdooPartnerCreateError,
    OdooSaleOrderCreateError,
)

logger = logging.getLogger(__name__)


def log_odoo_sync_failure(
    *,
    event: str,
    entity_type: str,
    entity_id: int | None,
    exc: BaseException,
    **context: Any,
) -> None:
    """
    Single structured ERROR line for a persisted entity after Odoo sync failed.

    Uses JSON for stable key=value inspection in log aggregators.
    """
    payload: dict[str, Any] = {
        "event": event,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "exc_type": type(exc).__name__,
        "exc_message": str(exc),
        **context,
    }
    logger.error(
        "odoo_sync_failure %s",
        json.dumps(payload, default=str),
        extra={"odoo_sync": payload},
        exc_info=isinstance(exc, Exception),
    )


def http_detail_for_odoo_exception(exc: BaseException) -> str:
    """
    Short, user-facing message (no raw Odoo fault strings or stack traces).
    """
    if isinstance(exc, OdooAuthenticationError):
        return (
            "Could not authenticate with Odoo. Check integration credentials "
            "or try again later."
        )
    if isinstance(exc, OdooPartnerCreateError):
        return (
            "The customer could not be synced to Odoo. Your record was saved; "
            "retry or contact support if this persists."
        )
    if isinstance(exc, OdooSaleOrderCreateError):
        return (
            "The order could not be synced to Odoo. Your record was saved; "
            "retry or contact support if this persists."
        )
    if isinstance(exc, OdooError):
        return (
            "Odoo integration is misconfigured or unavailable. Your record "
            "was saved; try again later."
        )
    return (
        "An unexpected error occurred while syncing with Odoo. Your record "
        "was saved; try again later."
    )
