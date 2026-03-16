from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import (
    AsyncIterator,
    Iterable,
)
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from hikaripersist.cache import Cache
    from hikaripersist.impl.query import (
        ChannelQuery,
        GuildQuery,
        MemberQuery,
        RoleQuery,
    )

    import asyncio
    import hikari

__all__ = ("Backend",)

class Backend(ABC):
    """Base persistent cache backend."""

    _cache: Cache

    @abstractmethod
    async def channel_create(
        self,
        channel: hikari.GuildChannel,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Store a created channel.

        Parameters
        ----------
        channel : hikari.GuildChannel
            The created channel to store.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def channel_delete(
        self,
        channel_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Remove a deleted channel.

        Parameters
        ----------
        channel_id : hikari.Snowflake
            The ID of the channel that was deleted.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def channel_update(
        self,
        channel: hikari.GuildChannel,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Update an updated channel.

        Parameters
        ----------
        channel : hikari.GuildChannel
            The updated channel to update.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def connect(
        self,
        *args: tuple,
        **kwargs: dict[str, Any],
    ) -> None:
        """
        Establish a connection with the backend database and initialize.
        """

    @abstractmethod
    async def disconnect(
        self,
        *args: tuple,
        **kwargs: dict[str, Any],
    ) -> None:
        """
        Save state and disconnect from a backend database.
        """

    @abstractmethod
    async def guild_join(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Store a joined guild.

        Parameters
        ----------
        guild : hikari.GatewayGuild
            The guild that was joined.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def guild_leave(
        self,
        guild_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Remove a left guild.

        Parameters
        ----------
        guild_id : hikari.Snowflake
            The ID of the guild that was left.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def guild_update(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Update an updated guild.

        Parameters
        ----------
        guild : hikari.GatewayGuild
            The updated guild to update.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def iter_channels(
        self,
        query: ChannelQuery,
    ) -> AsyncIterator[hikari.GuildChannel]:
        """
        Iterate through all channels in a query.

        Parameters
        ----------
        query : ChannelQuery
            The channel query used in cache lookup.

        Returns
        -------
        AsyncIterator[hikari.GuildChannel]
            The async iterator containing the queried channels.
        """

    @abstractmethod
    async def iter_guilds(
        self,
        query: GuildQuery,
    ) -> AsyncIterator[hikari.Guild]:
        """
        Iterate through all guilds in a query.

        Parameters
        ----------
        query : GuildQuery
            The guild query used in cache lookup.

        Returns
        -------
        AsyncIterator[hikari.Guild]
            The async iterator containing the queried guilds.
        """

    @abstractmethod
    async def iter_members(
        self,
        query: MemberQuery,
    ) -> AsyncIterator[hikari.Member]:
        """
        Iterate through all members in a query.

        Parameters
        ----------
        query : GuildQuery
            The member query used in cache lookup.

        Returns
        -------
        AsyncIterator[hikari.Member]
            The async iterator containing the queried members.
        """

    @abstractmethod
    async def iter_roles(
        self,
        query: RoleQuery,
    ) -> AsyncIterator[hikari.Role]:
        """
        Iterate through all roles in a query.

        Parameters
        ----------
        query : RoleQuery
            The role query used in cache lookup.

        Returns
        -------
        AsyncIterator[hikari.Role]
            The async iterator containing the queried roles.
        """

    @abstractmethod
    async def member_create(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Store a created member.

        Parameters
        ----------
        member : hikari.Member
            The created member to store.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def member_delete(
        self,
        user_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Remove a deleted member.

        Parameters
        ----------
        user_id : hikari.Snowflake
            The ID of the user that left/was deleted.
        guild_id : hikari.Snowflake
            The ID of the guild that the user left.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def member_update(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Update an updated member.

        Parameters
        ----------
        member : hikari.Member
            The updated member to update.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def role_create(
        self,
        role: hikari.Role,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Store a created role.

        Parameters
        ----------
        role : hikari.Role
            The created role to store.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def role_delete(
        self,
        role_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Remove a deleted role.

        Parameters
        ----------
        role_id : hikari.Snowflake
            The ID of the role that was deleted.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def role_update(
        self,
        role: hikari.Role,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Update an updated role.

        Parameters
        ----------
        role : hikari.Role
            The updated role to update.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def startup_guild(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Cache a guild on startup.

        Parameters
        ----------
        guild : hikari.GatewayGuild
            The guild to cache.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def startup_guild_channels(
        self,
        channels: Iterable[hikari.GuildChannel],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Cache channels on startup.

        Parameters
        ----------
        channels : Iterable[hikari.GuildChannel]
            The channels to cache.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def startup_guild_members(
        self,
        members: Iterable[hikari.Member],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Cache members on startup.

        Parameters
        ----------
        members : Iterable[hikari.Member]
            The members to cache.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @abstractmethod
    async def startup_guild_roles(
        self,
        roles: Iterable[hikari.Role],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Cache roles on startup.

        Parameters
        ----------
        roles : Iterable[hikari.Role]
            The roles to cache.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """
