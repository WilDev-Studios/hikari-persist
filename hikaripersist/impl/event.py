from __future__ import annotations

from dataclasses import dataclass

import hikari

__all__ = (
    "BulkChannelEvent",
    "BulkMemberEvent",
    "BulkRoleEvent",
    "ChannelInsertEvent",
    "ChannelRemoveEvent",
    "ChannelUpdateEvent",
    "GuildInsertEvent",
    "GuildRemoveEvent",
    "GuildUpdateEvent",
    "MemberInsertEvent",
    "MemberRemoveEvent",
    "MemberUpdateEvent",
    "PersistEvent",
    "RoleInsertEvent",
    "RoleRemoveEvent",
    "RoleUpdateEvent",
)

class PersistEvent(hikari.Event):
    """Base event for all persistent cache-related events."""

    @property
    def app(self) -> hikari.RESTAware:
        return super().app

@dataclass(frozen=True, kw_only=True, slots=True)
class PersistObjectEvent(PersistEvent):
    """Base event for all persistent cache-related events that can pass/fail a rule."""

    successful: bool
    """
    If the object's operation was successful.
    `True` is passed custom rules/filters, otherwise `False`.
    Will always be `True` for `~RemoveEvent`.
    """


@dataclass(frozen=True, kw_only=True, slots=True)
class BulkChannelEvent(PersistEvent):
    """
    Dispatched when an array of channels are attempted to be manipulated in the cache.
    Inserts, removals, and updates may occur on any one channel in this event depending on it's
    status in the cache and on Discord's end.
    """

    failed: set[hikari.GuildChannel]
    """All channels that failed to pass channel rules/filters."""
    guild: hikari.Guild
    """The guild that the channels belong to."""
    passed: set[hikari.GuildChannel]
    """All channels that succeeded in passing channel rules/filters."""

@dataclass(frozen=True, kw_only=True, slots=True)
class BulkMemberEvent(PersistEvent):
    """
    Dispatched when an array of members are attempted to be manipulated in the cache.
    Inserts, removals, and updates may occur on any one member in this event depending on it's
    status in the cache and on Discord's end.
    """

    failed: set[hikari.Member]
    """All members that failed to pass member rules/filters."""
    guild_id: hikari.Snowflake
    """The ID of the guild that the members belong to."""
    passed: set[hikari.Member]
    """All members that succeeded in passing channel rules/filters."""

@dataclass(frozen=True, kw_only=True, slots=True)
class BulkRoleEvent(PersistEvent):
    """
    Dispatched when an array of roles are attempted to be manipulated in the cache.
    Inserts, removals, and updates may occur on any one role in this event depending on it's
    status in the cache and on Discord's end.
    """

    failed: set[hikari.Role]
    """All roles that failed to pass role rules/filters."""
    guild: hikari.Guild
    """The guild that the roles belong to."""
    passed: set[hikari.Role]
    """All roles that succeeded in passing role rules/filters."""


@dataclass(frozen=True, kw_only=True, slots=True)
class ChannelInsertEvent(PersistObjectEvent):
    """
    Dispatched when a channel is attempted to be inserted into the cache.
    """

    channel: hikari.GuildChannel
    """The channel that was attempted to be inserted into the cache."""

@dataclass(frozen=True, kw_only=True, slots=True)
class ChannelRemoveEvent(PersistObjectEvent):
    """
    Dispatched when a channel is attempted to be removed from the cache.
    """

    channel_id: hikari.Snowflake
    """The ID of the channel that was attempted to be removed from the cache."""
    guild_id: hikari.Snowflake
    """The ID of the guild the channel belongs to."""
    successful: bool = True
    """
    If the object's operation was successful.
    `True` is passed custom rules/filters, otherwise `False`.
    Will always be `True` for `~RemoveEvent`.
    """

@dataclass(frozen=True, kw_only=True, slots=True)
class ChannelUpdateEvent(PersistObjectEvent):
    """
    Dispatched when a channel is attempted to be updated in the cache.
    """

    channel: hikari.GuildChannel
    """The channel that was attempted to be updated in the cache."""


@dataclass(frozen=True, kw_only=True, slots=True)
class GuildInsertEvent(PersistObjectEvent):
    """
    Dispatched when a guild is attempted to be inserted into the cache.
    """

    guild: hikari.Guild
    """The guild that was attempted to be inserted into the cache."""

@dataclass(frozen=True, kw_only=True, slots=True)
class GuildRemoveEvent(PersistObjectEvent):
    """
    Dispatched when a guild is attempted to be removed from the cache.
    """

    guild_id: hikari.Snowflake
    """The ID of the guild that was attempted to be removed from the cache."""
    successful: bool = True
    """
    If the object's operation was successful.
    `True` is passed custom rules/filters, otherwise `False`.
    Will always be `True` for `~RemoveEvent`.
    """

@dataclass(frozen=True, kw_only=True, slots=True)
class GuildUpdateEvent(PersistObjectEvent):
    """
    Dispatched when a guild is attempted to be updated in the cache.

    Also fired for the guild in the `GUILD_AVAILABLE` event.
    """

    guild: hikari.Guild
    """The guild that was attempted to be updated in the cache."""


@dataclass(frozen=True, kw_only=True, slots=True)
class MemberInsertEvent(PersistObjectEvent):
    """
    Dispatched when a member is attempted to be inserted into the cache.
    """

    member: hikari.Member
    """The member that was attempted to be inserted into the cache."""

@dataclass(frozen=True, kw_only=True, slots=True)
class MemberRemoveEvent(PersistObjectEvent):
    """
    Dispatched when a member is attempted to be removed from the cache.
    """

    guild_id: hikari.Snowflake
    """The ID of the guild the member was in."""
    user: hikari.User
    """The user of the member that was attempted to be removed from the cache."""
    successful: bool = True
    """
    If the object's operation was successful.
    `True` is passed custom rules/filters, otherwise `False`.
    Will always be `True` for `~RemoveEvent`.
    """

@dataclass(frozen=True, kw_only=True, slots=True)
class MemberUpdateEvent(PersistObjectEvent):
    """
    Dispatched when a member is attempted to be updated in the cache.
    """

    member: hikari.Member
    """The member that was attempted to be updated in the cache."""


@dataclass(frozen=True, kw_only=True, slots=True)
class RoleInsertEvent(PersistObjectEvent):
    """
    Dispatched when a role is attempted to be inserted into the cache.
    """

    role: hikari.Role
    """The role that was attempted to be inserted into the cache."""

@dataclass(frozen=True, kw_only=True, slots=True)
class RoleRemoveEvent(PersistObjectEvent):
    """
    Dispatched when a role is attempted to be removed from the cache.
    """

    guild_id: hikari.Snowflake
    """The ID of the guild the role was in."""
    role_id: hikari.Snowflake
    """The ID of the role that was attempted to be removed from the cache."""
    successful: bool = True
    """
    If the object's operation was successful.
    `True` is passed custom rules/filters, otherwise `False`.
    Will always be `True` for `~RemoveEvent`.
    """

@dataclass(frozen=True, kw_only=True, slots=True)
class RoleUpdateEvent(PersistObjectEvent):
    """
    Dispatched when a role is attempted to be updated in the cache.
    """

    role: hikari.Role
    """The role that was attempted to be updated in the cache."""
