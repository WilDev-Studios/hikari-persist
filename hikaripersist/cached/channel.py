from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    import hikari

__all__ = (
    "CachedChannel",
    "CachedPermissionOverwrite",
)

@dataclass(frozen=True, slots=True)
class CachedChannel:
    """Represents a guild channel in persistent cache."""

    id: hikari.Snowflake
    """The ID of the channel."""
    guild_id: hikari.Snowflake
    """The ID of the channel's guild."""
    category: hikari.Snowflake | None
    """The ID of the parent channel/category, if one exists."""
    type: hikari.ChannelType
    """The type of the channel."""
    created: datetime
    """The timestamp in which the channel was created."""
    name: str
    """The name of the channel."""
    is_nsfw: bool
    """If the channel is marked as NSFW."""
    position: int
    """The position of the channel."""
    topic: str | None
    """The topic of the channel."""
    permission_overwrites: Mapping[hikari.Snowflake, CachedPermissionOverwrite]
    """Any overwriting permissions of the channel, if they exist."""

@dataclass(frozen=True, slots=True)
class CachedPermissionOverwrite:
    """Represents a guild channel permission overwrite."""

    channel_id: hikari.Snowflake
    """The ID of the channel."""
    target_id: hikari.Snowflake
    """The ID of the target (member or role)."""
    type: hikari.PermissionOverwriteType
    """The type of permission overwrite."""
    allow: hikari.Permissions
    """The allowed permissions in the overwrite."""
    deny: hikari.Permissions
    """The denied permissions in the overwrite."""
