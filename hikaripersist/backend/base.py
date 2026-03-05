from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from hikaripersist.cached.channel import CachedChannel
    from hikaripersist.cached.guild import CachedGuild
    from hikaripersist.cached.member import CachedMember
    from hikaripersist.cached.message import CachedMessage
    from hikaripersist.cached.role import CachedRole

    import asyncio
    import hikari

__all__ = ("Backend",)

class Backend(ABC):
    """Base persistent cache backend."""

    @abstractmethod
    async def channel_create(
        self,
        channel: hikari.PermissibleGuildChannel,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Store a created channel.

        Parameters
        ----------
        channel : hikari.PermissibleGuildChannel
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
        channel: hikari.PermissibleGuildChannel,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Update an updated channel.

        Parameters
        ----------
        channel : hikari.PermissibleGuildChannel
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
    async def get_channel(
        self,
        channel_id: hikari.Snowflake,
    ) -> CachedChannel | None:
        """
        Retrieve a stored channel.

        Parameters
        ----------
        channel_id : hikari.Snowflake
            The ID of the channel to retrieve.

        Returns
        -------
        CachedChannel | None
            If found, the stored channel.
        """

    @abstractmethod
    async def get_guild(
        self,
        guild_id: hikari.Snowflake,
    ) -> CachedGuild | None:
        """
        Retrieve a stored guild.

        Parameters
        ----------
        guild_id : hikari.Snowflake
            The ID of the guild to retrieve.

        Returns
        -------
        CachedGuild | None
            If found, the stored guild.
        """

    @abstractmethod
    async def get_member(
        self,
        user_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
    ) -> CachedMember | None:
        """
        Retrieve a stored member.

        Parameters
        ----------
        user_id : hikari.Snowflake
            The ID of the user to retrieve.
        guild_id : hikari.Snowflake
            The ID of the bounded guild.

        Returns
        -------
        CachedMember | None
            If found, the stored member.
        """

    @abstractmethod
    async def get_message(
        self,
        message_id: hikari.Snowflake,
        channel_id: hikari.Snowflake,
    ) -> CachedMessage | None:
        """
        Retrieve a stored message.

        Parameters
        ----------
        message_id : hikari.Snowflake
            The ID of the message to retrieve.
        channel_id : hikari.Snowflake
            The ID of the channel the message is in.

        Returns
        -------
        CachedMessage | None
            If found, the stored message.
        """

    @abstractmethod
    async def get_role(
        self,
        role_id: hikari.Snowflake,
    ) -> CachedRole | None:
        """
        Retrieve a stored role.

        Parameters
        ----------
        role_id : hikari.Snowflake
            The ID of the role to retrieve.

        Returns
        -------
        CachedRole | None
            If found, the stored role.
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
    ) -> AsyncIterator[CachedChannel]:
        """
        Iterate through all channels.

        Returns
        -------
        AsyncIterator[CachedChannel]
            The async iterator containing all channels.
        """

    @abstractmethod
    async def iter_guilds(
        self,
    ) -> AsyncIterator[CachedGuild]:
        """
        Iterate through all guilds.

        Returns
        -------
        AsyncIterator[CachedGuild]
            The async iterator containing all guilds.
        """

    @abstractmethod
    async def iter_members(
        self,
        guild_id: hikari.Snowflake,
    ) -> AsyncIterator[CachedMember]:
        """
        Iterate through all guild members.

        Parameters
        ----------
        guild_id : hikari.Snowflake
            The ID of the guild to get all members from.

        Returns
        -------
        AsyncIterator[CachedMember]
            The async iterator containing all guild members.
        """

    @abstractmethod
    async def iter_messages(
        self,
        channel_id: hikari.Snowflake,
    ) -> AsyncIterator[CachedMessage]:
        """
        Iterate through all channel messages.

        Parameters
        ----------
        channel_id : hikari.Snowflake
            The ID of the channel to get all messages from.

        Returns
        -------
        AsyncIterator[CachedMessage]
            The async iterator containing all the channel messages.
        """

    @abstractmethod
    async def iter_roles(
        self,
        guild_id: hikari.Snowflake,
    ) -> AsyncIterator[CachedRole]:
        """
        Iterate through all guild roles.

        Parameters
        ----------
        guild_id : hikari.Snowflake
            The ID of the guild to get all roles from.

        Returns
        -------
        AsyncIterator[CachedRole]
            The async iterator containing all guild roles.
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
    async def message_create(
        self,
        message: hikari.Message,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Store a created message.

        Parameters
        ----------
        message : hikari.Message
            The created message to store.
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
    async def message_delete(
        self,
        message_id: hikari.Snowflake,
        channel_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Remove a deleted message.

        Parameters
        ----------
        message_id : hikari.Snowflake
            The ID of the message that was deleted.
        channel_id : hikari.Snowflake
            The ID of the channel in which the message was deleted.
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
    async def message_update(
        self,
        message: hikari.PartialMessage,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        """
        Update an updated message.

        Parameters
        ----------
        message : hikari.PartialMessage
            The updated message to update.
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
