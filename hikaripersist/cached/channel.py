from __future__ import annotations

from collections.abc import Mapping
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

__all__ = (
    "CachedChannel",
    "CachedPermissionOverwrite",
)

@dataclass(frozen=True, slots=True)
class CachedChannel(CachedObject):
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

    @classmethod
    def from_sqlite(
        cls: type[CachedChannel],
        row: aiosqlite.Row,
        overwrites: Mapping[hikari.Snowflake, CachedPermissionOverwrite],
    ) -> CachedChannel:
        return CachedChannel(
            row[0],
            row[1],
            row[2],
            hikari.ChannelType(row[3]),
            datetime.fromtimestamp(row[4], timezone.utc),
            row[5],
            bool(row[6]) if row[6] is not None else None,
            row[7],
            row[8],
            overwrites,
        )

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

    @classmethod
    def from_sqlite(
        cls: type[CachedPermissionOverwrite],
        row: aiosqlite.Row,
    ) -> CachedPermissionOverwrite:
        return cls(
            row[0],
            row[1],
            hikari.PermissionOverwriteType(row[2]),
            hikari.Permissions(row[3]),
            hikari.Permissions(row[4]),
        )
