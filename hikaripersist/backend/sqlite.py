from __future__ import annotations

from collections.abc import (
    AsyncIterator,
    Iterable,
)
from contextlib import suppress
from hikaripersist.backend.base import Backend
from hikaripersist.cached.channel import (
    CachedChannel,
    CachedPermissionOverwrite,
)
from hikaripersist.cached.guild import CachedGuild
from hikaripersist.cached.member import CachedMember
from hikaripersist.cached.message import CachedMessage
from hikaripersist.cached.role import CachedRole
from typing import Any, TYPE_CHECKING

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
        ChannelQuery,
        GuildQuery,
        MemberQuery,
        MessageQuery,
        RoleQuery,
    )

__all__ = ("SQLiteBackend",)

logger: logging.Logger = logging.getLogger("persist.sqlite")

BATCH_SIZE_NORMAL: int = 100
BATCH_SIZE_STARTUP: int = 1000

MAX_VARIABLES: int = 999

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
                created     REAL NOT NULL,
                icon        TEXT,
                banner      TEXT,
                nsfw        INTEGER NOT NULL,
                mfa         INTEGER NOT NULL,
                verification INTEGER NOT NULL,
                features     TEXT,
                vanity       TEXT,
                premium      INTEGER NOT NULL
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
                avatar        TEXT NOT NULL,
                banner        TEXT,
                name          TEXT NOT NULL,
                flags         INTEGER NOT NULL,
                bot           INTEGER NOT NULL,
                system        INTEGER NOT NULL,
                roles         TEXT,
                premium_since REAL,
                timeout       REAL,
                PRIMARY KEY (id, guild)
            );
        """)
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id      INTEGER NOT NULL,
                channel INTEGER NOT NULL,
                guild   INTEGER NOT NULL,
                author  INTEGER NOT NULL,
                created REAL NOT NULL,
                pinned  INTEGER NOT NULL,
                content TEXT,
                edited  REAL,
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
                icon        TEXT,
                permissions INTEGER NOT NULL,
                created     REAL NOT NULL,
                position    INTEGER NOT NULL,
                hoisted     INTEGER NOT NULL,
                bot         INTEGER,
                premium     INTEGER NOT NULL
            );
        """)
        await self._connection.executescript("""
            CREATE INDEX IF NOT EXISTS idx_channels_guild ON channels(guild);
            CREATE INDEX IF NOT EXISTS idx_members_guild ON members(guild);
            CREATE INDEX IF NOT EXISTS idx_roles_guild ON roles(guild);

            CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel);
            CREATE INDEX IF NOT EXISTS idx_messages_guild ON messages(guild);
            CREATE INDEX IF NOT EXISTS idx_messages_author ON messages(author);
            CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created);
        """)
        await self._connection.execute(
            "CREATE VIRTUAL TABLE message_fts USING fts5(content);"
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

                        if len(batch) >= BATCH_SIZE_NORMAL:
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

    async def guild_join(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO guilds
                (
                    id,
                    name,
                    description,
                    owner,
                    created,
                    icon,
                    banner,
                    nsfw,
                    mfa,
                    verification,
                    features,
                    vanity,
                    premium
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                guild.id,
                guild.name,
                guild.description,
                guild.owner_id,
                guild.created_at.timestamp(),
                guild.icon_hash,
                guild.banner_hash,
                int(guild.nsfw_level),
                int(guild.mfa_level),
                int(guild.verification_level),
                ','.join(str(feature) for feature in guild.features) if guild.features else None,
                guild.vanity_url_code,
                int(guild.premium_tier),
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
            """
                UPDATE guilds SET
                name = ?,
                description = ?,
                icon = ?,
                banner = ?,
                nsfw = ?,
                mfa = ?,
                verification = ?,
                features = ?,
                vanity = ?,
                premium = ?
                WHERE id = ?;
            """,
            (
                guild.name,
                guild.description,
                guild.icon_hash,
                guild.banner_hash,
                int(guild.nsfw_level),
                int(guild.mfa_level),
                int(guild.verification_level),
                ','.join(str(feature) for feature in guild.features) if guild.features else None,
                guild.vanity_url_code,
                int(guild.premium_tier),

                guild.id,
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def iter_channels( # noqa: PLR0912, PLR0915
        self,
        query: ChannelQuery,
    ) -> AsyncIterator[CachedChannel]:
        await self._ready.wait()

        sql: str = "SELECT * FROM channels"
        conditions: list[str] = []
        params: list[object] = []

        if query._category is not None:
            conditions.append("category = ?")
            params.append(query._category)

        if query._channel_id is not None:
            conditions.append("id = ?")
            params.append(query._channel_id)

        if query._created_after is not None:
            conditions.append("created > ?")
            params.append(query._created_after.timestamp())

        if query._created_before is not None:
            conditions.append("created < ?")
            params.append(query._created_before.timestamp())

        if query._guild_id is not None:
            conditions.append("guild = ?")
            params.append(query._guild_id)

        if query._name is not None:
            conditions.append("name = ?")
            params.append(query._name)

        if query._nsfw is not None:
            conditions.append("nsfw = ?")
            params.append(int(query._nsfw))

        if query._position is not None:
            conditions.append("position = ?")
            params.append(query._position)

        if query._topic is not None:
            conditions.append("topic LIKE ?")
            params.append(f"%{query._topic}%")

        if query._type is not None:
            conditions.append("type = ?")
            params.append(int(query._type))

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        if query._limit is not None:
            sql += " LIMIT ?"
            params.append(query._limit)

        sql += ';'

        batch: int = BATCH_SIZE_NORMAL
        if query._limit is not None:
            batch = min(batch, query._limit)

        async with self._connection.execute(sql, tuple(params)) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(batch)
                if not rows:
                    break

                for row in rows:
                    async with self._connection.execute(
                        "SELECT * FROM permission_overwrites WHERE channel_id = ?;",
                        (row[0],),
                    ) as pcursor:
                        presult: Iterable[aiosqlite.Row] = await pcursor.fetchall()

                    overwrites: dict[hikari.Snowflake, hikari.PermissionOverwrite] = {
                        r[1]: CachedPermissionOverwrite.from_sqlite(r) for r in presult
                    }
                    yield CachedChannel.from_sqlite(row, overwrites)

    async def iter_guilds( # noqa: PLR0912, PLR0915
        self,
        query: GuildQuery,
    ) -> AsyncIterator[CachedGuild]:
        await self._ready.wait()

        sql: str = "SELECT * FROM guilds"
        conditions: list[str] = []
        params: list[object] = []

        if query._created_after is not None:
            conditions.append("created > ?")
            params.append(query._created_after.timestamp())

        if query._created_before is not None:
            conditions.append("created < ?")
            params.append(query._created_before.timestamp())

        if query._description is not None:
            conditions.append("description LIKE ?")
            params.append(f"%{query._description}%")

        if query._guild_id is not None:
            conditions.append("id = ?")
            params.append(query._guild_id)

        if query._name is not None:
            conditions.append("name = ?")
            params.append(query._name)

        if query._nsfw is not None:
            conditions.append("nsfw = ?")
            params.append(int(query._nsfw))

        if query._mfa is not None:
            conditions.append("mfa = ?")
            params.append(int(query._mfa))

        if query._owner_id is not None:
            conditions.append("owner = ?")
            params.append(query._owner_id)

        if query._premium is not None:
            conditions.append("premium = ?")
            params.append(int(query._premium))

        if query._vanity is not None:
            conditions.append("vanity = ?")
            params.append(query._vanity)

        if query._verification is not None:
            conditions.append("verification = ?")
            params.append(int(query._verification))

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        if query._limit is not None:
            sql += " LIMIT ?"
            params.append(query._limit)

        sql += ';'

        batch: int = BATCH_SIZE_NORMAL
        if query._limit is not None:
            batch = min(batch, query._limit)

        async with self._connection.execute(sql, tuple(params)) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(batch)
                if not rows:
                    break

                for row in rows:
                    yield CachedGuild.from_sqlite(row)

    async def iter_members( # noqa: PLR0912, PLR0915
        self,
        query: MemberQuery,
    ) -> AsyncIterator[CachedMember]:
        await self._ready.wait()

        sql: str = "SELECT * FROM members"
        conditions: list[str] = []
        params: list[object] = []

        if query._boosting_after is not None:
            conditions.append("premium_since > ?")
            params.append(query._boosting_after.timestamp())

        if query._boosting_before is not None:
            conditions.append("premium_since < ?")
            params.append(query._boosting_before.timestamp())

        if query._bot is not None:
            conditions.append("bot = ?")
            params.append(int(query._bot))

        if query._discriminator is not None:
            conditions.append("discriminator = ?")
            params.append(query._discriminator)

        if query._created_after is not None:
            conditions.append("created > ?")
            params.append(query._created_after.timestamp())

        if query._created_before is not None:
            conditions.append("created < ?")
            params.append(query._created_before.timestamp())

        if query._flags is not None:
            conditions.append("flags = ?")
            params.append(int(query._flags))

        if query._guild_id is not None:
            conditions.append("guild = ?")
            params.append(query._guild_id)

        if query._joined_after is not None:
            conditions.append("joined > ?")
            params.append(query._joined_after.timestamp())

        if query._joined_before is not None:
            conditions.append("joined < ?")
            params.append(query._joined_before.timestamp())

        if query._member_id is not None:
            conditions.append("id = ?")
            params.append(query._member_id)

        if query._name is not None:
            conditions.append("name = ?")
            params.append(query._name)

        if query._system is not None:
            conditions.append("system = ?")
            params.append(int(query._system))

        if query._timed_out is not None:
            if query._timed_out:
                conditions.append("timeout IS NOT NULL")
            else:
                conditions.append("timeout IS NULL")

        if query._username is not None:
            conditions.append("username = ?")
            params.append(query._username)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        if query._limit is not None:
            sql += " LIMIT ?"
            params.append(query._limit)

        sql += ';'

        batch: int = BATCH_SIZE_NORMAL
        if query._limit is not None:
            batch = min(batch, query._limit)

        async with self._connection.execute(sql, tuple(params)) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(batch)
                if not rows:
                    break

                for row in rows:
                    yield CachedMember.from_sqlite(row)

    async def iter_messages( # noqa: PLR0912, PLR0915
        self,
        query: MessageQuery,
    ) -> AsyncIterator[CachedMessage]:
        await self._ready.wait()

        sql: str = ''
        conditions: list[str] = []
        params: list[object] = []

        if query._contains is not None:
            sql = (
                "SELECT messages.* FROM messages "
                "JOIN message_fts ON messages.id = message_fts.rowid"
            )
            conditions.append("message_fts MATCH ?")
            params.append(query._contains)
        else:
            sql = "SELECT * FROM messages"

        if query._author_id is not None:
            conditions.append("author = ?")
            params.append(query._author_id)

        if query._channel_id is not None:
            conditions.append("channel = ?")
            params.append(query._channel_id)

        if query._created_after is not None:
            conditions.append("created > ?")
            params.append(query._created_after.timestamp())

        if query._created_before is not None:
            conditions.append("created < ?")
            params.append(query._created_before.timestamp())

        if query._edited_after is not None:
            conditions.append("edited > ?")
            params.append(query._edited_after.timestamp())

        if query._edited_before is not None:
            conditions.append("edited < ?")
            params.append(query._edited_before.timestamp())

        if query._guild_id is not None:
            conditions.append("guild = ?")
            params.append(query._guild_id)

        if query._message_id is not None:
            conditions.append("id = ?")
            params.append(query._message_id)

        if query._pinned is not None:
            conditions.append("pinned = ?")
            params.append(int(query._pinned))

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        if query._limit is not None:
            sql += " LIMIT ?"
            params.append(query._limit)

        sql += ';'

        batch: int = BATCH_SIZE_NORMAL
        if query._limit is not None:
            batch = min(batch, query._limit)

        async with self._connection.execute(sql, tuple(params)) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(batch)
                if not rows:
                    break

                for row in rows:
                    yield CachedMessage.from_sqlite(row)

    async def iter_roles( # noqa: PLR0912, PLR0915
        self,
        query: RoleQuery,
    ) -> AsyncIterator[CachedRole]:
        await self._ready.wait()

        sql: str = "SELECT * FROM roles"
        conditions: list[str] = []
        params: list[object] = []

        if query._color is not None:
            conditions.append("color = ?")
            params.append(int(query._color))

        if query._created_after is not None:
            conditions.append("created > ?")
            params.append(query._created_after.timestamp())

        if query._created_before is not None:
            conditions.append("created < ?")
            params.append(query._created_before.timestamp())

        if query._guild_id is not None:
            conditions.append("guild = ?")
            params.append(query._guild_id)

        if query._hoisted is not None:
            conditions.append("hoisted = ?")
            params.append(int(query._hoisted))

        if query._managed is not None:
            if query._managed:
                conditions.append("bot IS NOT NULL")
            else:
                conditions.append("bot IS NULL")

        if query._name is not None:
            conditions.append("name = ?")
            params.append(query._name)

        if query._permissions is not None:
            conditions.append("permissions = ?")
            params.append(int(query._permissions))

        if query._position is not None:
            conditions.append("position = ?")
            params.append(query._position)

        if query._premium is not None:
            conditions.append("premium = ?")
            params.append(int(query._premium))

        if query._role_id is not None:
            conditions.append("id = ?")
            params.append(query._role_id)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        if query._limit is not None:
            sql += " LIMIT ?"
            params.append(query._limit)

        sql += ';'

        batch: int = BATCH_SIZE_NORMAL
        if query._limit is not None:
            batch = min(batch, query._limit)

        async with self._connection.execute(sql, tuple(params)) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(batch)
                if not rows:
                    break

                for row in rows:
                    yield CachedRole.from_sqlite(row)

    async def member_create(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        comm_disabled = member.communication_disabled_until()

        future: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO members
                (
                    id,
                    guild,
                    username,
                    discriminator,
                    created,
                    joined,
                    avatar,
                    banner,
                    name,
                    flags,
                    bot,
                    system,
                    roles,
                    premium_since,
                    timeout
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                member.id,
                member.guild_id,
                member.username,
                member.discriminator,
                member.created_at.timestamp(),
                member.joined_at.timestamp(),
                str(member.display_avatar_url),
                str(member.display_banner_url) if member.display_banner_url else None,
                member.display_name,
                int(member.flags),
                int(member.is_bot),
                int(member.is_system),
                ','.join(str(role) for role in member.role_ids) if member.role_ids else None,
                member.premium_since.timestamp() if member.premium_since else None,
                comm_disabled.timestamp() if comm_disabled else None,
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
        comms_disabled = member.communication_disabled_until()

        future: asyncio.Future[None] = await self.__execute(
            """
                UPDATE members SET
                username = ?,
                discriminator = ?,
                avatar = ?,
                banner = ?,
                name = ?,
                flags = ?,
                roles = ?,
                premium_since = ?,
                timeout = ?
                WHERE id = ? AND guild = ?;
            """,
            (
                member.username,
                member.discriminator,
                str(member.display_avatar_url),
                str(member.display_banner_url) if member.display_banner_url else None,
                member.display_name,
                int(member.flags),
                ','.join(str(role) for role in member.role_ids) if member.role_ids else None,
                member.premium_since.timestamp() if member.premium_since else None,
                comms_disabled.timestamp() if comms_disabled else None,

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
            """
                INSERT OR REPLACE INTO messages (
                    id,
                    channel,
                    guild,
                    author,
                    created,
                    pinned,
                    content,
                    edited
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                message.id,
                message.channel_id,
                message.guild_id,
                message.author.id,
                message.created_at.timestamp(),
                int(message.is_pinned),
                message.content,
                message.edited_timestamp.timestamp() if message.edited_timestamp else None,
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

        if message.is_pinned is not hikari.UNDEFINED:
            fields.append("pinned = ?")
            values.append(message.is_pinned)

        if message.content is not hikari.UNDEFINED:
            fields.append("content = ?")
            values.append(message.content)

        if message.edited_timestamp is not hikari.UNDEFINED:
            fields.append("edited = ?")
            values.append(
                message.edited_timestamp.timestamp()
                if message.edited_timestamp else None
            )

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
                (
                    id,
                    guild,
                    name,
                    color,
                    icon,
                    permissions,
                    created,
                    position,
                    hoisted,
                    bot,
                    premium
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                role.id,
                role.guild_id,
                role.name,
                int(role.color),
                role.icon_hash,
                int(role.permissions),
                role.created_at.timestamp(),
                role.position,
                int(role.is_hoisted),
                int(role.bot_id) if role.bot_id is not None else None,
                int(role.is_premium_subscriber_role),
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
            """
            UPDATE roles SET
                name = ?,
                color = ?,
                icon = ?,
                permissions = ?,
                position = ?,
                hoisted = ?
            WHERE id = ?;
            """,
            (
                role.name,
                int(role.color),
                role.icon_hash,
                int(role.permissions),
                role.position,
                int(role.is_hoisted),

                role.id,
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def startup_guild(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self.__execute(
            """
                INSERT OR REPLACE INTO guilds
                (
                    id,
                    name,
                    description,
                    owner,
                    created,
                    icon,
                    banner,
                    nsfw,
                    mfa,
                    verification,
                    features,
                    vanity,
                    premium
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                guild.id,
                guild.name,
                guild.description,
                guild.owner_id,
                guild.created_at.timestamp(),
                guild.icon_hash,
                guild.banner_hash,
                int(guild.nsfw_level),
                int(guild.mfa_level),
                int(guild.verification_level),
                ','.join(str(feature) for feature in guild.features) if guild.features else None,
                guild.vanity_url_code,
                int(guild.premium_tier),
            ),
            confirm,
        )

        if confirm:
            return future

        return None

    async def startup_guild_channels(
        self,
        channels: Iterable[hikari.PermissibleGuildChannel],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        channel_rows: list[tuple] = []
        overwrite_rows: list[tuple] = []

        for channel in channels:
            channel_rows.append((
                channel.id,
                channel.guild_id,
                channel.parent_id,
                int(channel.type),
                channel.created_at.timestamp(),
                channel.name,
                int(channel.is_nsfw),
                channel.position,
                getattr(channel, "topic", None),
            ))

            for overwrite in channel.permission_overwrites.values():
                overwrite_rows.append((
                    channel.id,
                    overwrite.id,
                    int(overwrite.type),
                    int(overwrite.allow),
                    int(overwrite.deny),
                ))

        if not channel_rows:
            return None

        future: asyncio.Future[None] | None = (
            asyncio.get_running_loop().create_future() if confirm else None
        )

        async with self._connection.execute("BEGIN"):
            await self._connection.executemany(
                """
                    INSERT OR REPLACE INTO channels
                    (id, guild, category, type, created, name, nsfw, position, topic)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                channel_rows,
            )

            if overwrite_rows:
                await self._connection.executemany(
                    """
                        INSERT OR REPLACE INTO permission_overwrites
                        (channel_id, target_id, type, allow, deny)
                        VALUES (?, ?, ?, ?, ?);
                    """,
                    overwrite_rows,
                )

            await self._connection.commit()

        if future:
            future.set_result(None)

        return future

    async def startup_guild_members(
        self,
        members: Iterable[hikari.Member],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        rows: list[tuple] = []

        for member in members:
            comm_disabled = member.communication_disabled_until()

            rows.append((
                member.id,
                member.guild_id,
                member.username,
                member.discriminator,
                member.created_at.timestamp(),
                member.joined_at.timestamp(),
                str(member.display_avatar_url),
                str(member.display_banner_url) if member.display_banner_url else None,
                member.display_name,
                int(member.flags),
                int(member.is_bot),
                int(member.is_system),
                ','.join(str(role) for role in member.role_ids) if member.role_ids else None,
                member.premium_since.timestamp() if member.premium_since else None,
                comm_disabled.timestamp() if comm_disabled else None,
            ))

        if not rows:
            return None

        future: asyncio.Future[None] | None = (
            asyncio.get_running_loop().create_future() if confirm else None
        )

        async with self._connection.execute("BEGIN"):
            await self._connection.executemany(
                """
                    INSERT OR REPLACE INTO members
                    (
                        id,
                        guild,
                        username,
                        discriminator,
                        created,
                        joined,
                        avatar,
                        banner,
                        name,
                        flags,
                        bot,
                        system,
                        roles,
                        premium_since,
                        timeout
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                rows,
            )
            await self._connection.commit()

        if future:
            future.set_result(None)

        return future

    async def startup_guild_roles(
        self,
        roles: Iterable[hikari.Role],
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        rows: list[tuple] = []

        for role in roles:
            rows.append((
                role.id,
                role.guild_id,
                role.name,
                int(role.color),
                role.icon_hash,
                int(role.permissions),
                role.created_at.timestamp(),
                role.position,
                int(role.is_hoisted),
                int(role.bot_id) if role.bot_id is not None else None,
                int(role.is_premium_subscriber_role),
            ))

        if not rows:
            return None

        future: asyncio.Future[None] | None = (
            asyncio.get_running_loop().create_future() if confirm else None
        )

        async with self._connection.execute("BEGIN"):
            await self._connection.executemany(
                """
                    INSERT OR REPLACE INTO roles
                    (
                        id,
                        guild,
                        name,
                        color,
                        icon,
                        permissions,
                        created,
                        position,
                        hoisted,
                        bot,
                        premium
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                rows,
            )
            await self._connection.commit()

        if future:
            future.set_result(None)

        return future
