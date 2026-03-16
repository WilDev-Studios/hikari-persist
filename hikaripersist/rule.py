from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

import hikari

__all__ = (
    "ChannelRule",
    "GuildRule",
    "MemberRule",
    "RoleRule",
    "Rule",
)

_T = TypeVar("_T")

def verify_type(obj: object, type_: type[_T] | tuple[type[_T], ...], name: str) -> _T:
    if not isinstance(obj, type_):
        error: str = f"Provided {name} must be {type_}"
        raise TypeError(error)

    return obj

def to_snowflake_set(ids: Iterable[hikari.Snowflakeish] | None, name: str) -> set[hikari.Snowflake]:
    if ids is None:
        return set()

    ids: Iterable[hikari.Snowflakeish] = verify_type(ids, Iterable, name)

    final: set[hikari.Snowflake] = set()
    for id_ in ids:
        final.add(verify_type(id_, hikari.Snowflakeish, f"{name} ID"))

    return final

class ChannelRule:
    """Channel cache rule."""

    def __init__(
        self,
        *,
        channel_denylist: Iterable[hikari.Snowflakeish] | None = None,
        channel_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        guild_denylist: Iterable[hikari.Snowflakeish] | None = None,
        guild_allowlist: Iterable[hikari.Snowflakeish] | None = None,
    ) -> None:
        """
        Create a cache channel rule.

        Parameters
        ----------
        channel_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of channels to ignore.
        channel_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all channels except these.
        guild_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of guilds to ignore.
        guild_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.

        Raises
        ------
        TypeError
            If any parameter is provided and is not `Iterable` of `hikari.Snowflakeish`.
        """

        self._channel_denylist: set[hikari.Snowflake] = to_snowflake_set(
            channel_denylist,
            "channel_denylist",
        )
        self._channel_allowlist: set[hikari.Snowflake] = to_snowflake_set(
            channel_allowlist,
            "channel_allowlist",
        )
        self._guild_denylist: set[hikari.Snowflake] = to_snowflake_set(
            guild_denylist,
            "guild_denylist",
        )
        self._guild_allowlist: set[hikari.Snowflake] = to_snowflake_set(
            guild_allowlist,
            "guild_allowlist",
        )

    def can_cache(
        self,
        channel_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
    ) -> bool:
        """
        Return whether a channel passes the rule.
        """

        if channel_id in self._channel_denylist:
            return False

        if self._channel_allowlist and channel_id not in self._channel_allowlist:
            return False

        if guild_id in self._guild_denylist:
            return False

        if self._guild_allowlist and guild_id not in self._guild_allowlist: # noqa: SIM103
            return False

        return True

class GuildRule:
    """Guild cache rule."""

    def __init__(
        self,
        *,
        guild_denylist: Iterable[hikari.Snowflakeish] | None = None,
        guild_allowlist: Iterable[hikari.Snowflakeish] | None = None,
    ) -> None:
        """
        Create a cache guild rule.

        Parameters
        ----------
        guild_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all guilds to ignore.
        guild_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.

        Raises
        ------
        TypeError
            If any parameter is provided and is not `Iterable` of `hikari.Snowflakeish`.
        """

        self._guild_denylist: set[hikari.Snowflake] = to_snowflake_set(
            guild_denylist,
            "guild_denylist",
        )
        self._guild_allowlist: set[hikari.Snowflake] = to_snowflake_set(
            guild_allowlist,
            "guild_allowlist",
        )

    def can_cache(
        self,
        guild_id: hikari.Snowflake,
    ) -> bool:
        """
        Return whether a guild passes the rule.
        """

        if guild_id in self._guild_denylist:
            return False

        if self._guild_allowlist and guild_id not in self._guild_allowlist: # noqa: SIM103
            return False

        return True

class MemberRule:
    """Member cache rule."""

    def __init__(
        self,
        *,
        guild_denylist: Iterable[hikari.Snowflakeish] | None = None,
        guild_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        user_denylist: Iterable[hikari.Snowflakeish] | None = None,
        user_allowlist: Iterable[hikari.Snowflakeish] | None = None,
    ) -> None:
        """
        Create a cache member rule.

        Parameters
        ----------
        guild_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all guilds to ignore.
        guild_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.
        user_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all users to ignore.
        user_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all users except these.

        Raises
        ------
        TypeError
            If any parameter is provided and is not `Iterable` of `hikari.Snowflakeish`.
        """

        self._guild_denylist: set[hikari.Snowflake] = to_snowflake_set(
            guild_denylist,
            "guild_denylist",
        )
        self._guild_allowlist: set[hikari.Snowflake] = to_snowflake_set(
            guild_allowlist,
            "guild_allowlist",
        )
        self._user_denylist: set[hikari.Snowflake] = to_snowflake_set(
            user_denylist,
            "user_denylist",
        )
        self._user_allowlist: set[hikari.Snowflake] = to_snowflake_set(
            user_allowlist,
            "user_allowlist",
        )

    def can_cache(
        self,
        guild_id: hikari.Snowflake,
        user_id: hikari.Snowflake,
    ) -> bool:
        """
        Return whether a member passes the rule.
        """

        if guild_id in self._guild_denylist:
            return False

        if self._guild_allowlist and guild_id not in self._guild_allowlist:
            return False

        if user_id in self._user_denylist:
            return False

        if self._user_allowlist and user_id not in self._user_allowlist: # noqa: SIM103
            return False

        return True

class RoleRule:
    """Role cache rule."""

    def __init__(
        self,
        *,
        guild_denylist: Iterable[hikari.Snowflakeish] | None = None,
        guild_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        role_denylist: Iterable[hikari.Snowflakeish] | None = None,
        role_allowlist: Iterable[hikari.Snowflakeish] | None = None,
    ) -> None:
        """
        Create a cache role rule.

        Parameters
        ----------
        guild_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all guilds to ignore.
        guild_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.
        role_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all roles to ignore.
        role_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all roles except these.
        """

        self._guild_denylist: set[hikari.Snowflake] = to_snowflake_set(
            guild_denylist,
            "guild_denylist",
        )
        self._guild_allowlist: set[hikari.Snowflake] = to_snowflake_set(
            guild_allowlist,
            "guild_allowlist",
        )
        self._role_denylist: set[hikari.Snowflake] = to_snowflake_set(
            role_denylist,
            "role_denylist",
        )
        self._role_allowlist: set[hikari.Snowflake] = to_snowflake_set(
            role_allowlist,
            "role_allowlist",
        )

    def can_cache(
        self,
        guild_id: hikari.Snowflake,
        role_id: hikari.Snowflake,
    ) -> bool:
        """
        Return whether a role passes the rule.
        """

        if guild_id in self._guild_denylist:
            return False

        if self._guild_allowlist and guild_id not in self._guild_allowlist:
            return False

        if role_id in self._role_denylist:
            return False

        if self._role_allowlist and role_id not in self._role_allowlist: # noqa: SIM103
            return False

        return True

class Rule:
    """Cache ruleset."""

    def __init__(
        self,
        *,
        channel: ChannelRule | None = None,
        guild: GuildRule | None = None,
        member: MemberRule | None = None,
        role: RoleRule | None = None,
    ) -> None:
        """
        Create a cache rule.

        Parameters
        ----------
        channel : ChannelRule | None
            If provided, rule regarding channel caching.
        guild : GuildRule | None
            If provided, rule regarding guild caching.
        member : MemberRule | None
            If provided, rule regarding member caching.
        role : RoleRule | None
            If provided, rule regarding role caching.

        Raises
        ------
        TypeError
            - If `channel` is provided and is not `ChannelRule`.
            - If `guild` is provided and is not `GuildRule`.
            - If `member` is provided and is not `MemberRule`.
            - If `role` is provided and is not `RoleRule`.
        """

        self._channel: ChannelRule = (
            verify_type(channel, ChannelRule, "channel")
            if channel else ChannelRule()
        )
        self._guild: GuildRule = (
            verify_type(guild, GuildRule, "guild")
            if guild else GuildRule()
        )
        self._member: MemberRule = (
            verify_type(member, MemberRule, "member")
            if member else MemberRule()
        )
        self._role: RoleRule = (
            verify_type(role, RoleRule, "role")
            if role else RoleRule()
        )
