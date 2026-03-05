from __future__ import annotations

from collections.abc import Iterable
from contextlib import suppress
from datetime import (
    datetime,
    timezone,
)
from hikaripersist.backend.base import Backend
from hikaripersist.cached.channel import (
    CachedChannel,
    CachedPermissionOverwrite,
)
from hikaripersist.cached.guild import CachedGuild
from hikaripersist.cached.member import CachedMember
from hikaripersist.cached.message import CachedMessage
from hikaripersist.cached.role import CachedRole
from typing import Any

import asyncio
import hikari
import logging

try:
    import aiosqlite
    INSTALLED: bool = True
except ImportError:
    INSTALLED: bool = False

__all__ = ("SQLiteBackend",)

logger: logging.Logger = logging.getLogger("persist.sqlite")

WRITER_THRESHOLD: int = 500

class SQLiteBackend(Backend):
    """Use `SQLite` as the persistent cache backend."""

    VERSION: int = 1
    """The database schema version; updated for automatic migrations."""

    __slots__ = (
        "_connection",
        "_filepath",
        "_queue",
        "_ready",
        "_writer",
    )

    def __init__(
        self,
        filepath: str,
    ) -> None:
        """
        Create a new `SQLite` persistent backend.

        Parameters
        ----------
        filepath : str
            The path to the `SQLite` database file.

        Raises
        ------
        ImportError
            If `aiosqlite` was not installed.
        """

        if not INSTALLED:
            error: str = "SQLiteBackend requires `aiosqlite` to be installed"
            raise ImportError(error)

        self._connection: aiosqlite.Connection | None = None
        self._filepath: str = filepath

        self._writer: asyncio.Task[None] | None = None
        self._queue: asyncio.Queue[
            tuple[str, tuple[Any], asyncio.Future[None] | None]
        ] = asyncio.Queue()

        self._ready: asyncio.Event = asyncio.Event()

    async def __create_schema(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id       INTEGER NOT NULL PRIMARY KEY,
                guild    INTEGER NOT NULL,
                category INTEGER,
                type     INTEGER NOT NULL,
                created  REAL NOT NULL,
                name     TEXT NOT NULL,
                nsfw     INTEGER NOT NULL,
                position INTEGER NOT NULL,
                topic    TEXT
            );
        """)
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS guilds (
                id          INTEGER NOT NULL PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT,
                owner       INTEGER NOT NULL,
                created     REAL NOT NULL
            );
        """)
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id            INTEGER NOT NULL,
                guild         INTEGER NOT NULL,
                username      TEXT NOT NULL,
                discriminator TEXT NOT NULL,
                created       REAL NOT NULL,
                joined        REAL NOT NULL,
                nickname      TEXT,
                roles         TEXT,
                PRIMARY KEY (id, guild)
            );
        """)
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id      INTEGER NOT NULL,
                channel INTEGER NOT NULL,
                guild   INTEGER,
                content TEXT,
                PRIMARY KEY (id, channel)
            );
        """)
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS permission_overwrites (
                channel_id INTEGER NOT NULL,
                target_id  INTEGER NOT NULL,
                type       INTEGER NOT NULL,
                allow      INTEGER NOT NULL,
                deny       INTEGER NOT NULL,
                PRIMARY KEY (channel_id, target_id),
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            );
        """)
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id          INTEGER NOT NULL PRIMARY KEY,
                guild       INTEGER NOT NULL,
                name        TEXT NOT NULL,
                color       INTEGER NOT NULL,
                permissions INTEGER NOT NULL,
                created     REAL NOT NULL,
                position    INTEGER NOT NULL
            );
        """)
        await self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_channels_guild ON channels(guild);"
        )
        await self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_members_guild ON members(guild);"
        )
        await self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel);"
        )
        await self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_roles_guild ON roles(guild);"
        )
        await self._connection.commit()

    async def __execute(
        self,
        execute: str,
        values: tuple[Any],
        confirm: bool = False,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = None
        if confirm:
            future = asyncio.get_running_loop().create_future()

        await self._queue.put((execute, values, future))

        return future

    async def __version_get(self) -> int:
        async with self._connection.execute("PRAGMA user_version;") as cursor:
            row: aiosqlite.Row = await cursor.fetchone()

        return row[0]

    async def __version_migrate(self, current: int) -> None:
        if current > SQLiteBackend.VERSION:
            error: str = "Database schema newer than supported version"
            raise RuntimeError(error)

        if current == 0:
            logger.debug("Database version not found; creating schemas...")

            await self.__create_schema()
            current = SQLiteBackend.VERSION

        #if current < 2:
        #    logger.debug(f"Migrating database: v{current} -> v2")
        #    # steps to migrate to v2, once implemented
        #    current = 2
        # and so on...

        await self._connection.execute(f"PRAGMA user_version = {SQLiteBackend.VERSION};")
        await self._connection.commit()

    async def __writer(self) -> None:
        try:
            while True:
                query: tuple[str, tuple[Any], asyncio.Future[None] | None] = await self._queue.get()
                batch: list[tuple[str, tuple[Any], asyncio.Future[None] | None]] = [query]

                while not self._queue.empty():
                    try:
                        batch.append(self._queue.get_nowait())

                        if len(batch) >= WRITER_THRESHOLD:
                            break
                    except asyncio.QueueEmpty:
                        break

                futures: list[asyncio.Future[None]] = []

                await self._connection.execute("BEGIN")
                for sql, values, future in batch:
                    await self._connection.execute(sql, values)
                    if future:
                        futures.append(future)
                await self._connection.commit()

                for future in futures:
                    if future.done():
                        continue

                    future.set_result(None)
        except asyncio.CancelledError:
            return

    async def connect(self) -> None:
        logger.debug(f"Connecting to SQLite database at {self._filepath}")

        self._connection = await aiosqlite.connect(self._filepath)

        await self._connection.execute("PRAGMA foreign_keys=ON;")
        await self._connection.execute("PRAGMA journal_mode=WAL;")
        await self._connection.execute("PRAGMA synchronous=NORMAL;")
        await self._connection.execute("PRAGMA temp_store=MEMORY;")
        await self._connection.execute("PRAGMA mmap_size=300000000000;")
        await self._connection.commit()

        version: int | None = await self.__version_get()

        if version != SQLiteBackend.VERSION:
            await self.__version_migrate(version)

        self._writer = asyncio.create_task(self.__writer(), name="sqlite-writer")
        self._ready.set()

        logger.info("Connected to SQLite cache database")

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.cancel()

            with suppress(asyncio.CancelledError):
                await self._writer

        remaining: list[tuple[str, tuple[Any]]] = []
        while not self._queue.empty():
            remaining.append(await self._queue.get())

        if remaining:
            async with self._connection.execute("BEGIN"):
                for query in remaining:
                    await self._connection.execute(*query)

                await self._connection.commit()

        await self._connection.close()

        logger.info("Disconnected from SQLite cache database")

    async def get_channel(
        self,
        channel_id: hikari.Snowflake,
    ) -> CachedChannel | None:
        await self._ready.wait()

        async with self._connection.execute(
            "SELECT * FROM channels WHERE id = ?;",
            (channel_id,),
        ) as cursor:
            channel_result: aiosqlite.Row | None = await cursor.fetchone()

        if not channel_result:
            return None

        async with self._connection.execute(
            "SELECT * FROM permission_overwrites WHERE channel_id = ?;",
            (channel_id,),
        ) as cursor:
            permissions_result: Iterable[aiosqlite.Row] = await cursor.fetchall()

        overwrites: dict[hikari.Snowflake, CachedPermissionOverwrite] = {}
        for row in permissions_result:
            overwrites[row[1]] = CachedPermissionOverwrite(
                row[0],
                row[1],
                hikari.PermissionOverwriteType(row[2]),
                hikari.Permissions(row[3]),
                hikari.Permissions(row[4]),
            )

        return CachedChannel(
            channel_result[0],
            channel_result[1],
            channel_result[2],
            hikari.ChannelType(channel_result[3]),
            datetime.fromtimestamp(channel_result[4], timezone.utc),
            channel_result[5],
            bool(channel_result[6]) if channel_result[6] is not None else None,
            channel_result[7],
            channel_result[8],
            overwrites,
        )

    async def get_guild(
        self,
        guild_id: hikari.Snowflake,
    ) -> CachedGuild | None:
        await self._ready.wait()

        async with self._connection.execute(
            "SELECT * FROM guilds WHERE id = ?;",
            (guild_id,),
        ) as cursor:
            result: aiosqlite.Row | None = await cursor.fetchone()

        if not result:
            return None

        return CachedGuild(
            result[0],
            result[1],
            result[2],
            result[3],
            datetime.fromtimestamp(result[4], timezone.utc),
        )

    async def get_member(
        self,
        user_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
    ) -> CachedMember | None:
        await self._ready.wait()

        async with self._connection.execute(
            "SELECT * FROM members WHERE id = ? AND guild = ?;",
            (user_id, guild_id,),
        ) as cursor:
            result: aiosqlite.Row | None = await cursor.fetchone()

        if not result:
            return None

        return CachedMember(
            result[0],
            result[1],
            result[2],
            result[3],
            datetime.fromtimestamp(result[4], timezone.utc),
            datetime.fromtimestamp(result[5], timezone.utc),
            result[6],
            {hikari.Snowflake(role) for role in result[7].split(',')} if result[7] else set(),
        )

    async def get_message(
        self,
        message_id: hikari.Snowflake,
        channel_id: hikari.Snowflake,
    ) -> CachedMessage | None:
        await self._ready.wait()

        async with self._connection.execute(
            "SELECT * FROM messages WHERE id = ? AND channel = ?;",
            (message_id, channel_id,),
        ) as cursor:
            result: aiosqlite.Row | None = await cursor.fetchone()

        if not result:
            return None

        return CachedMessage(*result)

    async def get_role(
        self,
        role_id: hikari.Snowflake,
    ) -> CachedRole | None:
        await self._ready.wait()

        async with self._connection.execute(
            "SELECT * FROM roles WHERE id = ?;",
            (role_id,),
        ) as cursor:
            result: aiosqlite.Row | None = await cursor.fetchone()

        if not result:
            return None

        return CachedRole(
            result[0],
            result[1],
            result[2],
            hikari.Color(result[3]),
            hikari.Permissions(result[4]),
            datetime.fromtimestamp(result[5], timezone.utc),
            result[6],
        )

    async def channel_create(
        self,
        channel: hikari.PermissibleGuildChannel,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        futures: list[asyncio.Future[None]] = []

        confirm_channel: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT INTO channels
                (id, guild, category, type, created, name, nsfw, position, topic)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                channel.id,
                channel.guild_id,
                channel.parent_id,
                int(channel.type),
                channel.created_at.timestamp(),
                channel.name,
                int(channel.is_nsfw),
                channel.position,
                getattr(channel, "topic", None),
            ),
            confirm,
        )

        for overwrite in channel.permission_overwrites.values():
            confirm_overwrite: asyncio.Future[None] | None = await self.__execute(
                """
                    INSERT OR REPLACE INTO permission_overwrites
                    (channel_id, target_id, type, allow, deny)
                    VALUES (?, ?, ?, ?, ?);
                """,
                (
                    channel.id,
                    overwrite.id,
                    int(overwrite.type),
                    int(overwrite.allow),
                    int(overwrite.deny),
                ),
                confirm,
            )

            if confirm:
                futures.append(confirm_overwrite)

        if confirm:
            futures.append(confirm_channel)

            return asyncio.gather(*futures, return_exceptions=True)

        return None

    async def channel_delete(
        self,
        channel_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self.__execute(
            "DELETE FROM channels WHERE id = ?;",
            (channel_id,),
            confirm,
        )

        if confirm:
            return future

        return None

    async def channel_update(
        self,
        channel: hikari.PermissibleGuildChannel,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        futures: list[asyncio.Future[None]] = []

        confirm_channel: asyncio.Future[None] | None = await self.__execute(
            """
                UPDATE channels SET category = ?, name = ?, nsfw = ?, position = ?, topic = ?
                WHERE id = ?;
            """,
            (
                channel.parent_id,
                channel.name,
                int(channel.is_nsfw),
                channel.position,
                getattr(channel, "topic", None),
                channel.id,
            ),
            confirm,
        )

        confirm_delete: asyncio.Future[None] | None = await self.__execute(
            "DELETE FROM permission_overwrites WHERE channel_id = ?;",
            (channel.id,),
            confirm,
        )

        for overwrite in channel.permission_overwrites.values():
            confirm_overwrite: asyncio.Future[None] | None = await self.__execute(
                """
                    INSERT OR REPLACE INTO permission_overwrites
                    (channel_id, target_id, type, allow, deny)
                    VALUES (?, ?, ?, ?, ?);
                """,
                (
                    channel.id,
                    overwrite.id,
                    int(overwrite.type),
                    int(overwrite.allow),
                    int(overwrite.deny),
                ),
                confirm,
            )

            if confirm:
                futures.append(confirm_overwrite)

        if confirm:
            futures.append(confirm_channel)
            futures.append(confirm_delete)

            return asyncio.gather(*futures, return_exceptions=True)

        return None

    async def guild_join(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO guilds
                (id, name, description, owner, created)
                VALUES (?, ?, ?, ?, ?);
            """,
            (
                guild.id,
                guild.name,
                guild.description,
                guild.owner_id,
                guild.created_at.timestamp(),
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
        future: asyncio.Future[None] | None = await self.__execute(
            "UPDATE guilds SET name = ?, description = ? WHERE id = ?;",
            (guild.name, guild.description, guild.id,),
            confirm,
        )

        if confirm:
            return future

        return None

    async def member_create(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO members
                (id, guild, username, discriminator, created, joined, nickname, roles)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                member.id,
                member.guild_id,
                member.username,
                member.discriminator,
                member.created_at.timestamp(),
                member.joined_at.timestamp(),
                member.nickname,
                ','.join(str(role) for role in member.role_ids) if member.role_ids else None,
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def member_delete(
        self,
        user_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self.__execute(
            "DELETE FROM members WHERE id = ? AND guild = ?;",
            (user_id, guild_id,),
            confirm,
        )

        if confirm:
            return future

        return None

    async def member_update(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] = await self.__execute(
            """
                UPDATE members SET username = ?, discriminator = ?, nickname = ?, roles = ?
                WHERE id = ? AND guild = ?;
            """,
            (
                member.username,
                member.discriminator,
                member.nickname,
                ','.join(str(role) for role in member.role_ids) if member.role_ids else None,
                member.id,
                member.guild_id,
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def message_create(
        self,
        message: hikari.Message,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self.__execute(
            "INSERT OR REPLACE INTO messages (id, channel, guild, content) VALUES (?, ?, ?, ?);",
            (
                message.id,
                message.channel_id,
                message.guild_id,
                message.content,
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def message_delete(
        self,
        message_id: hikari.Snowflake,
        channel_id: hikari.Snowflake,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self.__execute(
            "DELETE FROM messages WHERE id = ? AND channel = ?;",
            (message_id, channel_id,),
            confirm,
        )

        if confirm:
            return future

        return None

    async def message_update(
        self,
        message: hikari.PartialMessage,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        fields: list[str] = []
        values: list[object] = []

        if message.content is not hikari.UNDEFINED:
            fields.append("content = ?")
            values.append(message.content)

        if not fields:
            return None

        values.extend((message.id, message.channel_id))

        future: asyncio.Future[None] | None = await self.__execute(
            f"UPDATE messages SET {', '.join(fields)} WHERE id = ? AND channel = ?;",
            tuple(values),
            confirm,
        )

        if confirm:
            return future

        return None

    async def role_create(
        self,
        role: hikari.Role,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO roles
                (id, guild, name, color, permissions, created, position)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                role.id,
                role.guild_id,
                role.name,
                int(role.color),
                int(role.permissions),
                role.created_at.timestamp(),
                role.position,
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
        future: asyncio.Future[None] | None = await self.__execute(
            "UPDATE roles SET name = ?, color = ?, permissions = ?, position = ? WHERE id = ?;",
            (role.name, int(role.color), int(role.permissions), role.position, role.id,),
            confirm,
        )

        if confirm:
            return future

        return None
