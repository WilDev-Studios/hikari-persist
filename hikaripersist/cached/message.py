from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from hikaripersist.cached.base import CachedObject
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import hikari

__all__ = ("CachedMessage",)

@dataclass(frozen=True, slots=True)
class CachedMessage(CachedObject):
    """Represents a message in persistent cache."""

    id: hikari.Snowflake
    """The ID of the message."""
    channel_id: hikari.Snowflake
    """The ID of the parent channel."""
    guild_id: hikari.Snowflake
    """The ID of the parent guild."""
    author_id: hikari.Snowflake
    """The ID of the sender."""
    created: datetime
    """The timestamp in which the message was sent."""
    pinned: bool
    """If the message is pinned in the channel."""
    content: str | None
    """If present, any message content."""
    edited: datetime | None
    """If edited, the timestamp in which the message was edited."""

    @classmethod
    def from_sqlite(
        cls: type[CachedMessage],
        row, # noqa: ANN001 - Ambiguous because aiosqlite is optional
    ) -> CachedMessage:
        return cls(
            row[0],
            row[1],
            row[2],
            row[3],
            datetime.fromtimestamp(row[4], timezone.utc),
            bool(row[5]),
            row[6],
            datetime.fromtimestamp(row[7], timezone.utc) if row[7] else None,
        )
