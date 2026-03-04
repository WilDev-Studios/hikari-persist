from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    import hikari

__all__ = ("CachedGuild",)

@dataclass(frozen=True, slots=True)
class CachedGuild:
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
