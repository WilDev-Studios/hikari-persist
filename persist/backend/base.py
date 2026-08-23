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
from dataclasses import dataclass
from datetime import (
    timedelta,
    timezone,
)
from typing import (
    Any,
    ClassVar,
    Literal,
    overload,
    TYPE_CHECKING,
)

import asyncio

if TYPE_CHECKING:
    from ..impl.cache import Cache
    from ..internal.definitions import (
        DataType,
        Table,
    )
    from ..internal.query import (
        BaseQuery,
        ChannelQuery,
        GuildQuery,
        MemberQuery,
        RoleQuery,
    )
    from pathlib import Path

    import hikari


__all__ = ("Backend",)

class Backend(ABC):
    """Base persistent cache backend."""

    _cache: Cache

    TYPES: ClassVar[dict[DataType, str]]

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

@dataclass(frozen=True, slots=True)
class SQLOP:
    sql: str | list[str]
    mode: Literal["execute", "executemany", "multi"]
    parameters: tuple | list[tuple]
    future: asyncio.Future[None] | None

class SQLBackend:
    TYPES: ClassVar[dict[DataType, str]]
    PLACEHOLDER: ClassVar[str]

    def __init__(self, batch_size: int) -> None:
        self._batch_size: int = batch_size
        self._queue: asyncio.Queue[SQLOP] = asyncio.Queue()
        self._ready: asyncio.Event = asyncio.Event()

    @staticmethod
    def _build_query(query: BaseQuery) -> tuple[list[str], list[object]]:
        conditions: list[str] = []
        parameters: list[object] = []

        for name, value in query.__dict__.items():
            if value is None:
                continue

            conditions.append(f"{name.removeprefix('_')} = ?")

            if isinstance(value, (
                bool,
                hikari.ChannelType,
                hikari.Color,
                hikari.GuildExplicitContentFilterLevel,
                hikari.GuildMessageNotificationsLevel,
                hikari.GuildMFALevel,
                hikari.GuildNSFWLevel,
                hikari.GuildPremiumTier,
                hikari.GuildSystemChannelFlag,
                hikari.GuildVerificationLevel,
                hikari.Permissions,
            )):
                parameters.append(int(value))
            elif isinstance(value, timedelta):
                parameters.append(value.total_seconds())
            elif isinstance(value, hikari.UnicodeEmoji):
                parameters.append(str(value))
            else:
                parameters.append(value)

        return conditions, parameters

    def _ddl_create(self, table: Table) -> str:
        columns: list[str] = []

        for field in table.fields:
            col_type: str = self.TYPES[field.datatype]
            parts: list[str] = [field.name, col_type]

            if not field.nullable:
                parts.append("NOT NULL")

            columns.append(" ".join(parts))

        if table.primary_key:
            columns.append(f"PRIMARY KEY ({', '.join(table.primary_key)})")

        return f"CREATE TABLE IF NOT EXISTS {table.name} ({', '.join(columns)});"

    async def _execute(
        self,
        sql: str,
        parameters: tuple,
        confirm: bool = False,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = None
        if confirm:
            future = asyncio.get_running_loop().create_future()

        await self._queue.put(SQLOP(sql, "execute", parameters, future))
        return future

    async def _executemany(
        self,
        sql: str,
        parameters: list[tuple],
        confirm: bool = False,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = None
        if confirm:
            future = asyncio.get_running_loop().create_future()

        await self._queue.put(SQLOP(sql, "executemany", parameters, future))
        return future

    async def _executemulti(
        self,
        queries: Sequence[tuple[str, tuple]],
        confirm: bool = False,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = None
        if confirm:
            future = asyncio.get_running_loop().create_future()

        sqls: list[str] = []
        parameters: list[tuple] = []

        for sql, parameters_iter in queries:
            sqls.append(sql)
            parameters.append(parameters_iter)

        await self._queue.put(SQLOP(sqls, "multi", parameters, future))
        return future

    @staticmethod
    def _serialize_channel(
        channel: hikari.GuildChannel,
        sync: int,
    ) -> tuple[tuple[str, ...], tuple]:
        values: dict[str, Any] = {
            "id": channel.id,
            "_sync": sync,
            "name": channel.name,
            "type": int(channel.type),
            "guild_id": channel.guild_id,
            "parent_id": channel.parent_id,
            "position": None,
            "is_nsfw": None,
            "permission_overwrites": None,
            "topic": None,
            "last_message_id": None,
            "rate_limit_per_user": None,
            "last_pin_timestamp": None,
            "default_auto_archive_duration": None,
            "bitrate": None,
            "region": None,
            "user_limit": None,
            "video_quality_mode": None,
            "approximate_message_count": None,
            "approximate_member_count": None,
            "member_thread_id": None,
            "member_user_id": None,
            "member_joined_at": None,
            "member_flags": None,
            "owner_id": None,
            "metadata_is_archived": None,
            "metadata_is_invitable": None,
            "metadata_auto_archive_duration": None,
            "metadata_archive_timestamp": None,
            "metadata_is_locked": None,
            "metadata_created_at": None,
            "applied_tag_ids": None,
            "flags": None,
            "last_thread_id": None,
            "default_thread_rate_limit_per_user": None,
            "available_tags": None,
            "default_sort_order": None,
            "default_layout": None,
            "default_reaction_emoji_id": None,
            "default_reaction_emoji_name": None,
        }

        if isinstance(channel, hikari.PermissibleGuildChannel):
            values["position"] = channel.position
            values["is_nsfw"] = int(channel.is_nsfw)
            values["permission_overwrites"] = '|'.join(
                f"{overwrite.id}:{int(overwrite.type)}:{int(overwrite.allow)}:{int(overwrite.deny)}"
                for overwrite in channel.permission_overwrites.values()
            )

        if isinstance(channel, (hikari.GuildTextChannel, hikari.GuildNewsChannel)):
            values["topic"] = channel.topic
            values["last_message_id"] = channel.last_message_id
            values["last_pin_timestamp"] = channel.last_pin_timestamp.astimezone(
                timezone.utc,
            ).timestamp() if channel.last_pin_timestamp else None
            values[
                "default_auto_archive_duration"
            ] = channel.default_auto_archive_duration.total_seconds()

            if isinstance(channel, hikari.GuildTextChannel):
                values["rate_limit_per_user"] = channel.rate_limit_per_user.total_seconds()
        elif isinstance(channel, (hikari.GuildVoiceChannel, hikari.GuildStageChannel)):
            values["bitrate"] = channel.bitrate
            values["region"] = channel.region
            values["user_limit"] = channel.user_limit
            values["video_quality_mode"] = int(channel.video_quality_mode)
            values["last_message_id"] = channel.last_message_id
        elif isinstance(channel, (
            hikari.GuildNewsThread,
            hikari.GuildPublicThread,
            hikari.GuildPrivateThread,
        )):
            values["last_message_id"] = channel.last_message_id
            values["last_pin_timestamp"] = channel.last_pin_timestamp.astimezone(
                timezone.utc,
            ).timestamp() if channel.last_pin_timestamp else None
            values["rate_limit_per_user"] = channel.rate_limit_per_user.total_seconds()
            values["approximate_message_count"] = channel.approximate_message_count
            values["approximate_member_count"] = channel.approximate_member_count
            values["member_thread_id"] = channel.member.thread_id if channel.member else None
            values["member_user_id"] = channel.member.user_id if channel.member else None
            values["member_joined_at"] = channel.member.joined_at.astimezone(
                timezone.utc
            ).timestamp() if channel.member else None
            values["member_flags"] = channel.member.flags if channel.member else None
            values["owner_id"] = channel.owner_id
            values["metadata_is_archived"] = int(channel.metadata.is_archived)
            values["metadata_is_invitable"] = int(channel.metadata.is_invitable)
            values[
                "metadata_auto_archive_duration"
            ] = channel.metadata.auto_archive_duration.total_seconds()
            values["metadata_archive_timestamp"] = channel.metadata.archive_timestamp.astimezone(
                timezone.utc,
            ).timestamp()
            values["metadata_is_locked"] = int(channel.metadata.is_locked)
            values["metadata_created_at"] = channel.metadata.created_at.astimezone(
                timezone.utc,
            ).timestamp() if channel.metadata.created_at else None

            if isinstance(channel, hikari.GuildPublicThread):
                values["applied_tag_ids"] = ','.join(
                    channel.applied_tag_ids,
                ) if channel.applied_tag_ids else None
                values["flags"] = int(channel.flags)
        elif isinstance(channel, (hikari.GuildForumChannel, hikari.GuildMediaChannel)):
            values["topic"] = channel.topic
            values["last_thread_id"] = channel.last_thread_id
            values["rate_limit_per_user"] = channel.rate_limit_per_user.total_seconds()
            values[
                "default_thread_rate_limit_per_user"
            ] = channel.default_thread_rate_limit_per_user.total_seconds()
            values[
                "default_auto_archive_duration"
            ] = channel.default_auto_archive_duration.total_seconds()
            values["flags"] = int(channel.flags)
            values["available_tags"] = '|'.join(
                f"{tag.id}:{tag.name}:{int(tag.moderated)}:{tag.emoji_id if tag.emoji_id else -1}"
                for tag in channel.available_tags
            ) if channel.available_tags else None
            values["default_sort_order"] = int(channel.default_sort_order)
            values["default_layout"] = int(channel.default_layout)
            values["default_reaction_emoji_id"] = channel.default_reaction_emoji_id
            values["default_reaction_emoji_name"] = str(
                channel.default_reaction_emoji_name,
            ) if channel.default_reaction_emoji_name else None

        return tuple(values.keys()), tuple(values.values())

    def _sql_delete(self, table_name: str, where: Sequence[str]) -> str:
        return f"DELETE FROM {table_name} WHERE {' AND '.join(f'{w} = {self.PLACEHOLDER}' for w in where)};" # noqa: E501

    def _sql_insert(self, table_name: str, field_names: Sequence[str]) -> str:
        placeholder: str = ", ".join([self.PLACEHOLDER] * len(field_names))
        return f"INSERT INTO {table_name} ({', '.join(field_names)}) VALUES ({placeholder});"

    def _sql_update(self, table_name: str, field_names: Sequence[str], where: Sequence[str]) -> str:
        sets: str = ", ".join(f"{n} = {self.PLACEHOLDER}" for n in field_names)
        cond: str = " AND ".join(f"{w} = {self.PLACEHOLDER}" for w in where)
        return f"UPDATE {table_name} SET {sets} WHERE {cond};"
