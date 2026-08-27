from __future__ import annotations

from typing import TypeAlias

import asyncio


__all__ = ()

MaybeFuture: TypeAlias = asyncio.Future[None] | None
"""An alias for any type taking either no return or `Future` with no result."""
