from __future__ import annotations

from typing import (
    Any,
    TYPE_CHECKING,
)
from ..internal.query import (
    ChannelQuery,
    MemberQuery,
    RoleQuery,
)

import hikari

if TYPE_CHECKING:
    from ..impl.cache import Cache


__all__ = (
    "PersistentGuild",
    "PersistentGuildCategory",
    "PersistentGuildChannel",
    "PersistentGuildForumChannel",
    "PersistentGuildMediaChannel",
    "PersistentGuildNewsChannel",
    "PersistentGuildNewsThread",
    "PersistentGuildPrivateThread",
    "PersistentGuildPublicThread",
    "PersistentGuildStageChannel",
    "PersistentGuildTextChannel",
    "PersistentGuildVoiceChannel",
    "PersistentMember",
    "PersistentRole",
)

class _PersistentChannelMixin:
    def __init__(self, cache: Cache, **kwargs: Any) -> None: # noqa: ANN401
        super().__init__(app=cache._bot, **kwargs)

        self._cache: Cache = cache

    async def resolve_guild(self, *, fetch_if_missing: bool = False) -> PersistentGuild | None:
        """
        Resolve the guild directly tied to this channel from the cache
        and optionally fetch it from Discord if not found.

        Parameters
        ----------
        fetch_if_missing : bool
            If not found in cache, automatically fetch it from REST.

        Returns
        -------
        PersistentGuild | None
            The fetched guild from cache or REST, if found.

        Note
        ----
        The listed exceptions are only raised when fetch_if_missing=True.

        Raises
        ------
        hikari.ForbiddenError
            Not in the guild.
        hikari.InternalServerError
            Discord had an issue while handling the request.
        hikari.NotFoundError
            Guild wasn't found.
        hikari.RateLimitTooLongError
            Rate limit occurred longer than bot max_rate_limit upon request.
        hikari.UnauthorizedError
            Request unauthorized (invalid/missing token).
        """

        return await self._cache.guilds.get(
            id=self.guild_id,
            fetch_if_missing=fetch_if_missing,
        )

class PersistentGuildCategory(_PersistentChannelMixin, hikari.GuildCategory):...
class PersistentGuildChannel(_PersistentChannelMixin, hikari.GuildChannel):...
class PersistentGuildForumChannel(_PersistentChannelMixin, hikari.GuildForumChannel):...
class PersistentGuildMediaChannel(_PersistentChannelMixin, hikari.GuildMediaChannel):...
class PersistentGuildNewsChannel(_PersistentChannelMixin, hikari.GuildNewsChannel):...
class PersistentGuildNewsThread(_PersistentChannelMixin, hikari.GuildNewsThread):...
class PersistentGuildPrivateThread(_PersistentChannelMixin, hikari.GuildPrivateThread):...
class PersistentGuildPublicThread(_PersistentChannelMixin, hikari.GuildPublicThread):...
class PersistentGuildStageChannel(_PersistentChannelMixin, hikari.GuildStageChannel):...
class PersistentGuildTextChannel(_PersistentChannelMixin, hikari.GuildTextChannel):...
class PersistentGuildVoiceChannel(_PersistentChannelMixin, hikari.GuildVoiceChannel):...

class PersistentGuild(hikari.Guild):
    def __init__(self, cache: Cache, **kwargs: Any) -> None: # noqa: ANN401
        super().__init__(app=cache._bot, **kwargs)

        self._cache: Cache = cache

    @property
    def channels(self) -> ChannelQuery:
        return ChannelQuery(self._cache, guild_id=self.id)

    @property
    def members(self) -> MemberQuery:
        return MemberQuery(self._cache, guild_id=self.id)

    @property
    def roles(self) -> RoleQuery:
        return RoleQuery(self._cache, guild_id=self.id)

class PersistentMember(hikari.Member):
    def __init__(self, cache: Cache, **kwargs: Any) -> None: # noqa: ANN401
        super().__init__(**kwargs)

        self._cache: Cache = cache

    async def resolve_guild(self, *, fetch_if_missing: bool = False) -> PersistentGuild | None:
        """
        Resolve the guild directly tied to this member from the cache
        and optionally fetch it from Discord if not found.

        Parameters
        ----------
        fetch_if_missing : bool
            If not found in cache, automatically fetch it from REST.

        Returns
        -------
        PersistentGuild | None
            The fetched guild from cache or REST, if found.

        Note
        ----
        The listed exceptions are only raised when fetch_if_missing=True.

        Raises
        ------
        hikari.ForbiddenError
            Not in the guild.
        hikari.InternalServerError
            Discord had an issue while handling the request.
        hikari.NotFoundError
            Guild wasn't found.
        hikari.RateLimitTooLongError
            Rate limit occurred longer than bot max_rate_limit upon request.
        hikari.UnauthorizedError
            Request unauthorized (invalid/missing token).
        """

        return await self._cache.guilds.get(
            id=self.guild_id,
            fetch_if_missing=fetch_if_missing,
        )

class PersistentRole(hikari.Role):
    def __init__(self, cache: Cache, **kwargs: Any) -> None: # noqa: ANN401
        super().__init__(app=cache._bot, **kwargs)

        self._cache: Cache = cache

    async def resolve_guild(self, *, fetch_if_missing: bool = False) -> PersistentGuild | None:
        """
        Resolve the guild directly tied to this role from the cache
        and optionally fetch it from Discord if not found.

        Parameters
        ----------
        fetch_if_missing : bool
            If not found in cache, automatically fetch it from REST.

        Returns
        -------
        PersistentGuild | None
            The fetched guild from cache or REST, if found.

        Note
        ----
        The listed exceptions are only raised when fetch_if_missing=True.

        Raises
        ------
        hikari.ForbiddenError
            Not in the guild.
        hikari.InternalServerError
            Discord had an issue while handling the request.
        hikari.NotFoundError
            Guild wasn't found.
        hikari.RateLimitTooLongError
            Rate limit occurred longer than bot max_rate_limit upon request.
        hikari.UnauthorizedError
            Request unauthorized (invalid/missing token).
        """

        return await self._cache.guilds.get(
            id=self.guild_id,
            fetch_if_missing=fetch_if_missing,
        )
