from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    import hikari

__all__ = ("CachedMember",)

@dataclass(frozen=True, slots=True)
class CachedMember:
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
