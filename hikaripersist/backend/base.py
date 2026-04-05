from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from collections.abc import (
    AsyncIterator,
    Iterable,
    Sequence,
)
from typing import (
    Any,
    Literal,
    overload,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from hikaripersist.cache import Cache
    from hikaripersist.impl.query import (
        ChannelQuery,
        GuildQuery,
        MemberQuery,
        RoleQuery,
    )
    from pathlib import Path

    import asyncio
    import hikari

__all__ = ("Backend",)

class Backend(ABC):
    """Base persistent cache backend."""

    _cache: Cache

    @overload
    async def bulk_channels(
        self,
        channels: Iterable[hikari.GuildChannel],
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def bulk_channels(
        self,
        channels: Iterable[hikari.GuildChannel],
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

    @abstractmethod
    async def bulk_channels(
        self,
        channels: Sequence[hikari.GuildChannel],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Insert or update channels in bulk.

        Parameters
        ----------
        channels : Sequence[hikari.GuildChannel]
            The channels to insert or update.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @overload
    async def bulk_members(
        self,
        members: Iterable[hikari.Member],
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def bulk_members(
        self,
        members: Iterable[hikari.Member],
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

    @abstractmethod
    async def bulk_members(
        self,
        members: Iterable[hikari.Member],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Insert or update members in bulk.

        Parameters
        ----------
        members : Iterable[hikari.Member]
            The members to insert or update.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @overload
    async def bulk_roles(
        self,
        roles: Iterable[hikari.Role],
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def bulk_roles(
        self,
        roles: Iterable[hikari.Role],
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

    @abstractmethod
    async def bulk_roles(
        self,
        roles: Iterable[hikari.Role],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Insert or update roles in bulk.

        Parameters
        ----------
        roles : Iterable[hikari.Role]
            The roles to insert or update.
        confirm : bool
            If `True`, this method will wait until the database transaction
            containing this operation has been committed before returning.
            If `False`, the operation is queued and this method returns immediately.

        Returns
        -------
        asyncio.Future[None] | None
            If `confirm`, the returned future to wait for.
        """

    @overload
    async def channel_create(
        self,
        channel: hikari.GuildChannel,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def channel_create(
        self,
        channel: hikari.GuildChannel,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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

    @overload
    async def channel_delete(
        self,
        channel_id: hikari.Snowflake,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def channel_delete(
        self,
        channel_id: hikari.Snowflake,
        confirm: Literal[True]
    ) -> asyncio.Future[None]:
        ...

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

    @overload
    async def channel_update(
        self,
        channel: hikari.GuildChannel,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def channel_update(
        self,
        channel: hikari.GuildChannel,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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
    async def clear(
        self,
        channels: bool,
        guilds: bool,
        members: bool,
        roles: bool,
    ) -> None:
        """
        Clear select cache data.

        Parameters
        ----------
        channels : bool
            If all channels should be cleared.
        guilds : bool
            If all guilds should be cleared.
        members : bool
            If all members should be cleared.
        roles : bool
            If all roles should be cleared.
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

    @overload
    async def guild_join(
        self,
        guild: hikari.GatewayGuild,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def guild_join(
        self,
        guild: hikari.GatewayGuild,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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

    @overload
    async def guild_leave(
        self,
        guild_id: hikari.Snowflake,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def guild_leave(
        self,
        guild_id: hikari.Snowflake,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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

    @overload
    async def guild_update(
        self,
        guild: hikari.GatewayGuild,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def guild_update(
        self,
        guild: hikari.GatewayGuild,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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
        query: ChannelQuery | None,
    ) -> AsyncIterator[hikari.GuildChannel]:
        """
        Iterate through all channels in a query.

        Parameters
        ----------
        query : ChannelQuery | None
            If provided, the channel query used in cache lookup for filtration.

        Returns
        -------
        AsyncIterator[hikari.GuildChannel]
            The async iterator containing the queried channels.
        """

    @abstractmethod
    async def iter_guilds(
        self,
        query: GuildQuery | None,
    ) -> AsyncIterator[hikari.Guild]:
        """
        Iterate through all guilds in a query.

        Parameters
        ----------
        query : GuildQuery | None
            If provided, the guild query used in cache lookup for filtration.

        Returns
        -------
        AsyncIterator[hikari.Guild]
            The async iterator containing the queried guilds.
        """

    @abstractmethod
    async def iter_members(
        self,
        query: MemberQuery | None,
    ) -> AsyncIterator[hikari.Member]:
        """
        Iterate through all members in a query.

        Parameters
        ----------
        query : GuildQuery | None
            If provided, the member query used in cache lookup for filtration.

        Returns
        -------
        AsyncIterator[hikari.Member]
            The async iterator containing the queried members.
        """

    @abstractmethod
    async def iter_roles(
        self,
        query: RoleQuery | None,
    ) -> AsyncIterator[hikari.Role]:
        """
        Iterate through all roles in a query.

        Parameters
        ----------
        query : RoleQuery | None
            If provided, the role query used in cache lookup for filtration.

        Returns
        -------
        AsyncIterator[hikari.Role]
            The async iterator containing the queried roles.
        """

    @overload
    async def member_create(
        self,
        member: hikari.Member,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def member_create(
        self,
        member: hikari.Member,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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

    @overload
    async def member_delete(
        self,
        user_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def member_delete(
        self,
        user_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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

    @overload
    async def member_update(
        self,
        member: hikari.Member,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def member_update(
        self,
        member: hikari.Member,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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
    async def prune(
        self,
    ) -> None:
        """
        Prune all objects in cache that weren't updated on startup.
        """

    @abstractmethod
    async def restore(
        self,
        path: Path,
    ) -> None:
        """
        Restore the backend from a backed up file.

        Parameters
        ----------
        path : Path
            The path to the file to restore.
        """

    @overload
    async def role_create(
        self,
        role: hikari.Role,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def role_create(
        self,
        role: hikari.Role,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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

    @overload
    async def role_delete(
        self,
        role_id: hikari.Snowflake,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def role_delete(
        self,
        role_id: hikari.Snowflake,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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

    @overload
    async def role_update(
        self,
        role: hikari.Role,
        confirm: Literal[False],
    ) -> None:
        ...

    @overload
    async def role_update(
        self,
        role: hikari.Role,
        confirm: Literal[True],
    ) -> asyncio.Future[None]:
        ...

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
    async def snapshot(
        self,
        path: Path,
    ) -> None:
        """
        Back up the backend into a restorable file.

        Parameters
        ----------
        path : Path
            The path to the file to create as the backup.
        """
