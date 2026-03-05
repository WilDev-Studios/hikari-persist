from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from hikaripersist.cached.base import CachedObject
from typing import TYPE_CHECKING

import hikari

if TYPE_CHECKING:
    import aiosqlite

__all__ = ("CachedRole",)

@dataclass(frozen=True, slots=True)
class CachedRole(CachedObject):
    """Represents a role in persistent cache."""

    id: hikari.Snowflake
    """The ID of the role."""
    guild_id: hikari.Snowflake
    """The ID of the guild that owns the role."""
    name: str
    """The name of the role."""
    color: hikari.Color
    """The color of the role."""
    permissions: hikari.Permissions
    """The permissions of the role."""
    created: datetime
    """The timestamp in which the role was created."""
    position: int
    """The position of the role."""

    @classmethod
    def from_sqlite(
        cls: type[CachedRole],
        row: aiosqlite.Row,
    ) -> CachedRole:
        return CachedRole(
            row[0],
            row[1],
            row[2],
            hikari.Color(row[3]),
            hikari.Permissions(row[4]),
            datetime.fromtimestamp(row[5], timezone.utc),
            row[6],
        )
