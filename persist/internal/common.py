from __future__ import annotations

from typing import TypeAlias

import asyncio


__all__ = ()

MaybeFuture: TypeAlias = asyncio.Future[None] | None
