"""
Odoo integration (XML-RPC is synchronous).

Sync clients must not block the asyncio event loop: wrap calls with ``run_in_executor``
when using ``async def`` route handlers (see fastapi-best-practices).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import partial
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


async def run_sync(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    """Run a blocking callable in the default thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))


def create_partner_sync(_name: str, _email: str, _phone: str | None) -> int:
    """
    Placeholder for ``xmlrpc.client`` partner creation.

    Returns a fake Odoo id until credentials and DB name are wired.
    """
    raise NotImplementedError("Wire XML-RPC to Odoo (use run_sync from async code).")
