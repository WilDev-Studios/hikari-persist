from __future__ import annotations

from collections.abc import Iterable

import hikari

__all__ = (
    "ChannelRule",
    "GuildRule",
    "MemberRule",
    "MessageRule",
    "RoleRule",
    "Rule",
)

def verify_type(obj: object, type_: type | tuple[type, ...], name: str) -> object:
    """
    Verify that a provided object is an instance of a type.

    Parameters
    ----------
    obj : object
        The object to type check.
    type_ : type | tuple[type, ...]
        The type to check against.
    name : str
        The name of the parameter if errored.

    Returns
    -------
    object
        If passed, the object itself.
    """

    if not isinstance(obj, type_):
        error: str = f"Provided {name} must be {type_}"
        raise TypeError(error)

    return obj

def to_snowflake_set(ids: Iterable[hikari.Snowflakeish] | None, name: str) -> set[hikari.Snowflake]:
    """
    Convert an iterable of `hikari.Snowflakeish` to a set of `hikari.Snowflake`.

    Parameters
    ----------
    ids : Iterable[hikari.Snowflakeish] | None
        If provided, any IDs to convert.
    name : str
        If type erroring, the name of the IDs iterable.

    Returns
    -------
    set[hikari.Snowflake]
        The converted set of IDs.

    Raises
    ------
    TypeError
        If `ids` is not an `Iterable` of `hikari.Snowflakeish`.
    """

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
        channel_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        channel_whitelist: Iterable[hikari.Snowflakeish] | None = None,
        guild_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        guild_whitelist: Iterable[hikari.Snowflakeish] | None = None,
    ) -> None:
        """
        Create a cache channel rule.

        Parameters
        ----------
        channel_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of channels to ignore.
        channel_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all channels except these.
        guild_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of guilds to ignore.
        guild_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.

        Raises
        ------
        TypeError
            If any parameter is provided and is not `Iterable` of `hikari.Snowflakeish`.
        """

        self._channel_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            channel_blacklist,
            "channel_blacklist",
        )
        self._channel_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            channel_whitelist,
            "channel_whitelist",
        )
        self._guild_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            guild_blacklist,
            "guild_blacklist",
        )
        self._guild_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            guild_whitelist,
            "guild_whitelist",
        )

    def can_cache(
        self,
        channel_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
    ) -> bool:
        """
        Return whether a channel passes the rule.
        """

        if channel_id in self._channel_blacklist:
            return False

        if self._channel_whitelist and channel_id not in self._channel_whitelist:
            return False

        if guild_id in self._guild_blacklist:
            return False

        return not (self._guild_whitelist and guild_id not in self._guild_whitelist)

class GuildRule:
    """Guild cache rule."""

    def __init__(
        self,
        *,
        guild_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        guild_whitelist: Iterable[hikari.Snowflakeish] | None = None,
    ) -> None:
        """
        Create a cache guild rule.

        Parameters
        ----------
        guild_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all guilds to ignore.
        guild_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.

        Raises
        ------
        TypeError
            If any parameter is provided and is not `Iterable` of `hikari.Snowflakeish`.
        """

        self._guild_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            guild_blacklist,
            "guild_blacklist",
        )
        self._guild_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            guild_whitelist,
            "guild_whitelist",
        )

    def can_cache(
        self,
        guild_id: hikari.Snowflake,
    ) -> bool:
        """
        Return whether a guild passes the rule.
        """

        if guild_id in self._guild_blacklist:
            return False

        return not (self._guild_whitelist and guild_id not in self._guild_whitelist)

class MemberRule:
    """Member cache rule."""

    def __init__(
        self,
        *,
        guild_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        guild_whitelist: Iterable[hikari.Snowflakeish] | None = None,
        user_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        user_whitelist: Iterable[hikari.Snowflakeish] | None = None,
    ) -> None:
        """
        Create a cache member rule.

        Parameters
        ----------
        guild_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all guilds to ignore.
        guild_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.
        user_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all users to ignore.
        user_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all users except these.

        Raises
        ------
        TypeError
            If any parameter is provided and is not `Iterable` of `hikari.Snowflakeish`.
        """

        self._guild_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            guild_blacklist,
            "guild_blacklist",
        )
        self._guild_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            guild_whitelist,
            "guild_whitelist",
        )
        self._user_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            user_blacklist,
            "user_blacklist",
        )
        self._user_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            user_whitelist,
            "user_whitelist",
        )

    def can_cache(
        self,
        guild_id: hikari.Snowflake,
        user_id: hikari.Snowflake,
    ) -> bool:
        """
        Return whether a member passes the rule.
        """

        if guild_id in self._guild_blacklist:
            return False

        if self._guild_whitelist and guild_id not in self._guild_whitelist:
            return False

        if user_id in self._user_blacklist:
            return False

        return not (self._user_whitelist and user_id not in self._user_whitelist)

class MessageRule:
    """Message cache rule."""

    def __init__( # noqa: PLR0913
        self,
        *,
        channel_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        channel_whitelist: Iterable[hikari.Snowflakeish] | None = None,
        guild_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        guild_whitelist: Iterable[hikari.Snowflakeish] | None = None,
        message_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        message_whitelist: Iterable[hikari.Snowflakeish] | None = None,
        user_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        user_whitelist: Iterable[hikari.Snowflakeish] | None = None,
    ) -> None:
        """
        Create a cache message rule.

        Parameters
        ----------
        channel_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of channels to ignore.
        channel_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all channels except these.
        guild_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of guilds to ignore.
        guild_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.
        message_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of messages to ignore.
        message_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all messages except these.
        user_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of users to ignore.
        user_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all users except these.

        Raises
        ------
        TypeError
            If any parameter is provided and is not `Iterable` of `hikari.Snowflakeish`.
        """

        self._channel_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            channel_blacklist,
            "channel_blacklist",
        )
        self._channel_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            channel_whitelist,
            "channel_whitelist",
        )
        self._guild_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            guild_blacklist,
            "guild_blacklist",
        )
        self._guild_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            guild_whitelist,
            "guild_whitelist",
        )
        self._message_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            message_blacklist,
            "message_blacklist",
        )
        self._message_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            message_whitelist,
            "message_whitelist",
        )
        self._user_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            user_blacklist,
            "user_blacklist",
        )
        self._user_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            user_whitelist,
            "user_whitelist",
        )

    def can_cache( # noqa: PLR0911
        self,
        channel_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
        message_id: hikari.Snowflake,
        user_id: hikari.Snowflake,
    ) -> bool:
        """
        Return whether a message passes the rule.
        """

        if channel_id in self._channel_blacklist:
            return False

        if self._channel_whitelist and channel_id not in self._channel_whitelist:
            return False

        if guild_id in self._guild_blacklist:
            return False

        if self._guild_whitelist and guild_id not in self._guild_whitelist:
            return False

        if message_id in self._message_blacklist:
            return False

        if self._message_whitelist and message_id not in self._message_whitelist:
            return False

        if user_id in self._user_blacklist:
            return False

        return not (self._user_whitelist and user_id not in self._user_whitelist)

class RoleRule:
    """Role cache rule."""

    def __init__(
        self,
        *,
        guild_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        guild_whitelist: Iterable[hikari.Snowflakeish] | None = None,
        role_blacklist: Iterable[hikari.Snowflakeish] | None = None,
        role_whitelist: Iterable[hikari.Snowflakeish] | None = None,
    ) -> None:
        """
        Create a cache role rule.

        Parameters
        ----------
        guild_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all guilds to ignore.
        guild_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all guilds except these.
        role_blacklist : Iterable[hikari.Snowflakeish] | None
            If provided, an iterable of all roles to ignore.
        role_whitelist : Iterable[hikari.Snowflakeish] | None
            If provided, ignore all roles except these.
        """

        self._guild_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            guild_blacklist,
            "guild_blacklist",
        )
        self._guild_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            guild_whitelist,
            "guild_whitelist",
        )
        self._role_blacklist: set[hikari.Snowflake] = to_snowflake_set(
            role_blacklist,
            "role_blacklist",
        )
        self._role_whitelist: set[hikari.Snowflake] = to_snowflake_set(
            role_whitelist,
            "role_whitelist",
        )

    def can_cache(
        self,
        guild_id: hikari.Snowflake,
        role_id: hikari.Snowflake,
    ) -> bool:
        """
        Return whether a role passes the rule.
        """

        if guild_id in self._guild_blacklist:
            return False

        if self._guild_whitelist and guild_id not in self._guild_whitelist:
            return False

        if role_id in self._role_blacklist:
            return False

        return not (self._role_whitelist and role_id not in self._role_whitelist)

class Rule:
    "Cache ruleset."

    def __init__(
        self,
        *,
        channel: ChannelRule | None = None,
        guild: GuildRule | None = None,
        member: MemberRule | None = None,
        message: MessageRule | None = None,
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
        message : MessageRule | None
            If provided, rule regarding message caching.
        role : RoleRule | None
            If provided, rule regarding role caching.

        Raises
        ------
        TypeError
            - If `channel` is provided and is not `ChannelRule`.
            - If `guild` is provided and is not `GuildRule`.
            - If `member` is provided and is not `MemberRule`.
            - If `message` is provided and is not `MessageRule`.
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
        self._message: MessageRule = (
            verify_type(message, MessageRule, "message")
            if message else MessageRule()
        )
        self._role: RoleRule = (
            verify_type(role, RoleRule, "role")
            if role else RoleRule()
        )
