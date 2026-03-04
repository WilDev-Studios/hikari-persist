from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    import hikari

__all__ = ("CachedRole",)

@dataclass(frozen=True, slots=True)
class CachedRole:
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
