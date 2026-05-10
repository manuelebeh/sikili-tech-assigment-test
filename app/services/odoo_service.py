"""
Odoo integration via XML-RPC using only the standard library ``xmlrpc.client``.

- ``/xmlrpc/2/common``: meta calls such as ``authenticate`` and ``version``.
- ``/xmlrpc/2/object``: ``execute_kw`` against Odoo models.

Calls are **synchronous**. For FastAPI / asyncio, use ``run_sync`` so you do not block
the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import xmlrpc.client
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from functools import partial
from typing import Any, ParamSpec, TypeVar
from urllib.parse import urljoin

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)

# Generic sellable product used for free-text lines (description + price); override via env.
_MISC_PRODUCT_DEFAULT_CODE = "SIKILI_MISC_LINE"


class OdooError(Exception):
    """Generic error from the Odoo XML-RPC client."""


class OdooAuthenticationError(OdooError):
    """Authentication failed (invalid credentials or database)."""


class OdooPartnerCreateError(OdooError):
    """Failed to create a ``res.partner`` record via XML-RPC."""


class OdooSaleOrderCreateError(OdooError):
    """Failed to create a ``sale.order`` (or related product/line) via XML-RPC."""


@dataclass(frozen=True, slots=True)
class OdooConfig:
    """Connection parameters for an Odoo instance."""

    base_url: str
    database: str
    username: str
    password: str


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _xmlrpc_url(base_url: str, path: str) -> str:
    return urljoin(f"{_normalize_base_url(base_url)}/", path.lstrip("/"))


def odoo_config_from_env(
    *,
    base_url: str | None = None,
    database: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> OdooConfig:
    """
    Build an :class:`OdooConfig` from explicit arguments or environment variables:

    - ``ODOO_URL`` (defaults to ``http://localhost:8069`` when nothing else is set)
    - ``ODOO_DB`` or ``ODOO_DATABASE``
    - ``ODOO_LOGIN`` or ``ODOO_USER``
    - ``ODOO_PASSWORD``
    """
    url = base_url or os.environ.get("ODOO_URL", "http://localhost:8069")
    db = database or os.environ.get("ODOO_DB") or os.environ.get("ODOO_DATABASE")
    user = username or os.environ.get("ODOO_LOGIN") or os.environ.get("ODOO_USER")
    pwd = password or os.environ.get("ODOO_PASSWORD")
    missing = [
        name
        for name, val in (
            ("ODOO_DB / ODOO_DATABASE", db),
            ("ODOO_LOGIN / ODOO_USER", user),
            ("ODOO_PASSWORD", pwd),
        )
        if not val
    ]
    if missing:
        raise OdooError(
            "Missing environment variables for Odoo XML-RPC: "
            + ", ".join(missing)
            + ". Set them or pass keyword arguments to odoo_config_from_env()."
        )
    return OdooConfig(
        base_url=_normalize_base_url(url),
        database=db,
        username=user,
        password=pwd,
    )


class OdooXMLRPCClient:
    """
    Minimal XML-RPC client: authenticate on ``common``, model calls on ``object``.
    """

    __slots__ = ("_config", "_common", "_object", "_uid")

    def __init__(self, config: OdooConfig) -> None:
        self._config = config
        base = _normalize_base_url(config.base_url)
        self._common = xmlrpc.client.ServerProxy(
            _xmlrpc_url(base, "/xmlrpc/2/common"),
            allow_none=True,
        )
        self._object = xmlrpc.client.ServerProxy(
            _xmlrpc_url(base, "/xmlrpc/2/object"),
            allow_none=True,
        )
        self._uid: int | None = None

    @property
    def config(self) -> OdooConfig:
        return self._config

    def version(self) -> dict[str, Any]:
        """Server info without authentication; useful for a quick connectivity check."""
        try:
            return self._common.version()
        except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError) as e:
            self._log_rpc_exception("common.version", e)
            raise

    def authenticate(self) -> int:
        """
        Authenticate against ``/xmlrpc/2/common`` and return the Odoo user id.

        The uid is cached for subsequent :meth:`execute_kw` calls.
        """
        try:
            uid = self._common.authenticate(
                self._config.database,
                self._config.username,
                self._config.password,
                {},
            )
        except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError) as e:
            self._log_rpc_exception("common.authenticate", e)
            raise
        if not uid or not isinstance(uid, int):
            raise OdooAuthenticationError(
                "authenticate() failed: check database name, login, and password "
                "(or use an API key instead of the password on Odoo 14+)."
            )
        self._uid = uid
        return uid

    def _log_rpc_exception(self, operation: str, exc: Exception) -> None:
        """Structured log for each failed XML-RPC round-trip (warning level)."""
        if isinstance(exc, xmlrpc.client.Fault):
            logger.warning(
                "odoo_xmlrpc_fault operation=%s faultCode=%s faultString=%s",
                operation,
                exc.faultCode,
                exc.faultString,
                extra={
                    "odoo_operation": operation,
                    "odoo_fault_code": exc.faultCode,
                    "odoo_fault_string": exc.faultString,
                },
            )
        elif isinstance(exc, xmlrpc.client.ProtocolError):
            logger.warning(
                "odoo_xmlrpc_protocol operation=%s errcode=%s errmsg=%s url=%s",
                operation,
                exc.errcode,
                exc.errmsg,
                getattr(exc, "url", ""),
                extra={
                    "odoo_operation": operation,
                    "odoo_http_status": exc.errcode,
                },
            )
        else:
            logger.warning(
                "odoo_xmlrpc_transport operation=%s error=%s",
                operation,
                exc,
                extra={"odoo_operation": operation},
            )

    @property
    def uid(self) -> int:
        if self._uid is None:
            self.authenticate()
        assert self._uid is not None
        return self._uid

    def execute_kw(
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: Mapping[str, Any] | None = None,
    ) -> Any:
        """
        Call Odoo's ``execute_kw`` on ``/xmlrpc/2/object``.

        ``args`` is the positional argument list expected by the Odoo method (often a
        domain list ``[[...]]`` or values ``[{...}]``).
        """
        pos_args = [] if args is None else args
        kw = dict(kwargs or {})
        try:
            return self._object.execute_kw(
                self._config.database,
                self.uid,
                self._config.password,
                model,
                method,
                pos_args,
                kw,
            )
        except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError) as e:
            self._log_rpc_exception(f"object.execute_kw:{model}.{method}", e)
            raise

    def invalidate_session(self) -> None:
        """Clear cached uid so the next call that needs it will re-authenticate."""
        self._uid = None


async def run_sync(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    """Run a blocking callable (e.g. XML-RPC) in the default thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))


def create_partner(
    name: str,
    email: str,
    phone: str | None = None,
    *,
    client: OdooXMLRPCClient | None = None,
    config: OdooConfig | None = None,
) -> int:
    """
    Create a customer ``res.partner`` (``customer_rank=1``) and return the Odoo record id.

    Pass either a configured :class:`OdooXMLRPCClient` or an :class:`OdooConfig` (a client
    will be created internally). If both are omitted, configuration is loaded via
    :func:`odoo_config_from_env`.

    Raises:
        OdooAuthenticationError: When login / database credentials are invalid.
        OdooPartnerCreateError: On RPC faults, transport errors, or unexpected responses.
    """
    if client is None:
        cfg = config if config is not None else odoo_config_from_env()
        client = OdooXMLRPCClient(cfg)

    vals: dict[str, Any] = {
        "name": name.strip(),
        "email": email.strip(),
        "customer_rank": 1,
    }
    if phone and str(phone).strip():
        vals["phone"] = str(phone).strip()

    try:
        new_id: Any = client.execute_kw("res.partner", "create", [vals])
    except OdooAuthenticationError:
        raise
    except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError) as e:
        raise OdooPartnerCreateError(
            f"Odoo partner create failed ({type(e).__name__}): {e}"
        ) from e
    except OdooError:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error creating Odoo res.partner name=%r email=%r",
            name,
            email,
        )
        raise OdooPartnerCreateError(f"Unexpected error creating partner: {e}") from e

    if not isinstance(new_id, int):
        logger.error(
            "res.partner create returned non-int: %r name=%r email=%r",
            type(new_id).__name__,
            name,
            email,
        )
        raise OdooPartnerCreateError(
            f"res.partner create expected integer id, got {type(new_id).__name__}"
        )

    logger.info(
        "Created Odoo res.partner id=%s customer_rank=1 name=%r email=%r",
        new_id,
        name,
        email,
    )
    return new_id


def _ensure_misc_sale_product(client: OdooXMLRPCClient) -> int:
    """
    Return a ``product.product`` id suitable for generic integration lines.

    Uses ``ODOO_DEFAULT_SALE_PRODUCT_ID`` when set; otherwise searches by
    ``default_code`` :data:`_MISC_PRODUCT_DEFAULT_CODE`, or creates a minimal service
    product that is sellable.
    """
    raw = os.environ.get("ODOO_DEFAULT_SALE_PRODUCT_ID")
    if raw is not None and str(raw).strip() != "":
        try:
            pid = int(raw)
        except ValueError as e:
            raise OdooSaleOrderCreateError(
                f"ODOO_DEFAULT_SALE_PRODUCT_ID must be an integer, got {raw!r}"
            ) from e
        if pid <= 0:
            raise OdooSaleOrderCreateError(
                "ODOO_DEFAULT_SALE_PRODUCT_ID must be a positive integer"
            )
        return pid

    found: Any = client.execute_kw(
        "product.product",
        "search",
        [[["default_code", "=", _MISC_PRODUCT_DEFAULT_CODE], ["sale_ok", "=", True]]],
        {"limit": 1},
    )
    if isinstance(found, list) and found:
        return found[0]

    pid_any: Any = client.execute_kw(
        "product.product",
        "create",
        [
            {
                "name": "Miscellaneous (integration)",
                "default_code": _MISC_PRODUCT_DEFAULT_CODE,
                "type": "service",
                "sale_ok": True,
                "purchase_ok": False,
            }
        ],
    )
    if not isinstance(pid_any, int):
        raise OdooSaleOrderCreateError(
            f"product.product create expected integer id, got {type(pid_any).__name__}"
        )
    logger.info(
        "Created placeholder product.product id=%s default_code=%r for integration "
        "sale lines",
        pid_any,
        _MISC_PRODUCT_DEFAULT_CODE,
    )
    return pid_any


def create_sale_order(
    partner_id: int,
    product_name: str,
    amount: float | int | Decimal,
    *,
    client: OdooXMLRPCClient | None = None,
    config: OdooConfig | None = None,
) -> int:
    """
    Create a ``sale.order`` for ``partner_id`` with one ``sale.order.line``.

    The line uses a generic sellable product (see :func:`_ensure_misc_sale_product`) and
    sets the line description to ``product_name``, quantity ``1``, and ``price_unit``
    from ``amount``. Returns the new ``sale.order`` id.

    Raises:
        OdooAuthenticationError: Invalid Odoo credentials.
        OdooSaleOrderCreateError: Validation errors, RPC faults, transport errors, or bad
            responses (e.g. Sales app not installed).
    """
    if partner_id <= 0:
        raise OdooSaleOrderCreateError("partner_id must be a positive Odoo id")

    line_name = product_name.strip()
    if not line_name:
        raise OdooSaleOrderCreateError("product_name must not be empty")

    try:
        unit_price = float(amount)
    except (TypeError, ValueError) as e:
        raise OdooSaleOrderCreateError(
            f"amount must be numeric, got {amount!r}"
        ) from e

    if client is None:
        cfg = config if config is not None else odoo_config_from_env()
        client = OdooXMLRPCClient(cfg)

    try:
        product_id = _ensure_misc_sale_product(client)
        order_vals: dict[str, Any] = {
            "partner_id": partner_id,
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": product_id,
                        "name": line_name,
                        "product_uom_qty": 1,
                        "price_unit": unit_price,
                    },
                )
            ],
        }
        order_id: Any = client.execute_kw("sale.order", "create", [order_vals])
    except OdooAuthenticationError:
        raise
    except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError) as e:
        raise OdooSaleOrderCreateError(
            f"Odoo sale order create failed ({type(e).__name__}): {e}"
        ) from e
    except OdooError:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error creating Odoo sale.order partner_id=%s product_name=%r",
            partner_id,
            line_name,
        )
        raise OdooSaleOrderCreateError(
            f"Unexpected error creating sale order: {e}"
        ) from e

    if not isinstance(order_id, int):
        logger.error(
            "sale.order create returned non-int: %r partner_id=%s product_name=%r",
            type(order_id).__name__,
            partner_id,
            line_name,
        )
        raise OdooSaleOrderCreateError(
            f"sale.order create expected integer id, got {type(order_id).__name__}"
        )

    logger.info(
        "Created Odoo sale.order id=%s partner_id=%s line=%r qty=1 price_unit=%s",
        order_id,
        partner_id,
        line_name,
        unit_price,
    )
    return order_id


def create_partner_sync(
    name: str,
    email: str,
    phone: str | None = None,
    *,
    client: OdooXMLRPCClient | None = None,
    config: OdooConfig | None = None,
) -> int:
    """
    Same as :func:`create_partner` (sync XML-RPC); kept for backward compatibility.
    """
    return create_partner(
        name,
        email,
        phone,
        client=client,
        config=config,
    )
