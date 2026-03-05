from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from hikaripersist.cached.base import CachedObject

import hikari

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
    avatar: hikari.URL
    """The member's display avatar URL."""
    banner: hikari.URL | None
    """If present, the member's display banner URL."""
    name: str
    """The member's display name (nickname > global name > username)."""
    flags: hikari.UserFlag
    """All member account flags."""
    bot: bool
    """If the member is a bot."""
    system: bool
    """If the member is a system user."""
    roles: set[hikari.Snowflake]
    """All IDs of each role given to the member."""
    premium_since: datetime | None
    """If guild boosting, the timestamp at which the member started boosting."""
    timeout: datetime | None
    """If timed out, the timestamp in which it ends."""

    @classmethod
    def from_sqlite(
        cls: type[CachedMember],
        row, # noqa: ANN001 - Ambiguous because aiosqlite is optional
    ) -> CachedMember:
        return cls(
            row[0],
            row[1],
            row[2],
            row[3],
            datetime.fromtimestamp(row[4], timezone.utc),
            datetime.fromtimestamp(row[5], timezone.utc),
            hikari.URL(row[6]),
            hikari.URL(row[7]) if row[7] else None,
            row[8],
            hikari.UserFlag(row[9]),
            bool(row[10]),
            bool(row[11]),
            {hikari.Snowflake(role) for role in row[12].split(',')} if row[12] else set(),
            datetime.fromtimestamp(row[13], timezone.utc) if row[13] else None,
            datetime.fromtimestamp(row[14], timezone.utc) if row[14] else None,
        )
