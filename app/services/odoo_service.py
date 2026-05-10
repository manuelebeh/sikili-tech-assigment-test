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
from functools import partial
from typing import Any, ParamSpec, TypeVar
from urllib.parse import urljoin

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


class OdooError(Exception):
    """Generic error from the Odoo XML-RPC client."""


class OdooAuthenticationError(OdooError):
    """Authentication failed (invalid credentials or database)."""


class OdooPartnerCreateError(OdooError):
    """Failed to create a ``res.partner`` record via XML-RPC."""


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
        return self._common.version()

    def authenticate(self) -> int:
        """
        Authenticate against ``/xmlrpc/2/common`` and return the Odoo user id.

        The uid is cached for subsequent :meth:`execute_kw` calls.
        """
        uid = self._common.authenticate(
            self._config.database,
            self._config.username,
            self._config.password,
            {},
        )
        if not uid or not isinstance(uid, int):
            raise OdooAuthenticationError(
                "authenticate() failed: check database name, login, and password "
                "(or use an API key instead of the password on Odoo 14+)."
            )
        self._uid = uid
        return uid

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
        return self._object.execute_kw(
            self._config.database,
            self.uid,
            self._config.password,
            model,
            method,
            pos_args,
            kw,
        )

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
        logger.error(
            "Odoo authentication failed while creating partner name=%r email=%r",
            name,
            email,
        )
        raise
    except xmlrpc.client.Fault as e:
        logger.error(
            "Odoo XML-RPC Fault creating res.partner: faultCode=%s faultString=%s "
            "name=%r email=%r",
            e.faultCode,
            e.faultString,
            name,
            email,
        )
        raise OdooPartnerCreateError(
            f"Odoo rejected partner create (fault {e.faultCode}): {e.faultString}"
        ) from e
    except xmlrpc.client.ProtocolError as e:
        logger.error(
            "Odoo XML-RPC protocol error creating partner: errcode=%s errmsg=%s "
            "name=%r email=%r",
            e.errcode,
            e.errmsg,
            name,
            email,
        )
        raise OdooPartnerCreateError(
            f"Odoo XML-RPC transport error (HTTP {e.errcode}): {e.errmsg}"
        ) from e
    except OSError as e:
        logger.error(
            "Network error calling Odoo while creating partner: %s name=%r email=%r",
            e,
            name,
            email,
        )
        raise OdooPartnerCreateError(f"Could not reach Odoo: {e}") from e
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
