from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import hikari

__all__ = ("CachedMessage",)

@dataclass(frozen=True, slots=True)
class CachedMessage:
    """Represents a message in persistent cache."""

    id: hikari.Snowflake
    channel_id: hikari.Snowflake
    guild_id: hikari.Snowflake | None
    content: str | None
