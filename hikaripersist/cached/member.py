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

__all__ = ("CachedMember",)

@dataclass(frozen=True, slots=True)
class CachedMember(CachedObject):
    """Represents a member in persistent cache."""

    id: hikari.Snowflake
    """The ID of the member."""
    guild_id: hikari.Snowflake
    """The ID of the bounded guild."""
    username: str
    """The username of the member."""
    discriminator: str
    """The discriminator of the member."""
    created: datetime
    """The timestamp in which the member created their account."""
    joined: datetime
    """The timestamp in which the member joined the guild."""
    nickname: str | None
    """The nickname of the member, if present."""
    roles: set[hikari.Snowflake]
    """All IDs of each role given to the member."""

    @classmethod
    def from_sqlite(
        cls: type[CachedMember],
        row: aiosqlite.Row,
    ) -> CachedMember:
        return cls(
            row[0],
            row[1],
            row[2],
            row[3],
            datetime.fromtimestamp(row[4], timezone.utc),
            datetime.fromtimestamp(row[5], timezone.utc),
            row[6],
            {hikari.Snowflake(role) for role in row[7].split(',')} if row[7] else set(),
        )
