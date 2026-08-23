from __future__ import annotations

from collections.abc import (
    Callable,
    Iterable,
)

import hikari


__all__ = (
    "ChannelRule",
    "GuildRule",
    "MemberRule",
    "RoleRule",
    "Rule",
)


def _coerce_snowflakes(
    values: Iterable[hikari.Snowflakeish],
    *,
    param: str,
) -> set[hikari.Snowflake]:
    result: set[hikari.Snowflake] = set()

    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, hikari.Snowflake)):
            error: str = (
                f"{param} must contain only int or hikari.Snowflake elements, "
                f"got {type(v).__name__}: {v!r}"
            )
            raise TypeError(error)

        result.add(hikari.Snowflake(v))

    return result

class ChannelRule:
    """Channel cache rule."""

    def __init__(
        self,
        *,
        channel_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        channel_denylist: Iterable[hikari.Snowflakeish] | None = None,
        guild_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        guild_denylist: Iterable[hikari.Snowflakeish] | None = None,
        predicate: Callable[[hikari.GuildChannel], bool] | None = None,
    ) -> None:
        """
        Create a cache channel rule.

        Parameters
        ----------
        channel_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all channels except these.
        channel_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of channels to ignore.
        guild_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.
        guild_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of guilds to ignore.
        predicate : Callable[[hikari.GuildChannel], bool] | None
            If provided, a predicate method used for advanced, custom filtration of pending
            channels. Returns `True` if the channel should be cached, `False` otherwise.

        Raises
        ------
        TypeError
            If any allowlist/denylist contains a non-Snowflakeish element.
        """

        self._channel_allowlist: set[hikari.Snowflake] = set()
        self._channel_denylist: set[hikari.Snowflake] = set()
        self._guild_allowlist: set[hikari.Snowflake] = set()
        self._guild_denylist: set[hikari.Snowflake] = set()
        self._predicate: Callable[[hikari.GuildChannel], bool] | None = predicate

        if channel_allowlist:
            self._channel_allowlist = _coerce_snowflakes(channel_allowlist, param="channel_allowlist") # noqa: E501
        if channel_denylist:
            self._channel_denylist = _coerce_snowflakes(channel_denylist, param="channel_denylist")
        if guild_allowlist:
            self._guild_allowlist = _coerce_snowflakes(guild_allowlist, param="guild_allowlist")
        if guild_denylist:
            self._guild_denylist = _coerce_snowflakes(guild_denylist, param="guild_denylist")

    def can_cache(
        self,
        channel: hikari.GuildChannel,
    ) -> bool:
        """
        Return whether a channel passes the rule.
        """

        if self._predicate and not self._predicate(channel):
            return False

        if channel.id in self._channel_denylist:
            return False

        if self._channel_allowlist and channel.id not in self._channel_allowlist:
            return False

        if channel.guild_id in self._guild_denylist:
            return False

        if self._guild_allowlist and channel.guild_id not in self._guild_allowlist: # noqa: SIM103
            return False

        return True

class GuildRule:
    """Guild cache rule."""

    def __init__(
        self,
        *,
        guild_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        guild_denylist: Iterable[hikari.Snowflakeish] | None = None,
        predicate: Callable[[hikari.Guild], bool] | None = None,
    ) -> None:
        """
        Create a cache guild rule.

        Parameters
        ----------
        guild_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.
        guild_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all guilds to ignore.
        predicate : Callable[[hikari.Guild], bool] | None
            If provided, a predicate method used for advanced, custom filtration of pending
            guilds. Returns `True` if the guild should be cached, `False` otherwise.

        Raises
        ------
        TypeError
            If any allowlist/denylist contains a non-Snowflakeish element.
        """

        self._guild_allowlist: set[hikari.Snowflake] = set()
        self._guild_denylist: set[hikari.Snowflake] = set()
        self._predicate: Callable[[hikari.Guild], bool] | None = predicate

        if guild_allowlist:
            self._guild_allowlist = _coerce_snowflakes(guild_allowlist, param="guild_allowlist")
        if guild_denylist:
            self._guild_denylist = _coerce_snowflakes(guild_denylist, param="guild_denylist")

    def can_cache(
        self,
        guild: hikari.Guild,
    ) -> bool:
        """
        Return whether a guild passes the rule.
        """

        if self._predicate and not self._predicate(guild):
            return False

        if guild.id in self._guild_denylist:
            return False

        if self._guild_allowlist and guild.id not in self._guild_allowlist: # noqa: SIM103
            return False

        return True

class MemberRule:
    """Member cache rule."""

    def __init__(
        self,
        *,
        guild_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        guild_denylist: Iterable[hikari.Snowflakeish] | None = None,
        user_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        user_denylist: Iterable[hikari.Snowflakeish] | None = None,
        predicate: Callable[[hikari.Member], bool] | None = None,
    ) -> None:
        """
        Create a cache member rule.

        Parameters
        ----------
        guild_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.
        guild_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all guilds to ignore.
        user_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all users except these.
        user_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all users to ignore.
        predicate : Callable[[hikari.Member], bool] | None
            If provided, a predicate method used for advanced, custom filtration of pending
            members. Returns `True` if the member should be cached, `False` otherwise.

        Raises
        ------
        TypeError
            If any allowlist/denylist contains a non-Snowflakeish element.
        """

        self._guild_allowlist: set[hikari.Snowflake] = set()
        self._guild_denylist: set[hikari.Snowflake] = set()
        self._user_allowlist: set[hikari.Snowflake] = set()
        self._user_denylist: set[hikari.Snowflake] = set()
        self._predicate: Callable[[hikari.Member], bool] | None = predicate

        if guild_allowlist:
            self._guild_allowlist = _coerce_snowflakes(guild_allowlist, param="guild_allowlist")
        if guild_denylist:
            self._guild_denylist = _coerce_snowflakes(guild_denylist, param="guild_denylist")
        if user_allowlist:
            self._user_allowlist = _coerce_snowflakes(user_allowlist, param="user_allowlist")
        if user_denylist:
            self._user_denylist = _coerce_snowflakes(user_denylist, param="user_denylist")

    def can_cache(
        self,
        member: hikari.Member,
    ) -> bool:
        """
        Return whether a member passes the rule.
        """

        if self._predicate and not self._predicate(member):
            return False

        if member.guild_id in self._guild_denylist:
            return False

        if self._guild_allowlist and member.guild_id not in self._guild_allowlist:
            return False

        if member.id in self._user_denylist:
            return False

        if self._user_allowlist and member.id not in self._user_allowlist: # noqa: SIM103
            return False

        return True

class RoleRule:
    """Role cache rule."""

    def __init__(
        self,
        *,
        guild_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        guild_denylist: Iterable[hikari.Snowflakeish] | None = None,
        role_allowlist: Iterable[hikari.Snowflakeish] | None = None,
        role_denylist: Iterable[hikari.Snowflakeish] | None = None,
        predicate: Callable[[hikari.Role], bool] | None = None,
    ) -> None:
        """
        Create a cache role rule.

        Parameters
        ----------
        guild_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.
        guild_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all guilds to ignore.
        role_allowlist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all roles except these.
        role_denylist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all roles to ignore.
        predicate : Callable[[hikari.Role], bool] | None
            If provided, a predicate method used for advanced, custom filtration of pending
            roles. Returns `True` if the role should be cached, `False` otherwise.

        Raises
        ------
        TypeError
            If any allowlist/denylist contains a non-Snowflakeish element.
        """

        self._guild_allowlist: set[hikari.Snowflake] = set()
        self._guild_denylist: set[hikari.Snowflake] = set()
        self._role_allowlist: set[hikari.Snowflake] = set()
        self._role_denylist: set[hikari.Snowflake] = set()
        self._predicate: Callable[[hikari.Role], bool] | None = predicate

        if guild_allowlist:
            self._guild_allowlist = _coerce_snowflakes(guild_allowlist, param="guild_allowlist")
        if guild_denylist:
            self._guild_denylist = _coerce_snowflakes(guild_denylist, param="guild_denylist")
        if role_allowlist:
            self._role_allowlist = _coerce_snowflakes(role_allowlist, param="role_allowlist")
        if role_denylist:
            self._role_denylist = _coerce_snowflakes(role_denylist, param="role_denylist")

    def can_cache(
        self,
        role: hikari.Role,
    ) -> bool:
        """
        Return whether a role passes the rule.
        """

        if self._predicate and not self._predicate(role):
            return False

        if role.guild_id in self._guild_denylist:
            return False

        if self._guild_allowlist and role.guild_id not in self._guild_allowlist:
            return False

        if role.id in self._role_denylist:
            return False

        if self._role_allowlist and role.id not in self._role_allowlist: # noqa: SIM103
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

        if channel is not None and not isinstance(channel, ChannelRule):
            raise TypeError(f"channel must be a ChannelRule, got {type(channel).__name__}")
        if guild is not None and not isinstance(guild, GuildRule):
            raise TypeError(f"guild must be a GuildRule, got {type(guild).__name__}")
        if member is not None and not isinstance(member, MemberRule):
            raise TypeError(f"member must be a MemberRule, got {type(member).__name__}")
        if role is not None and not isinstance(role, RoleRule):
            raise TypeError(f"role must be a RoleRule, got {type(role).__name__}")

        self._channel: ChannelRule = channel or ChannelRule()
        self._guild: GuildRule = guild or GuildRule()
        self._member: MemberRule = member or MemberRule()
        self._role: RoleRule = role or RoleRule()
