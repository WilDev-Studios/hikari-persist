from __future__ import annotations

from collections.abc import (
    AsyncIterator,
    Iterable,
    Sequence,
)
from contextlib import suppress
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from hikari import users
from hikaripersist.backend.base import Backend
from pathlib import Path
from typing import (
    Any,
    Literal,
    TYPE_CHECKING,
)

import asyncio
import hikari
import logging

try:
    import aiosqlite
    INSTALLED: bool = True
except ImportError:
    INSTALLED: bool = False

if TYPE_CHECKING:
    from hikaripersist.impl.query import (
        BaseQuery,
        ChannelQuery,
        GuildQuery,
        MemberQuery,
        RoleQuery,
    )

__all__ = ("SQLiteBackend",)

logger: logging.Logger = logging.getLogger("persist.sqlite")

@dataclass(frozen=True, slots=True)
class _SQLOP:
    sql: str
    mode: Literal["execute", "executemany"]
    params: tuple[Any, ...] | list[tuple[Any, ...]]
    future: asyncio.Future[None] | None

class SQLiteBackend(Backend):
    """Use `SQLite` as the persistent cache backend."""

    VERSION: int = 1
    """
    The database schema version; updated for automatic migrations.

    Warning
    -------
    Automatic migrations will not occur until `1.0.0`.
    Until then, each update requires a deletion of cache.
    """

    __slots__ = (
        "_backup",
        "_batch_size",
        "_connection",
        "_connection_file",
        "_db_lock",
        "_filepath",
        "_interval",
        "_queue",
        "_ready",
        "_writer",
    )

    def __init__(
        self,
        filepath: Path | str,
        *,
        backup_interval: int = 0,
        batch_size: int = 100,
    ) -> None:
        """
        Create a new `SQLite` persistent backend.

        Parameters
        ----------
        filepath : Path | str
            The path to the `SQLite` database file.
        backup_interval : int
            If `> 0`, the backend should use an in-memory database for performance
            while using the given filepath as a backup-and-restore database for persistence.
            This interval configures how often the in-memory database backs up into the file in
            seconds.
        batch_size : int
            The size of each batched SQL execution. Iterated reads and writes will occur in batches
            of this amount.

        Raises
        ------
        ImportError
            If `aiosqlite` is not installed.
        TypeError
            - If `filepath` is not `Path` or `str`.
            - If `backup_interval` is not `int`.
            - If `batch_size` is not `int`.
        ValueError
            - If `backup_interval` is less than `0`.
            - If `batch_size` is less than `1`.
        """

        if not INSTALLED:
            error: str = "SQLiteBackend requires `aiosqlite` to be installed"
            raise ImportError(error)

        if not isinstance(filepath, (Path, str)):
            error: str = "Provided filepath must be `Path` or `str`"
            raise TypeError(error)

        if not isinstance(backup_interval, int):
            error: str = "Provided backup interval must be `int`"
            raise TypeError(error)

        if not isinstance(batch_size, int):
            error: str = "Provided batch size must be `int`"
            raise TypeError(error)

        if backup_interval < 0:
            error: str = "Provided backup interval must be 0 or greater"
            raise ValueError(error)

        if batch_size < 1:
            error: str = "Provided batch size must be 1 or greater"
            raise ValueError(error)

        self._connection: aiosqlite.Connection | None = None
        self._filepath: Path | str = filepath
        self._batch_size: int = batch_size

        self._writer: asyncio.Task[None] | None = None
        self._queue: asyncio.Queue[_SQLOP] = asyncio.Queue()

        self._connection_file: aiosqlite.Connection | None = None
        self._backup: asyncio.Task[None] | None = None
        self._interval: int = backup_interval

        self._ready: asyncio.Event = asyncio.Event()
        self._db_lock: asyncio.Lock = asyncio.Lock()

    async def __backup(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._interval)
                await self._connection.backup(self._connection_file)

                logger.debug("Backup of in-memory database to file made")
        except asyncio.CancelledError:
            return

    def __build_query(
        self,
        query: BaseQuery,
    ) -> tuple[list[str], list[object]]:
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

    async def __create_schema(
        self,
        db: aiosqlite.Connection,
    ) -> None:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS channels (
                id                    INTEGER NOT NULL PRIMARY KEY,
                name                  TEXT,
                type                  INTEGER NOT NULL,
                guild_id              INTEGER NOT NULL,
                parent_id             INTEGER,
                position              INTEGER,              -- !GUILD_NEWS_THREAD, !GUILD_PUBLIC_THREAD, !GUILD_PRIVATE_THREAD
                is_nsfw               INTEGER,              -- !GUILD_NEWS_THREAD, !GUILD_PUBLIC_THREAD, !GUILD_PRIVATE_THREAD
                permission_overwrites TEXT,                 -- !GUILD_NEWS_THREAD, !GUILD_PUBLIC_THREAD, !GUILD_PRIVATE_THREAD
                topic                              TEXT,    -- GUILD_TEXT, GUILD_NEWS, GUILD_FORUM, GUILD_MEDIA
                last_message_id                    INTEGER, -- GUILD_TEXT, GUILD_VOICE, GUILD_NEWS, GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD, GUILD_STAGE
                rate_limit_per_user                INTEGER, -- GUILD_TEXT, GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD, GUILD_FORUM, GUILD_MEDIA
                last_pin_timestamp                 REAL,    -- GUILD_TEXT, GUILD_NEWS, GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD
                default_auto_archive_duration      INTEGER, -- GUILD_TEXT, GUILD_NEWS, GUILD_FORUM, GUILD_MEDIA
                bitrate                            INTEGER, -- GUILD_VOICE, GUILD_STAGE
                region                             TEXT,    -- GUILD_VOICE, GUILD_STAGE
                user_limit                         INTEGER, -- GUILD_VOICE, GUILD_STAGE
                video_quality_mode                 INTEGER, -- GUILD_VOICE, GUILD_STAGE
                approximate_message_count          INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD
                approximate_member_count           INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD
                member_thread_id                   INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (member field)
                member_user_id                     INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (member field)
                member_joined_at                   REAL,    -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (member field)
                member_flags                       INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (member field)
                owner_id                           INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD
                metadata_is_archived               INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (metadata field)
                metadata_is_invitable              INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (metadata field)
                metadata_auto_archive_duration     INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (metadata field)
                metadata_archive_timestamp         INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (metadata field)
                metadata_is_locked                 INTEGER, -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (metadata field)
                metadata_created_at                REAL,    -- GUILD_NEWS_THREAD, GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD (metadata field)
                applied_tag_ids                    TEXT,    -- GUILD_PUBLIC_THREAD
                flags                              INTEGER, -- GUILD_PUBLIC_THREAD, GUILD_FORUM, GUILD_MEDIA
                last_thread_id                     INTEGER, -- GUILD_FORUM, GUILD_MEDIA
                default_thread_rate_limit_per_user INTEGER, -- GUILD_FORUM, GUILD_MEDIA
                available_tags                     TEXT,    -- GUILD_FORUM, GUILD_MEDIA
                default_sort_order                 INTEGER, -- GUILD_FORUM, GUILD_MEDIA
                default_layout                     INTEGER, -- GUILD_FORUM, GUILD_MEDIA
                default_reaction_emoji_id          INTEGER, -- GUILD_FORUM, GUILD_MEDIA
                default_reaction_emoji_name        TEXT     -- GUILD_FORUM, GUILD_MEDIA
            );
            CREATE TABLE IF NOT EXISTS guilds (
                id                            INTEGER NOT NULL PRIMARY KEY,
                icon_hash                     TEXT,
                name                          TEXT NOT NULL,
                features                      TEXT,
                incidents_invites_disabled_until REAL, -- incidents field
                incidents_dms_disabled_until     REAL, -- incidents field
                incidents_dm_spam_detected_at    REAL, -- incidents field
                incidents_raid_detected_at       REAL, -- incidents field
                application_id                INTEGER,
                afk_channel_id                INTEGER,
                afk_timeout                   INTEGER NOT NULL,
                banner_hash                   TEXT,
                default_message_notifications INTEGER NOT NULL,
                description                   TEXT,
                discovery_splash_hash         TEXT,
                explicit_content_filter       INTEGER NOT NULL,
                is_widget_enabled             INTEGER,
                max_video_channel_users       INTEGER,
                mfa_level                     INTEGER NOT NULL,
                owner_id                      INTEGER NOT NULL,
                preferred_locale              TEXT NOT NULL,
                premium_subscription_count    INTEGER,
                premium_tier                  INTEGER NOT NULL,
                public_updates_channel_id     INTEGER,
                rules_channel_id              INTEGER,
                splash_hash                   TEXT,
                system_channel_flags          INTEGER NOT NULL,
                system_channel_id             INTEGER,
                vanity_url_code               TEXT,
                verification_level            INTEGER NOT NULL,
                widget_channel_id             INTEGER,
                nsfw_level                    INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS members (
                id                               INTEGER NOT NULL,
                guild_id                         INTEGER NOT NULL,
                joined_at                        REAL,
                nickname                         TEXT,
                premium_since                    REAL,
                raw_communication_disabled_until REAL,
                role_ids                         TEXT,
                guild_avatar_decoration_asset_hash TEXT,    -- guild_avatar_decoration field
                guild_avatar_decoration_sku_id     INTEGER, -- guild_avatar_decoration field
                guild_avatar_decoration_expires_at REAL,    -- guild_avatar_decoration field
                guild_avatar_hash                TEXT,
                guild_banner_hash                TEXT,
                guild_flags                      INTEGER,
                PRIMARY KEY (id, guild_id)
            );
            CREATE TABLE IF NOT EXISTS roles (
                id                         INTEGER NOT NULL PRIMARY KEY,
                name                       TEXT NOT NULL,
                color                      INTEGER NOT NULL,
                guild_id                   INTEGER NOT NULL,
                is_hoisted                 INTEGER NOT NULL,
                icon_hash                  TEXT,
                unicode_emoji              TEXT,
                is_managed                 INTEGER NOT NULL,
                is_mentionable             INTEGER NOT NULL,
                permissions                INTEGER NOT NULL,
                position                   INTEGER NOT NULL,
                bot_id                     INTEGER,
                integration_id             INTEGER,
                is_premium_subscriber_role INTEGER NOT NULL,
                subscription_listing_id    INTEGER,
                is_available_for_purchase  INTEGER NOT NULL,
                is_guild_linked_role       INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER NOT NULL PRIMARY KEY,
                discriminator TEXT NOT NULL,
                username      TEXT NOT NULL,
                global_name   TEXT,
                avatar_decoration_asset_hash TEXT,    -- avatar_decoration field
                avatar_decoration_sku_id     INTEGER, -- avatar_decoration field
                avatar_decoration_expires_at REAL,    -- avatar_decoration field
                avatar_hash   TEXT,
                banner_hash   TEXT,
                accent_color  INTEGER,
                is_bot        INTEGER NOT NULL,
                is_system     INTEGER NOT NULL,
                flags         INTEGER NOT NULL,
                primary_guild_identity_guild_id INTEGER, -- primary_guild field
                primary_guild_identity_enabled  INTEGER, -- primary_guild field
                primary_guild_tag               TEXT,    -- primary_guild field
                primary_guild_badge_hash        TEXT     -- primary_guild field
            );
            CREATE INDEX IF NOT EXISTS idx_channels_guild ON channels(guild_id);
            CREATE INDEX IF NOT EXISTS idx_members_guild ON members(guild_id);
            CREATE INDEX IF NOT EXISTS idx_roles_guild ON roles(guild_id);
        """) # noqa: E501
        await db.commit()

    async def __execute(
        self,
        execute: str,
        values: tuple[Any],
        confirm: bool = False,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = None
        if confirm:
            future = asyncio.get_running_loop().create_future()

        await self._queue.put(_SQLOP(execute, "execute", values, future))

        return future

    async def __executemany(
        self,
        execute: str,
        values: list[tuple[Any, ...]],
        confirm: bool = False,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = None
        if confirm:
            future = asyncio.get_running_loop().create_future()

        await self._queue.put(_SQLOP(execute, "executemany", values, future))

        return future

    def __serialize_channel(
        self,
        channel: hikari.GuildChannel,
    ) -> tuple[tuple[str, ...], tuple[Any, ...]]:
        values: dict[str, Any] = {
            "id": channel.id,
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

    async def __version_get(
        self,
        db: aiosqlite.Connection,
    ) -> int:
        async with db.execute("PRAGMA user_version;") as cursor:
            row: aiosqlite.Row = await cursor.fetchone()

        return row[0]

    async def __version_migrate(
        self,
        current: int,
        db: aiosqlite.Connection,
    ) -> None:
        if current > SQLiteBackend.VERSION:
            error: str = "Database schema newer than supported version"
            raise RuntimeError(error)

        if current == 0:
            logger.debug("Database version not found; creating schemas...")

            await self.__create_schema(db)
            current = SQLiteBackend.VERSION
        #elif current < 2:
            # migrate to V2

            #if from_backup:
                #...
            #else:
                #...

        await db.execute(f"PRAGMA user_version = {SQLiteBackend.VERSION};")
        await db.commit()

    async def __writer(self) -> None: # noqa: PLR0912
        try:
            while True:
                operation: _SQLOP = await self._queue.get()
                batch: list[_SQLOP] = [operation]

                while len(batch) < self._batch_size:
                    try:
                        batch.append(self._queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break

                futures: list[asyncio.Future[None]] = []

                async with self._db_lock:
                    await self._connection.execute("BEGIN")

                    i: int = 0
                    while i < len(batch):
                        op: _SQLOP = batch[i]

                        match op.mode:
                            case "execute":
                                await self._connection.execute(op.sql, op.params)
                            case "executemany":
                                rows: list[tuple[Any, ...]] = list(op.params)

                                j: int = i + 1
                                while j < len(batch):
                                    nxt: _SQLOP = batch[j]

                                    if nxt.mode != "executemany" or nxt.sql != op.sql:
                                        break

                                    rows.extend(nxt.params)
                                    j += 1

                                await self._connection.executemany(op.sql, rows)
                                i = j - 1

                        if op.future:
                            futures.append(op.future)

                        i += 1

                    await self._connection.commit()

                for future in futures:
                    if future.done():
                        continue

                    future.set_result(None)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Writer crashed")
            raise

    async def bulk_channels(
        self,
        channels: Sequence[hikari.GuildChannel],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        if not channels:
            return None

        if len(channels) == 1:
            return await self.channel_create(channels[0], confirm)

        rows: list[tuple[Any, ...]] = [self.__serialize_channel(c)[1] for c in channels]
        fields, _ = self.__serialize_channel(channels[0])

        return await self.__executemany(
            f"""
            INSERT OR REPLACE INTO channels
            ({', '.join(fields)})
            VALUES ({', '.join('?' * len(fields))});
            """,
            rows,
            confirm,
        )

    async def bulk_members(
        self,
        members: Iterable[hikari.Member],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        members_values: list[tuple[Any, ...]] = []
        users_values: list[tuple[Any, ...]] = []

        for member in members:
            comm_disabled: datetime | None = member.raw_communication_disabled_until

            members_values.append((
                member.id,
                member.guild_id,
                member.joined_at.astimezone(timezone.utc).timestamp(),
                member.nickname,
                member.premium_since.astimezone(timezone.utc).timestamp()
                if member.premium_since else None,
                comm_disabled.astimezone(timezone.utc).timestamp()
                if comm_disabled else None,
                ','.join(str(r) for r in member.role_ids) if member.role_ids else None,
                member.guild_avatar_decoration.asset_hash
                if member.guild_avatar_decoration else None,
                member.guild_avatar_decoration.sku_id
                if member.guild_avatar_decoration else None,
                member.guild_avatar_decoration.expires_at.astimezone(timezone.utc).timestamp()
                if (
                    member.guild_avatar_decoration and
                    member.guild_avatar_decoration.expires_at
                ) else None,
                member.guild_avatar_hash,
                member.guild_banner_hash,
                int(member.guild_flags),
            ))

            users_values.append((
                member.id,
                member.discriminator,
                member.username,
                member.global_name,
                member.avatar_decoration.asset_hash if member.avatar_decoration else None,
                member.avatar_decoration.sku_id if member.avatar_decoration else None,
                member.avatar_decoration.expires_at.astimezone(timezone.utc).timestamp()
                if member.avatar_decoration and member.avatar_decoration.expires_at else None,
                member.avatar_hash,
                member.banner_hash,
                int(member.accent_color) if member.accent_color is not None else None,
                int(member.is_bot),
                int(member.is_system),
                int(member.flags),
                member.primary_guild.identity_guild_id if member.primary_guild else None,
                int(member.primary_guild.identity_enabled) if member.primary_guild else None,
                member.primary_guild.tag if member.primary_guild else None,
                member.primary_guild.badge_hash if member.primary_guild else None,
            ))

        if not members_values and not users_values:
            return None

        futures: list[asyncio.Future[None]] = []

        if members_values:
            future: asyncio.Future[None] | None = await self.__executemany(
                """
                INSERT INTO members (
                    id,
                    guild_id,
                    joined_at,
                    nickname,
                    premium_since,
                    raw_communication_disabled_until,
                    role_ids,
                    guild_avatar_decoration_asset_hash,
                    guild_avatar_decoration_sku_id,
                    guild_avatar_decoration_expires_at,
                    guild_avatar_hash,
                    guild_banner_hash,
                    guild_flags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id, guild_id) DO UPDATE SET
                    nickname = excluded.nickname,
                    premium_since = excluded.premium_since,
                    raw_communication_disabled_until = excluded.raw_communication_disabled_until,
                    role_ids = excluded.role_ids,
                    guild_avatar_decoration_asset_hash = excluded.guild_avatar_decoration_asset_hash,
                    guild_avatar_decoration_sku_id = excluded.guild_avatar_decoration_sku_id,
                    guild_avatar_decoration_expires_at = excluded.guild_avatar_decoration_expires_at,
                    guild_avatar_hash = excluded.guild_avatar_hash,
                    guild_banner_hash = excluded.guild_banner_hash,
                    guild_flags = excluded.guild_flags;
                """, # noqa: E501
                members_values,
                confirm,
            )

            if future:
                futures.append(future)

        if users_values:
            future: asyncio.Future[None] | None = await self.__executemany(
                """
                INSERT INTO users (
                    id,
                    discriminator,
                    username,
                    global_name,
                    avatar_decoration_asset_hash,
                    avatar_decoration_sku_id,
                    avatar_decoration_expires_at,
                    avatar_hash,
                    banner_hash,
                    accent_color,
                    is_bot,
                    is_system,
                    flags,
                    primary_guild_identity_guild_id,
                    primary_guild_identity_enabled,
                    primary_guild_tag,
                    primary_guild_badge_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    discriminator = excluded.discriminator,
                    username = excluded.username,
                    global_name = excluded.global_name,
                    avatar_decoration_asset_hash = excluded.avatar_decoration_asset_hash,
                    avatar_decoration_sku_id = excluded.avatar_decoration_sku_id,
                    avatar_decoration_expires_at = excluded.avatar_decoration_expires_at,
                    avatar_hash = excluded.avatar_hash,
                    banner_hash = excluded.banner_hash,
                    accent_color = excluded.accent_color,
                    is_bot = excluded.is_bot,
                    is_system = excluded.is_system,
                    flags = excluded.flags,
                    primary_guild_identity_guild_id = excluded.primary_guild_identity_guild_id,
                    primary_guild_identity_enabled = excluded.primary_guild_identity_enabled,
                    primary_guild_tag = excluded.primary_guild_tag,
                    primary_guild_badge_hash = excluded.primary_guild_badge_hash;
                """,
                users_values,
                confirm,
            )

            if future:
                futures.append(future)

        if confirm:
            return asyncio.gather(*futures, return_exceptions=True)

        return None

    async def bulk_roles(
        self,
        roles: Iterable[hikari.Role],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        values: list[tuple] = [
            (
                role.id,
                role.name,
                int(role.color),
                role.guild_id,
                int(role.is_hoisted),
                role.icon_hash,
                str(role.unicode_emoji) if role.unicode_emoji else None,
                int(role.is_managed),
                int(role.is_mentionable),
                int(role.permissions),
                role.position,
                role.bot_id,
                role.integration_id,
                int(role.is_premium_subscriber_role),
                role.subscription_listing_id,
                int(role.is_available_for_purchase),
                int(role.is_guild_linked_role),
            )
            for role in roles
        ]

        if not values:
            return None

        future: asyncio.Future[None] | None = await self.__executemany(
            """
            INSERT INTO ROLES
            (
                id,
                name,
                color,
                guild_id,
                is_hoisted,
                icon_hash,
                unicode_emoji,
                is_managed,
                is_mentionable,
                permissions,
                position,
                bot_id,
                integration_id,
                is_premium_subscriber_role,
                subscription_listing_id,
                is_available_for_purchase,
                is_guild_linked_role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                color = excluded.color,
                guild_id = excluded.guild_id,
                is_hoisted = excluded.is_hoisted,
                icon_hash = excluded.icon_hash,
                unicode_emoji = excluded.unicode_emoji,
                is_managed = excluded.is_managed,
                is_mentionable = excluded.is_mentionable,
                permissions = excluded.permissions,
                position = excluded.position,
                bot_id = excluded.bot_id,
                integration_id = excluded.integration_id,
                is_premium_subscriber_role = excluded.is_premium_subscriber_role,
                subscription_listing_id = excluded.subscription_listing_id,
                is_available_for_purchase = excluded.is_available_for_purchase,
                is_guild_linked_role = excluded.is_guild_linked_role;
            """,
            values,
            confirm,
        )

        if confirm:
            return future

        return None

    async def channel_create(
        self,
        channel: hikari.GuildChannel,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        fields, values = self.__serialize_channel(channel)

        return await self.__execute(
            f"""
                INSERT OR REPLACE INTO channels
                ({', '.join(fields)})
                VALUES ({', '.join('?' * len(fields))});
            """,
            values,
            confirm,
        )

    async def channel_delete(
        self,
        channel_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()
        return await self.__execute(
            "DELETE FROM channels WHERE id = ?;",
            (channel_id,),
            confirm,
        )

    async def channel_update(
        self,
        channel: hikari.GuildChannel,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        fields, values = self.__serialize_channel(channel)
        values = (*values, channel.id)

        return await self.__execute(
            f"UPDATE channels SET {', '.join(f'{f} = ?' for f in fields)} WHERE id = ?;",
            values,
            confirm,
        )

    async def clear(
        self,
        channels: bool,
        guilds: bool,
        members: bool,
        roles: bool,
    ) -> None:
        await self._ready.wait()

        async with self._db_lock:
            await self._connection.execute("BEGIN;")

            if channels:
                await self._connection.execute("DELETE FROM channels;")
            if guilds:
                await self._connection.execute("DELETE FROM guilds;")
            if members:
                await self._connection.execute("DELETE FROM users;")
                await self._connection.execute("DELETE FROM members;")
            if roles:
                await self._connection.execute("DELETE FROM roles;")

            await self._connection.commit()

    async def connect(self) -> None:
        logger.debug("Connecting to SQLite database at %s", self._filepath)

        if self._interval:
            logger.debug("Connecting to in-memory SQLite database")

            self._connection = await aiosqlite.connect(":memory:")
            self._connection_file = await aiosqlite.connect(self._filepath)

            await self._connection_file.backup(self._connection)

            def backup_done(task: asyncio.Task[None]) -> None:
                if task.cancelled():
                    return

                exception: BaseException | None = task.exception()
                if exception is not None:
                    logger.exception("Backup task crashed", exc_info=exception)

            self._backup = asyncio.create_task(self.__backup(), name="sqlite-backup")
            self._backup.add_done_callback(backup_done)
        else:
            self._connection = await aiosqlite.connect(self._filepath)

        await self._connection.execute("PRAGMA foreign_keys=ON;")
        await self._connection.execute("PRAGMA synchronous=NORMAL;")
        await self._connection.execute("PRAGMA temp_store=MEMORY;")

        if not self._interval:
            await self._connection.execute("PRAGMA journal_mode=WAL;")
            await self._connection.execute("PRAGMA mmap_size=300000000000;")

        await self._connection.commit()

        version: int = await self.__version_get(self._connection)

        if version != SQLiteBackend.VERSION:
            await self.__version_migrate(version, self._connection)

        def writer_done(task: asyncio.Task[None]) -> None:
            if task.cancelled():
                return

            exception: BaseException | None = task.exception()
            if exception is not None:
                logger.exception("Writer task crashed", exc_info=exception)

        self._writer = asyncio.create_task(self.__writer(), name="sqlite-writer")
        self._writer.add_done_callback(writer_done)

        self._ready.set()

        logger.info("Connected to SQLite cache database")

    async def disconnect(self) -> None:
        if self._backup:
            self._backup.cancel()

            with suppress(asyncio.CancelledError):
                await self._backup

            self._backup = None

        if self._writer:
            self._writer.cancel()

            with suppress(asyncio.CancelledError):
                await self._writer

            self._writer = None

        remaining: list[tuple[str, tuple[Any], asyncio.Future[None] | None]] = []
        while not self._queue.empty():
            remaining.append(await self._queue.get())

        if remaining:
            await self._connection.execute("BEGIN")
            for query in remaining:
                sql, values, _ = query
                await self._connection.execute(sql, values)
            await self._connection.commit()

        if self._interval:
            logger.debug("Dumping in-memory database to file")

            await self._connection.backup(self._connection_file)
            await self._connection_file.close()

        await self._connection.close()

        self._connection = None
        self._connection_file = None

        logger.info("Disconnected from SQLite cache database")

    async def guild_join(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        future: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO guilds
                (
                    id,
                    icon_hash,
                    name,
                    features,
                    incidents_invites_disabled_until,
                    incidents_dms_disabled_until,
                    incidents_dm_spam_detected_at,
                    incidents_raid_detected_at,
                    application_id,
                    afk_channel_id,
                    afk_timeout,
                    banner_hash,
                    default_message_notifications,
                    description,
                    discovery_splash_hash,
                    explicit_content_filter,
                    is_widget_enabled,
                    max_video_channel_users,
                    mfa_level,
                    owner_id,
                    preferred_locale,
                    premium_subscription_count,
                    premium_tier,
                    public_updates_channel_id,
                    rules_channel_id,
                    splash_hash,
                    system_channel_flags,
                    system_channel_id,
                    vanity_url_code,
                    verification_level,
                    widget_channel_id,
                    nsfw_level
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                );
            """,
            (
                guild.id,
                guild.icon_hash,
                guild.name,
                ','.join(str(feature) for feature in guild.features) if guild.features else None,
                guild.incidents.invites_disabled_until.astimezone(timezone.utc).timestamp()
                if guild.incidents.invites_disabled_until else None,
                guild.incidents.dms_disabled_until.astimezone(timezone.utc).timestamp()
                if guild.incidents.dms_disabled_until else None,
                guild.incidents.dm_spam_detected_at.astimezone(timezone.utc).timestamp()
                if guild.incidents.dm_spam_detected_at else None,
                guild.incidents.raid_detected_at.astimezone(timezone.utc).timestamp()
                if guild.incidents.raid_detected_at else None,
                guild.application_id,
                guild.afk_channel_id,
                guild.afk_timeout.total_seconds(),
                guild.banner_hash,
                int(guild.default_message_notifications),
                guild.description,
                guild.discovery_splash_hash,
                int(guild.explicit_content_filter),
                int(guild.is_widget_enabled) if guild.is_widget_enabled is not None else None,
                guild.max_video_channel_users,
                int(guild.mfa_level),
                guild.owner_id,
                str(guild.preferred_locale),
                guild.premium_subscription_count,
                int(guild.premium_tier),
                guild.public_updates_channel_id,
                guild.rules_channel_id,
                guild.splash_hash,
                int(guild.system_channel_flags),
                guild.system_channel_id,
                guild.vanity_url_code,
                int(guild.verification_level),
                guild.widget_channel_id,
                int(guild.nsfw_level),
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def guild_leave(
        self,
        guild_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        future: asyncio.Future[None] | None = await self.__execute(
            "DELETE FROM guilds WHERE id = ?;",
            (guild_id,),
            confirm,
        )

        if confirm:
            return future

        return None

    async def guild_update(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        future: asyncio.Future[None] | None = await self.__execute(
            """
                UPDATE guilds SET
                    icon_hash = ?,
                    name = ?,
                    features = ?,
                    incidents_invites_disabled_until = ?,
                    incidents_dms_disabled_until = ?,
                    incidents_dm_spam_detected_at = ?,
                    incidents_raid_detected_at = ?,
                    afk_channel_id = ?,
                    afk_timeout = ?,
                    banner_hash = ?,
                    default_message_notifications = ?,
                    description = ?,
                    discovery_splash_hash = ?,
                    explicit_content_filter = ?,
                    is_widget_enabled = ?,
                    max_video_channel_users = ?,
                    mfa_level = ?,
                    preferred_locale = ?,
                    premium_subscription_count = ?,
                    premium_tier = ?,
                    public_updates_channel_id = ?,
                    rules_channel_id = ?,
                    splash_hash = ?,
                    system_channel_flags = ?,
                    system_channel_id = ?,
                    vanity_url_code = ?,
                    verification_level = ?,
                    widget_channel_id = ?,
                    nsfw_level = ?
                WHERE id = ?;
            """,
            (
                guild.icon_hash,
                guild.name,
                ','.join(str(feature) for feature in guild.features) if guild.features else None,
                guild.incidents.invites_disabled_until.astimezone(timezone.utc).timestamp()
                if guild.incidents.invites_disabled_until else None,
                guild.incidents.dms_disabled_until.astimezone(timezone.utc).timestamp()
                if guild.incidents.dms_disabled_until else None,
                guild.incidents.dm_spam_detected_at.astimezone(timezone.utc).timestamp()
                if guild.incidents.dm_spam_detected_at else None,
                guild.incidents.raid_detected_at.astimezone(timezone.utc).timestamp()
                if guild.incidents.raid_detected_at else None,
                guild.afk_channel_id,
                guild.afk_timeout.total_seconds(),
                guild.banner_hash,
                int(guild.default_message_notifications),
                guild.description,
                guild.discovery_splash_hash,
                int(guild.explicit_content_filter),
                int(guild.is_widget_enabled) if guild.is_widget_enabled is not None else None,
                guild.max_video_channel_users,
                int(guild.mfa_level),
                str(guild.preferred_locale),
                guild.premium_subscription_count,
                int(guild.premium_tier),
                guild.public_updates_channel_id,
                guild.rules_channel_id,
                guild.splash_hash,
                int(guild.system_channel_flags),
                guild.system_channel_id,
                guild.vanity_url_code,
                int(guild.verification_level),
                guild.widget_channel_id,
                int(guild.nsfw_level),

                guild.id,
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def iter_channels( # noqa: PLR0912
        self,
        query: ChannelQuery | None,
    ) -> AsyncIterator[hikari.GuildChannel]:
        await self._ready.wait()

        sql: str = "SELECT * FROM channels"

        if query:
            conditions, params = self.__build_query(query)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._connection.execute(sql, tuple(params) if query else ()) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(self._batch_size)

                if not rows:
                    break

                for row in rows:
                    overwrites: dict[hikari.Snowflake, hikari.PermissionOverwrite] = {}

                    if row[7]:
                        for entry in row[7].split('|'):
                            parts: list[str] = entry.split(':')
                            id_: hikari.Snowflake = hikari.Snowflake(parts[0])
                            overwrites[id_] = hikari.PermissionOverwrite(
                                id=id_,
                                type=hikari.PermissionOverwriteType(int(parts[1])),
                                allow=hikari.Permissions(int(parts[2])),
                                deny=hikari.Permissions(int(parts[3])),
                            )

                    channel_type: hikari.ChannelType = hikari.ChannelType(row[2])

                    match channel_type:
                        case hikari.ChannelType.GUILD_TEXT:
                            yield hikari.GuildTextChannel(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                position=row[5],
                                is_nsfw=bool(row[6]),
                                permission_overwrites=overwrites,
                                topic=row[8],
                                last_message_id=row[9],
                                rate_limit_per_user=timedelta(seconds=row[10]),
                                last_pin_timestamp=datetime.fromtimestamp(row[11], timezone.utc)
                                if row[11] else None,
                                default_auto_archive_duration=timedelta(seconds=row[12]),
                            )
                        case hikari.ChannelType.GUILD_VOICE:
                            yield hikari.GuildVoiceChannel(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                position=row[5],
                                is_nsfw=bool(row[6]),
                                permission_overwrites=overwrites,
                                bitrate=row[13],
                                region=row[14],
                                user_limit=row[15],
                                video_quality_mode=hikari.VideoQualityMode(row[16]),
                                last_message_id=row[9],
                            )
                        case hikari.ChannelType.GUILD_CATEGORY:
                            yield hikari.GuildCategory(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                position=row[5],
                                is_nsfw=bool(row[6]),
                                permission_overwrites=overwrites,
                            )
                        case hikari.ChannelType.GUILD_NEWS:
                            yield hikari.GuildNewsChannel(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                position=row[5],
                                is_nsfw=bool(row[6]),
                                permission_overwrites=overwrites,
                                topic=row[8],
                                last_message_id=row[9],
                                last_pin_timestamp=datetime.fromtimestamp(row[11], timezone.utc)
                                if row[11] else None,
                                default_auto_archive_duration=timedelta(seconds=row[12]),
                            )
                        case hikari.ChannelType.GUILD_NEWS_THREAD:
                            yield hikari.GuildNewsThread(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                last_message_id=row[9],
                                last_pin_timestamp=datetime.fromtimestamp(row[11], timezone.utc)
                                if row[11] else None,
                                rate_limit_per_user=timedelta(seconds=row[10]),
                                approximate_message_count=row[17],
                                approximate_member_count=row[18],
                                member=hikari.ThreadMember(
                                    thread_id=row[19],
                                    user_id=row[20],
                                    joined_at=datetime.fromtimestamp(row[21], timezone.utc),
                                    flags=row[22],
                                ) if all((row[19], row[20], row[21], row[22])) else None,
                                owner_id=row[23],
                                metadata=hikari.ThreadMetadata(
                                    is_archived=bool(row[24]),
                                    is_invitable=bool(row[25]),
                                    auto_archive_duration=timedelta(seconds=row[26]),
                                    archive_timestamp=datetime.fromtimestamp(row[27], timezone.utc),
                                    is_locked=bool(row[28]),
                                    created_at=datetime.fromtimestamp(row[29], timezone.utc)
                                    if row[29] else None,
                                )
                            )
                        case hikari.ChannelType.GUILD_PUBLIC_THREAD:
                            yield hikari.GuildPublicThread(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                last_message_id=row[9],
                                last_pin_timestamp=datetime.fromtimestamp(row[11], timezone.utc)
                                if row[11] else None,
                                rate_limit_per_user=timedelta(seconds=row[10]),
                                approximate_message_count=row[17],
                                approximate_member_count=row[18],
                                member=hikari.ThreadMember(
                                    thread_id=row[19],
                                    user_id=row[20],
                                    joined_at=datetime.fromtimestamp(row[21], timezone.utc),
                                    flags=row[22],
                                ) if all((row[19], row[20], row[21], row[22])) else None,
                                owner_id=row[23],
                                metadata=hikari.ThreadMetadata(
                                    is_archived=bool(row[24]),
                                    is_invitable=bool(row[25]),
                                    auto_archive_duration=timedelta(seconds=row[26]),
                                    archive_timestamp=datetime.fromtimestamp(row[27], timezone.utc),
                                    is_locked=bool(row[28]),
                                    created_at=datetime.fromtimestamp(row[29], timezone.utc)
                                    if row[29] else None,
                                ),
                                applied_tag_ids=[
                                    hikari.Snowflake(id_) for id_ in row[30].split(',')
                                ] if row[30] else None,
                                flags=hikari.ChannelFlag(row[31]),
                            )
                        case hikari.ChannelType.GUILD_PRIVATE_THREAD:
                            yield hikari.GuildPrivateThread(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                last_message_id=row[9],
                                last_pin_timestamp=datetime.fromtimestamp(row[11], timezone.utc)
                                if row[11] else None,
                                rate_limit_per_user=timedelta(seconds=row[10]),
                                approximate_message_count=row[17],
                                approximate_member_count=row[18],
                                member=hikari.ThreadMember(
                                    thread_id=row[19],
                                    user_id=row[20],
                                    joined_at=datetime.fromtimestamp(row[21], timezone.utc),
                                    flags=row[22],
                                ) if all((row[19], row[20], row[21], row[22])) else None,
                                owner_id=row[23],
                                metadata=hikari.ThreadMetadata(
                                    is_archived=bool(row[24]),
                                    is_invitable=bool(row[25]),
                                    auto_archive_duration=timedelta(seconds=row[26]),
                                    archive_timestamp=datetime.fromtimestamp(row[27], timezone.utc),
                                    is_locked=bool(row[28]),
                                    created_at=datetime.fromtimestamp(row[29], timezone.utc)
                                    if row[29] else None,
                                )
                            )
                        case hikari.ChannelType.GUILD_STAGE:
                            yield hikari.GuildStageChannel(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                position=row[5],
                                is_nsfw=bool(row[6]),
                                permission_overwrites=overwrites,
                                bitrate=row[13],
                                region=row[14],
                                user_limit=row[15],
                                video_quality_mode=hikari.VideoQualityMode(row[16]),
                                last_message_id=row[9],
                            )
                        case hikari.ChannelType.GUILD_FORUM:
                            yield hikari.GuildForumChannel(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                position=row[5],
                                is_nsfw=bool(row[6]),
                                permission_overwrites=overwrites,
                                topic=row[8],
                                last_thread_id=row[32],
                                rate_limit_per_user=timedelta(seconds=row[10]),
                                default_thread_rate_limit_per_user=timedelta(seconds=row[33]),
                                default_auto_archive_duration=timedelta(seconds=row[12]),
                                flags=hikari.ChannelFlag(row[31]),
                                available_tags=[
                                    hikari.ForumTag(
                                        id=hikari.Snowflake(parts[0]),
                                        name=parts[1],
                                        moderated=bool(int(parts[2])),
                                        emoji=(
                                            hikari.Snowflake(parts[3])
                                            if parts[3] != "-1" else None
                                        ),
                                    )
                                    for entry in row[34].split('|')
                                    for parts in (entry.split(':'),)
                                ] if row[34] else [],
                                default_sort_order=hikari.ForumSortOrderType(row[35]),
                                default_layout=hikari.ForumLayoutType(row[36]),
                                default_reaction_emoji_id=row[37],
                                default_reaction_emoji_name=row[38],
                            )
                        case hikari.ChannelType.GUILD_MEDIA:
                            yield hikari.GuildMediaChannel(
                                app=self._cache._bot,
                                id=row[0],
                                name=row[1],
                                type=channel_type,
                                guild_id=row[3],
                                parent_id=row[4],
                                position=row[5],
                                is_nsfw=bool(row[6]),
                                permission_overwrites=overwrites,
                                topic=row[8],
                                last_thread_id=row[32],
                                rate_limit_per_user=timedelta(seconds=row[10]),
                                default_thread_rate_limit_per_user=timedelta(seconds=row[33]),
                                default_auto_archive_duration=timedelta(seconds=row[12]),
                                flags=hikari.ChannelFlag(row[31]),
                                available_tags=[
                                    hikari.ForumTag(
                                        id=hikari.Snowflake(parts[0]),
                                        name=parts[1],
                                        moderated=bool(int(parts[2])),
                                        emoji=(
                                            hikari.Snowflake(parts[3])
                                            if parts[3] != "-1" else None
                                        ),
                                    )
                                    for entry in row[34].split('|')
                                    for parts in (entry.split(':'),)
                                ] if row[34] else [],
                                default_sort_order=hikari.ForumSortOrderType(row[35]),
                                default_layout=hikari.ForumLayoutType(row[36]),
                                default_reaction_emoji_id=row[37],
                                default_reaction_emoji_name=row[38],
                            )

    async def iter_guilds(
        self,
        query: GuildQuery | None,
    ) -> AsyncIterator[hikari.Guild]:
        await self._ready.wait()

        sql: str = "SELECT * FROM guilds"

        if query:
            conditions, params = self.__build_query(query)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._connection.execute(sql, tuple(params) if query else ()) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(self._batch_size)

                if not rows:
                    break

                for row in rows:
                    yield hikari.Guild(
                        app=self._cache._bot,
                        id=row[0],
                        icon_hash=row[1],
                        name=row[2],
                        features=[
                            hikari.GuildFeature(feature) for feature in row[3].split(',')
                        ] if row[3] else None,
                        incidents=hikari.GuildIncidents(
                            invites_disabled_until=datetime.fromtimestamp(row[4], timezone.utc)
                            if row[4] else None,
                            dms_disabled_until=datetime.fromtimestamp(row[5], timezone.utc)
                            if row[5] else None,
                            dm_spam_detected_at=datetime.fromtimestamp(row[6], timezone.utc)
                            if row[6] else None,
                            raid_detected_at=datetime.fromtimestamp(row[7], timezone.utc)
                            if row[7] else None,
                        ),
                        application_id=row[8],
                        afk_channel_id=row[9],
                        afk_timeout=timedelta(seconds=row[10]),
                        banner_hash=row[11],
                        default_message_notifications=hikari.GuildMessageNotificationsLevel(row[12]),
                        description=row[13],
                        discovery_splash_hash=row[14],
                        explicit_content_filter=hikari.GuildExplicitContentFilterLevel(row[15]),
                        is_widget_enabled=bool(row[16]) if row[16] is not None else None,
                        max_video_channel_users=row[17],
                        mfa_level=hikari.GuildMFALevel(row[18]),
                        owner_id=row[19],
                        preferred_locale=hikari.Locale(row[20]),
                        premium_subscription_count=row[21],
                        premium_tier=hikari.GuildPremiumTier(row[22]),
                        public_updates_channel_id=row[23],
                        rules_channel_id=row[24],
                        splash_hash=row[25],
                        system_channel_flags=hikari.GuildSystemChannelFlag(row[26]),
                        system_channel_id=row[27],
                        vanity_url_code=row[28],
                        verification_level=hikari.GuildVerificationLevel(row[29]),
                        widget_channel_id=row[30],
                        nsfw_level=hikari.GuildNSFWLevel(row[31]),
                    )

    async def iter_members(
        self,
        query: MemberQuery | None,
    ) -> AsyncIterator[hikari.Member]:
        await self._ready.wait()

        sql: str = "SELECT * FROM members"

        if query:
            conditions, params = self.__build_query(query)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._connection.execute(sql, tuple(params) if query else ()) as cursor:
            while True:
                members: Iterable[aiosqlite.Row] = await cursor.fetchmany(self._batch_size)

                if not members:
                    break

                async with self._connection.execute(
                    f"SELECT * FROM users WHERE id IN ({','.join('?' * len(members))});",
                    tuple(member[0] for member in members),
                ) as ucursor:
                    user_rows: Iterable[aiosqlite.Row] = await ucursor.fetchall()

                users_by_id: dict[hikari.Snowflake, aiosqlite.Row] = {
                    row[0]: row for row in user_rows
                }

                for member in members:
                    user_row: aiosqlite.Row = users_by_id.get(member[0])

                    if not user_row:
                        logger.warning(
                            "Member has no cached user object, discarding; ID=%s",
                            member[0],
                        )
                        continue

                    yield hikari.Member(
                        guild_id=member[1],
                        is_deaf=hikari.UNDEFINED,
                        is_mute=hikari.UNDEFINED,
                        is_pending=hikari.UNDEFINED,
                        joined_at=datetime.fromtimestamp(member[2], timezone.utc),
                        nickname=member[3],
                        premium_since=datetime.fromtimestamp(member[4], timezone.utc)
                        if member[4] else None,
                        raw_communication_disabled_until=datetime.fromtimestamp(
                            member[5], timezone.utc
                        ) if member[5] else None,
                        role_ids=[
                            hikari.Snowflake(id_) for id_ in member[6].split(',')
                        ] if member[6] else [],
                        user=users.UserImpl(
                            id=user_row[0],
                            app=self._cache._bot,
                            discriminator=user_row[1],
                            username=user_row[2],
                            global_name=user_row[3],
                            avatar_decoration=users.AvatarDecoration(
                                asset_hash=user_row[4],
                                sku_id=user_row[5],
                                expires_at=datetime.fromtimestamp(user_row[6], timezone.utc)
                                if user_row[6] else None,
                            ) if user_row[4] and user_row[5] else None,
                            avatar_hash=user_row[7],
                            banner_hash=user_row[8],
                            accent_color=hikari.Color(
                                user_row[9]
                            ) if user_row[9] is not None else None,
                            is_bot=bool(user_row[10]),
                            is_system=bool(user_row[11]),
                            flags=hikari.UserFlag(user_row[12]),
                            primary_guild=hikari.PrimaryGuild(
                                identity_guild_id=user_row[13],
                                identity_enabled=bool(user_row[14]) if user_row[14] else None,
                                tag=user_row[15],
                                badge_hash=user_row[16],
                            ) if any(
                                (user_row[13], user_row[14], user_row[15], user_row[16])
                            ) else None,
                        ),
                        guild_avatar_decoration=users.AvatarDecoration(
                            asset_hash=member[7],
                            sku_id=member[8],
                            expires_at=datetime.fromtimestamp(member[9], timezone.utc)
                            if member[9] else None,
                        ) if member[7] and member[8] else None,
                        guild_avatar_hash=member[10],
                        guild_banner_hash=member[11],
                        guild_flags=hikari.GuildMemberFlags(member[12]),
                    )

    async def iter_roles(
        self,
        query: RoleQuery | None,
    ) -> AsyncIterator[hikari.Role]:
        await self._ready.wait()

        sql: str = "SELECT * FROM roles"

        if query:
            conditions, params = self.__build_query(query)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._connection.execute(sql, tuple(params) if query else ()) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(self._batch_size)

                if not rows:
                    break

                for row in rows:
                    yield hikari.Role(
                        app=self._cache._bot,
                        id=row[0],
                        name=row[1],
                        color=hikari.Color(row[2]),
                        guild_id=row[3],
                        is_hoisted=bool(row[4]),
                        icon_hash=row[5],
                        unicode_emoji=hikari.UnicodeEmoji(row[6]) if row[6] else None,
                        is_managed=bool(row[7]),
                        is_mentionable=bool(row[8]),
                        permissions=hikari.Permissions(row[9]),
                        position=row[10],
                        bot_id=row[11],
                        integration_id=row[12],
                        is_premium_subscriber_role=bool(row[13]),
                        subscription_listing_id=row[14],
                        is_available_for_purchase=bool(row[15]),
                        is_guild_linked_role=bool(row[16]),
                    )

    async def member_create(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        comm_disabled: datetime | None = member.raw_communication_disabled_until

        mfuture: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO members
                (
                    id,
                    guild_id,
                    joined_at,
                    nickname,
                    premium_since,
                    raw_communication_disabled_until,
                    role_ids,
                    guild_avatar_decoration_asset_hash,
                    guild_avatar_decoration_sku_id,
                    guild_avatar_decoration_expires_at,
                    guild_avatar_hash,
                    guild_banner_hash,
                    guild_flags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                member.id,
                member.guild_id,
                member.joined_at.astimezone(timezone.utc).timestamp(),
                member.nickname,
                member.premium_since.astimezone(timezone.utc).timestamp()
                if member.premium_since else None,
                comm_disabled.astimezone(timezone.utc).timestamp()
                if comm_disabled else None,
                ','.join(str(role_id) for role_id in member.role_ids) if member.role_ids else None,
                member.guild_avatar_decoration.asset_hash
                if member.guild_avatar_decoration else None,
                member.guild_avatar_decoration.sku_id
                if member.guild_avatar_decoration else None,
                member.guild_avatar_decoration.expires_at.astimezone(timezone.utc).timestamp()
                if (
                    member.guild_avatar_decoration and
                    member.guild_avatar_decoration.expires_at)
                else None,
                member.guild_avatar_hash,
                member.guild_banner_hash,
                int(member.guild_flags),
            ),
            confirm,
        )
        ufuture: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO users
                (
                    id,
                    discriminator,
                    username,
                    global_name,
                    avatar_decoration_asset_hash,
                    avatar_decoration_sku_id,
                    avatar_decoration_expires_at,
                    avatar_hash,
                    banner_hash,
                    accent_color,
                    is_bot,
                    is_system,
                    flags,
                    primary_guild_identity_guild_id,
                    primary_guild_identity_enabled,
                    primary_guild_tag,
                    primary_guild_badge_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                member.id,
                member.discriminator,
                member.username,
                member.global_name,
                member.avatar_decoration.asset_hash if member.avatar_decoration else None,
                member.avatar_decoration.sku_id if member.avatar_decoration else None,
                member.avatar_decoration.expires_at.astimezone(timezone.utc).timestamp()
                if member.avatar_decoration and member.avatar_decoration.expires_at else None,
                member.avatar_hash,
                member.banner_hash,
                int(member.accent_color) if member.accent_color is not None else None,
                int(member.is_bot),
                int(member.is_system),
                int(member.flags),
                member.primary_guild.identity_guild_id
                if member.primary_guild else None,
                int(member.primary_guild.identity_enabled)
                if member.primary_guild else None,
                member.primary_guild.tag
                if member.primary_guild else None,
                member.primary_guild.badge_hash
                if member.primary_guild else None,
            ),
            confirm,
        )

        if confirm:
            return asyncio.gather(mfuture, ufuture, return_exceptions=True)

        return None

    async def member_delete(
        self,
        user_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        async with self._connection.execute(
            "SELECT guild_id FROM members WHERE id = ?;",
            (user_id,),
        ) as cursor:
            rows: Iterable[aiosqlite.Row] = await cursor.fetchall()

        used: bool = False
        for row in rows:
            if row[0] == guild_id:
                continue

            used = True
            break

        mfuture: asyncio.Future[None] | None = await self.__execute(
            "DELETE FROM members WHERE id = ? AND guild_id = ?;",
            (user_id, guild_id,),
            confirm,
        )

        if not used:
            ufuture: asyncio.Future[None] | None = await self.__execute(
                "DELETE FROM users WHERE id = ?;",
                (user_id,),
                confirm,
            )

        if confirm:
            if not used:
                return asyncio.gather(mfuture, ufuture, return_exceptions=True)

            return mfuture

        return None

    async def member_update(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        comm_disabled: datetime | None = member.communication_disabled_until()

        mfuture: asyncio.Future[None] = await self.__execute(
            """
                UPDATE members SET
                    nickname = ?,
                    premium_since = ?,
                    raw_communication_disabled_until = ?,
                    role_ids = ?,
                    guild_avatar_decoration_asset_hash = ?,
                    guild_avatar_decoration_sku_id = ?,
                    guild_avatar_decoration_expires_at = ?,
                    guild_avatar_hash = ?,
                    guild_banner_hash = ?,
                    guild_flags = ?
                WHERE id = ? AND guild_id = ?;
            """,
            (
                member.nickname,
                member.premium_since.astimezone(timezone.utc).timestamp()
                if member.premium_since else None,
                comm_disabled.astimezone(timezone.utc).timestamp()
                if comm_disabled else None,
                ','.join(str(role_id) for role_id in member.role_ids) if member.role_ids else None,
                member.guild_avatar_decoration.asset_hash
                if member.guild_avatar_decoration else None,
                member.guild_avatar_decoration.sku_id
                if member.guild_avatar_decoration else None,
                member.guild_avatar_decoration.expires_at.astimezone(timezone.utc).timestamp()
                if (
                    member.guild_avatar_decoration and
                    member.guild_avatar_decoration.expires_at)
                else None,
                member.guild_avatar_hash,
                member.guild_banner_hash,
                int(member.guild_flags),

                member.id,
                member.guild_id,
            ),
            confirm,
        )
        ufuture: asyncio.Future[None] | None = await self.__execute(
            """
                UPDATE users SET
                    discriminator = ?,
                    username = ?,
                    global_name = ?,
                    avatar_decoration_asset_hash = ?,
                    avatar_decoration_sku_id = ?,
                    avatar_decoration_expires_at = ?,
                    avatar_hash = ?,
                    banner_hash = ?,
                    accent_color = ?,
                    flags = ?,
                    primary_guild_identity_guild_id = ?,
                    primary_guild_identity_enabled = ?,
                    primary_guild_tag = ?,
                    primary_guild_badge_hash = ?
                WHERE id = ?;
            """,
            (
                member.discriminator,
                member.username,
                member.global_name,
                member.avatar_decoration.asset_hash if member.avatar_decoration else None,
                member.avatar_decoration.sku_id if member.avatar_decoration else None,
                member.avatar_decoration.expires_at.astimezone(timezone.utc).timestamp()
                if member.avatar_decoration and member.avatar_decoration.expires_at else None,
                member.avatar_hash,
                member.banner_hash,
                int(member.accent_color) if member.accent_color is not None else None,
                int(member.flags),
                member.primary_guild.identity_guild_id
                if member.primary_guild else None,
                int(member.primary_guild.identity_enabled)
                if member.primary_guild else None,
                member.primary_guild.tag
                if member.primary_guild else None,
                member.primary_guild.badge_hash
                if member.primary_guild else None,

                member.id,
            ),
            confirm,
        )

        if confirm:
            return asyncio.gather(mfuture, ufuture, return_exceptions=True)

        return None

    async def restore(
        self,
        path: Path,
    ) -> None:
        await self._ready.wait()

        logger.debug("Restoring database from %s", str(path))

        backup: aiosqlite.Connection = await aiosqlite.connect(path)
        version: int = await self.__version_get(backup)

        if version != SQLiteBackend.VERSION:
            await self.__version_migrate(version, backup)

        await backup.backup(self._connection)
        await backup.close()

        logger.info("Restored database from %s", str(path))

    async def role_create(
        self,
        role: hikari.Role,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        future: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO roles
                (
                    id,
                    name,
                    color,
                    guild_id,
                    is_hoisted,
                    icon_hash,
                    unicode_emoji,
                    is_managed,
                    is_mentionable,
                    permissions,
                    position,
                    bot_id,
                    integration_id,
                    is_premium_subscriber_role,
                    subscription_listing_id,
                    is_available_for_purchase,
                    is_guild_linked_role
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                role.id,
                role.name,
                int(role.color),
                role.guild_id,
                int(role.is_hoisted),
                role.icon_hash,
                str(role.unicode_emoji) if role.unicode_emoji else None,
                int(role.is_managed),
                int(role.is_mentionable),
                int(role.permissions),
                role.position,
                role.bot_id,
                role.integration_id,
                int(role.is_premium_subscriber_role),
                role.subscription_listing_id,
                int(role.is_available_for_purchase),
                int(role.is_guild_linked_role),
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def role_delete(
        self,
        role_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        future: asyncio.Future[None] | None = await self.__execute(
            "DELETE FROM roles WHERE id = ?;",
            (role_id,),
            confirm,
        )

        if confirm:
            return future

        return None

    async def role_update(
        self,
        role: hikari.Role,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        await self._ready.wait()

        future: asyncio.Future[None] | None = await self.__execute(
            """
            UPDATE roles SET
                name = ?,
                color = ?,
                is_hoisted = ?,
                icon_hash = ?,
                unicode_emoji = ?,
                is_mentionable = ?,
                permissions = ?,
                position = ?,
                subscription_listing_id = ?,
                is_available_for_purchase = ?,
                is_guild_linked_role = ?
            WHERE id = ?;
            """,
            (
                role.name,
                int(role.color),
                int(role.is_hoisted),
                role.icon_hash,
                str(role.unicode_emoji) if role.unicode_emoji else None,
                int(role.is_mentionable),
                int(role.permissions),
                role.position,
                role.subscription_listing_id,
                int(role.is_available_for_purchase),
                int(role.is_guild_linked_role),

                role.id,
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def snapshot(
        self,
        path: Path,
    ) -> None:
        await self._ready.wait()

        logger.debug("Snapshotting database")

        path.parent.mkdir(parents=True, exist_ok=True)
        temp: Path = Path(str(path) + ".tmp")

        backup: aiosqlite.Connection = await aiosqlite.connect(temp)
        attempts: int = 0
        success: bool = False

        while attempts < 3: # noqa: PLR2004
            await self._connection.backup(backup)

            cursor: aiosqlite.Cursor = await backup.execute("PRAGMA integrity_check;")
            result: aiosqlite.Row | None = await cursor.fetchone()
            if result and result[0] == 'ok':
                success = True
                break

            logger.debug("Snapshot failed...retrying")
            await asyncio.sleep(0.5)

            attempts += 1

        await backup.close()

        if not success:
            logger.error("Database failed to snapshot")
            return

        temp.rename(path)

        logger.info("Database snapshot to %s", str(path))
