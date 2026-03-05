from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from hikaripersist.cached.base import CachedObject

import hikari

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
    icon: str | None
    """If present, the hash of the role's icon."""
    permissions: hikari.Permissions
    """The permissions of the role."""
    created: datetime
    """The timestamp in which the role was created."""
    position: int
    """The position of the role."""
    hoisted: bool
    """If member's with this role are hoisted."""
    bot_id: hikari.Snowflake | None
    """The ID of the bot the role belongs to, if managed by a bot."""
    premium: bool
    """If the role is the guild's premium boosting role."""

    @classmethod
    def from_sqlite(
        cls: type[CachedRole],
        row, # noqa: ANN001 - Ambiguous because aiosqlite is optional
    ) -> CachedRole:
        return CachedRole(
            row[0],
            row[1],
            row[2],
            hikari.Color(row[3]),
            row[4],
            hikari.Permissions(row[5]),
            datetime.fromtimestamp(row[6], timezone.utc),
            row[7],
            bool(row[8]),
            hikari.Snowflake(row[9]) if row[9] else None,
            bool(row[10]),
        )
