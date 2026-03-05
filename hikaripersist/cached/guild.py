from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from hikaripersist.cached.base import CachedObject
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite
    import hikari

__all__ = ("CachedGuild",)

@dataclass(frozen=True, slots=True)
class CachedGuild(CachedObject):
    """Represents a guild in persistent cache."""

    id: hikari.Snowflake
    """The ID of the guild."""
    name: str
    """The name of the guild."""
    description: str | None
    """The description of the guild, if present."""
    owner: hikari.Snowflake
    """The ID of the guild's parent user."""
    created: datetime
    """The timestamp in which the guild was created."""

    @classmethod
    def from_sqlite(
        cls: type[CachedGuild],
        row: aiosqlite.Row,
    ) -> CachedGuild:
        return cls(
            row[0],
            row[1],
            row[2],
            row[3],
            datetime.fromtimestamp(row[4], timezone.utc),
        )
