from __future__ import annotations

from dataclasses import dataclass
from hikaripersist.cached.base import CachedObject
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite
    import hikari

__all__ = ("CachedMessage",)

@dataclass(frozen=True, slots=True)
class CachedMessage(CachedObject):
    """Represents a message in persistent cache."""

    id: hikari.Snowflake
    channel_id: hikari.Snowflake
    guild_id: hikari.Snowflake | None
    content: str | None

    @classmethod
    def from_sqlite(
        cls: type[CachedMessage],
        row: aiosqlite.Row,
    ) -> CachedMessage:
        return cls(*row)
