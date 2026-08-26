from __future__ import annotations

from collections.abc import (
    AsyncIterator,
    Iterable,
    Sequence,
)
from contextlib import suppress
from .base import (
    Backend,
    SQLBackend,
    SQLOP,
)
from ..impl.objects import (
    PersistentGuild,
    PersistentGuildChannel,
    PersistentMember,
    PersistentRole,
)
from ..internal.builder import build_channel
from ..internal.definitions import DataType
from ..internal.mapping import (
    CHANNEL_WRITE_MAPPERS,
    decode_row,
    GUILD_MAPPER,
    MEMBER_MAPPER,
    ROLE_MAPPER,
    RowMapper,
    USER_MAPPER,
)
from ..internal.schemas import (
    CHANNELS,
    GUILDS,
    MEMBERS,
    ROLES,
    SCHEMA,
    USERS,
)
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    TYPE_CHECKING,
)

import asyncio
import hikari
import hikari.users as hikari_users
import logging

try:
    import aiosqlite
    INSTALLED: bool = True
except ImportError:
    INSTALLED: bool = False

if TYPE_CHECKING:
    from ..internal.common import MaybeFuture
    from ..internal.query import (
        ChannelQuery,
        GuildQuery,
        MemberQuery,
        RoleQuery,
    )


__all__ = ("SQLiteBackend",)

logger: logging.Logger = logging.getLogger("persist.sqlite")


class SQLiteBackend(SQLBackend, Backend):
    """Use `SQLite` as the persistent cache backend."""

    VERSION: int = 1
    """
    The database schema version; updated for automatic migrations.

    Warning
    -------
    Automatic migrations will not occur until `1.0.0`.
    Until then, each update requires a deletion of cache.
    """
    PLACEHOLDER: ClassVar[str] = '?'

    __slots__ = (
        "_backup",
        "_batch_size",
        "_cache",
        "_connection",
        "_connection_file",
        "_db_lock",
        "_filepath",
        "_interval",
        "_queue",
        "_ready",
        "_writer",
    )

    TYPES: ClassVar[dict[DataType, str]] = {
        DataType.BOOLEAN: "INTEGER",
        DataType.BYTES: "BLOB",
        DataType.DATETIME: "REAL",
        DataType.JSON: "TEXT",
        DataType.STRING: "TEXT",

        DataType.TINYINT: "INTEGER",
        DataType.SMALLINT: "INTEGER",
        DataType.INTEGER: "INTEGER",
        DataType.BIGINT: "INTEGER",

        DataType.DECIMAL: "REAL",
        DataType.DOUBLE: "REAL",
        DataType.FLOAT: "REAL",
    }

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
            seconds. Must be `>= 0`.
        batch_size : int
            The size of each batched SQL execution. Iterated reads and writes will occur in batches
            of this amount. Must be `>= 1`.

        Raises
        ------
        ImportError
            If `aiosqlite` is not installed.
        """

        if not INSTALLED:
            error: str = "SQLiteBackend requires `aiosqlite` to be installed"
            raise ImportError(error)

        super().__init__(batch_size)

        self._connection: aiosqlite.Connection | None = None
        self._filepath: Path | str = filepath

        self._writer: asyncio.Task[None] | None = None

        self._connection_file: aiosqlite.Connection | None = None
        self._backup: asyncio.Task[None] | None = None
        self._interval: int = backup_interval

        self._db_lock: asyncio.Lock = asyncio.Lock()

    async def __backup(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._interval)
                await self._connection.backup(self._connection_file)

                logger.debug("Backup of in-memory database to file made")
        except asyncio.CancelledError:
            return

    async def __create_schema(self, db: aiosqlite.Connection) -> None:
        indexes: list[str] = []
        for table in SCHEMA:
            await db.execute(self._ddl_create(table))

            if "_sync" in {f.name for f in table.fields}:
                indexes.append(
                    f"CREATE INDEX IF NOT EXISTS idx_{table.name}_sync ON {table.name}(_sync);",
                )
            if table.name != "guilds" and "guild_id" in {f.name for f in table.fields}:
                indexes.append(
                    f"CREATE INDEX IF NOT EXISTS idx_{table.name}_guild ON {table.name}(guild_id);",
                )

        for stmt in indexes:
            await db.execute(stmt)

        await db.commit()

    async def __drain(self) -> None: # noqa: PLR0912
        remaining: list[SQLOP] = []
        while True:
            try:
                remaining.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        futures: list[asyncio.Future[None]] = []

        try:
            async with self._db_lock:
                await self._connection.execute("BEGIN")
                for op in remaining:
                    match op.mode:
                        case "execute":
                            await self._connection.execute(op.sql, op.parameters)
                        case "executemany":
                            await self._connection.executemany(op.sql, op.parameters)
                        case "multi":
                            for stmt, parameters in zip(op.sql, op.parameters, strict=True):
                                await self._connection.execute(stmt, parameters)

                    if op.future:
                        futures.append(op.future)

                await self._connection.commit()
        except Exception as e:
            with suppress(Exception):
                await self._connection.rollback()

            if not futures:
                logger.exception("SQLite write failed with no confirmation future to report to")

            for future in futures:
                if future.done():
                    continue

                future.set_exception(e)
        else:
            for future in futures:
                if future.done():
                    continue

                future.set_result(None)

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

    async def __writer(self) -> None: # noqa: PLR0912, PLR0915
        try:
            while True:
                operation: SQLOP = await self._queue.get()
                batch: list[SQLOP] = [operation]

                while len(batch) < self._batch_size:
                    try:
                        batch.append(self._queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break

                futures: list[asyncio.Future[None]] = [
                    op.future for op in batch if op.future
                ]

                try:
                    async with self._db_lock:
                        await self._connection.execute("BEGIN")

                        i: int = 0
                        while i < len(batch):
                            op: SQLOP = batch[i]

                            match op.mode:
                                case "execute":
                                    await self._connection.execute(op.sql, op.parameters)
                                case "executemany":
                                    rows: list[tuple[Any, ...]] = list(op.parameters)

                                    j: int = i + 1
                                    while j < len(batch):
                                        nxt: SQLOP = batch[j]

                                        if nxt.mode != "executemany" or nxt.sql != op.sql:
                                            break

                                        rows.extend(nxt.parameters)
                                        j += 1

                                    await self._connection.executemany(op.sql, rows)
                                    i = j - 1
                                case "multi":
                                    for stmt, parameters in zip(op.sql, op.parameters, strict=True):
                                        await self._connection.execute(stmt, parameters)

                            i += 1

                        await self._connection.commit()
                except Exception as e:
                    with suppress(Exception):
                        await self._connection.rollback()

                    if not futures:
                        logger.exception("SQLite write failed with no confirmation future to report to") # noqa: E501

                    for future in futures:
                        if future.done():
                            continue

                        future.set_exception(e)
                else:
                    for future in futures:
                        if future.done():
                            continue

                        future.set_result(None)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Writer crashed")
            raise

    def _sql_upsert_replace(self, table_name: str, field_names: Sequence[str]) -> str:
        placeholder: str = ", ".join(['?'] * len(field_names))
        return f"INSERT OR REPLACE INTO {table_name} ({', '.join(field_names)}) VALUES ({placeholder});" # noqa: E501

    async def bulk_channels(
        self,
        channels: Sequence[hikari.GuildChannel],
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        if not channels:
            return None

        if len(channels) == 1:
            return await self.channel_create(channels[0], confirm)

        futures: list[asyncio.Future[None]] = []
        by_type: dict[hikari.ChannelType, list[hikari.GuildChannel]] = {}
        for c in channels:
            by_type.setdefault(c.type, []).append(c)

        for ctype, group in by_type.items():
            mapper: RowMapper = CHANNEL_WRITE_MAPPERS[ctype]
            rows: list[str] = [mapper.to_row(c, sync=self._cache._sync) for c in group]
            sql: str = self._sql_upsert_replace("channels", mapper.names)
            future: MaybeFuture = await self._executemany(sql, rows, confirm)

            if future:
                futures.append(future)

        if confirm:
            return await asyncio.gather(*futures, return_exceptions=True)

        return None

    async def bulk_members(
        self,
        members: Iterable[hikari.Member],
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        mm, um = MEMBER_MAPPER, USER_MAPPER
        member_rows: list[tuple[Any, ...]] = []
        user_rows: list[tuple[Any, ...]] = []

        for member in members:
            member_rows.append(mm.to_row(member, sync=self._cache._sync))
            user_rows.append(um.to_row(member.user, sync=self._cache._sync))

        if not member_rows:
            return None

        futures: list[asyncio.Future[None]] = []

        m_sql: str = self._sql_upsert_replace("members", mm.names)
        future: MaybeFuture = await self._executemany(m_sql, member_rows, confirm)

        if future:
            futures.append(future)

        u_sql: str = self._sql_upsert_replace("users", um.names)
        future: MaybeFuture = await self._executemany(u_sql, user_rows, confirm)

        if future:
            futures.append(future)

        if confirm:
            return await asyncio.gather(*futures, return_exceptions=True)

        return None

    async def bulk_roles(
        self,
        roles: Iterable[hikari.Role],
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        mapper: RowMapper = ROLE_MAPPER
        rows: list[tuple[Any, ...]] = [mapper.to_row(r, sync=self._cache._sync) for r in roles]

        if not rows:
            return None

        sql: str = self._sql_upsert_replace("roles", mapper.names)
        return await self._executemany(sql, rows, confirm)

    async def channel_create(
        self,
        channel: hikari.GuildChannel,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        mapper: RowMapper = CHANNEL_WRITE_MAPPERS[channel.type]
        sql: str = self._sql_upsert_replace("channels", mapper.names)

        return await self._execute(sql, mapper.to_row(channel, sync=self._cache._sync), confirm)

    async def channel_delete(
        self,
        channel_id: hikari.Snowflake,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()
        return await self._execute(self._sql_delete("channels", ("id",)), (channel_id,), confirm)

    async def channel_update(
        self,
        channel: hikari.GuildChannel,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        mapper: RowMapper = CHANNEL_WRITE_MAPPERS[channel.type]
        values = (*mapper.to_row(channel, sync=self._cache._sync), channel.id)
        sql: str = self._sql_update("channels", mapper.names, ("id",))

        return await self._execute(sql, values, confirm)

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

        await self.__drain()

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
    ) -> MaybeFuture:
        await self._ready.wait()

        mapper: RowMapper = GUILD_MAPPER
        sql: str = self._sql_upsert_replace("guilds", mapper.names)

        return await self._execute(sql, mapper.to_row(guild, sync=self._cache._sync), confirm)

    async def guild_leave(
        self,
        guild_id: hikari.Snowflake,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        sql: str = self._sql_delete("guilds", ("id",))
        return await self._execute(sql, (guild_id,), confirm)

    async def guild_update(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        set_fields: tuple[str, ...] = tuple(f for f in GUILDS.fields if f.name != "id")
        set_mapper: RowMapper = RowMapper(GUILDS, factory=None, fields=set_fields)

        sql: str = self._sql_update("guilds", set_mapper.names, ("id",))
        values: tuple[Any, ...] = (*set_mapper.to_row(guild, sync=self._cache._sync), guild.id)

        return await self._execute(sql, values, confirm)

    async def iter_channels(
        self,
        query: ChannelQuery | None,
    ) -> AsyncIterator[PersistentGuildChannel]:
        await self._ready.wait()

        sql: str = "SELECT * FROM channels"
        params: tuple[Any, ...] = ()

        if query:
            conditions, params = self._build_query(query)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        type_idx: int = next(i for i, f in enumerate(CHANNELS.fields) if f.name == "type")

        async with self._connection.execute(sql, params) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(self._batch_size)

                if not rows:
                    break

                for row in rows:
                    ctype: hikari.ChannelType = hikari.ChannelType(row[type_idx])
                    kwargs: dict[str, Any] = decode_row(CHANNELS.fields, row)
                    del kwargs["_sync"]
                    yield build_channel(self._cache, ctype, kwargs)

    async def iter_guilds(
        self,
        query: GuildQuery | None,
    ) -> AsyncIterator[PersistentGuild]:
        await self._ready.wait()

        sql: str = "SELECT * FROM guilds"
        params: tuple[Any, ...] = ()

        if query:
            conditions, params = self._build_query(query)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._connection.execute(sql, params) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(self._batch_size)

                if not rows:
                    break

                for row in rows:
                    kwargs: dict[str, Any] = decode_row(GUILDS.fields, row)
                    del kwargs["_sync"]
                    yield PersistentGuild(self._cache, **kwargs)

    async def iter_members(
        self,
        query: MemberQuery | None,
    ) -> AsyncIterator[PersistentMember]:
        await self._ready.wait()

        sql: str = "SELECT * FROM members"
        params: tuple[Any, ...] = ()

        if query:
            conditions, params = self._build_query(query)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._connection.execute(sql, params) as cursor:
            while True:
                members: Iterable[aiosqlite.Row] = await cursor.fetchmany(self._batch_size)

                if not members:
                    break

                async with self._connection.execute(
                    f"SELECT * FROM users WHERE id IN ({','.join('?' * len(members))});",
                    tuple(m[0] for m in members),
                ) as ucursor:
                    user_rows: Iterable[aiosqlite.Row] = await ucursor.fetchall()

                users_by_id: dict[hikari.Snowflake, dict[str, Any]] = {
                    row[0]: decode_row(USERS.fields, row) for row in user_rows
                }

                for row in members:
                    ukwargs: dict[str, Any] = users_by_id.get(row[0])

                    if not ukwargs:
                        logger.warning(
                            "Member has no cached user object, discarding; ID=%s",
                            row[0],
                        )
                        continue

                    del ukwargs["_sync"]

                    mkwargs: dict[str, Any] = decode_row(MEMBERS.fields, row)
                    user: hikari.User = hikari_users.UserImpl(app=self._cache._bot, **ukwargs)

                    del mkwargs["_sync"]
                    del mkwargs["id"]
                    yield PersistentMember(
                        self._cache,
                        user=user,
                        is_deaf=hikari.UNDEFINED,
                        is_mute=hikari.UNDEFINED,
                        is_pending=hikari.UNDEFINED,
                        **mkwargs,
                    )

    async def iter_roles(
        self,
        query: RoleQuery | None,
    ) -> AsyncIterator[PersistentRole]:
        await self._ready.wait()

        sql: str = "SELECT * FROM roles"
        params: tuple[Any, ...] = ()

        if query:
            conditions, params = self._build_query(query)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._connection.execute(sql, params) as cursor:
            while True:
                rows: Iterable[aiosqlite.Row] = await cursor.fetchmany(self._batch_size)

                if not rows:
                    break

                for row in rows:
                    kwargs: dict[str, Any] = decode_row(ROLES.fields, row)
                    del kwargs["_sync"]
                    yield PersistentRole(self._cache, **kwargs)

    async def member_create(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        mm, um = MEMBER_MAPPER, USER_MAPPER
        m_sql: str = self._sql_upsert_replace("members", mm.names)
        u_sql: str = self._sql_upsert_replace("users", um.names)

        return await self._executemulti(
            (
                (m_sql, mm.to_row(member, sync=self._cache._sync)),
                (u_sql, um.to_row(member.user, sync=self._cache._sync)),
            ),
            confirm,
        )

    async def member_delete(
        self,
        user_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        m_sql: str = self._sql_delete("members", ("id", "guild_id"))
        u_sql: str = (
            "DELETE FROM users WHERE id = ? AND NOT EXISTS "
            "(SELECT 1 FROM members WHERE id = ?);"
        )

        return await self._executemulti(
            (
                (m_sql, (user_id, guild_id)),
                (u_sql, (user_id, user_id)),
            ),
            confirm,
        )

    async def member_update(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        m_fields: tuple[str, ...] = tuple(
            f for f in MEMBERS.fields if f.name not in ("id", "guild_id")
        )
        m_mapper: RowMapper = RowMapper(MEMBERS, factory=None, fields=m_fields)
        m_sql: str = self._sql_update("members", m_mapper.names, ("id", "guild_id"))
        m_values: tuple[Any, ...] = (
            *m_mapper.to_row(member, sync=self._cache._sync), member.id, member.guild_id
        )

        u_fields: tuple[str, ...] = tuple(
            f for f in USERS.fields if f.name != "id"
        )
        u_mapper: RowMapper = RowMapper(USERS, factory=None, fields=u_fields)
        u_sql: str = self._sql_update("users", u_mapper.names, ("id",))
        u_values: tuple[Any, ...] = (
            *u_mapper.to_row(member.user, sync=self._cache._sync), member.id
        )

        return await self._executemulti(
            (
                (m_sql, m_values),
                (u_sql, u_values),
            ),
            confirm,
        )

    async def prune(self) -> None:
        await self._ready.wait()

        async with self._db_lock:
            await self._connection.execute("BEGIN;")
            for table in SCHEMA:
                if "_sync" not in {f.name for f in table.fields}:
                    continue

                await self._connection.execute(
                    f"DELETE FROM {table.name} WHERE _sync != ?;",
                    (self._cache._sync,),
                )

            await self._connection.commit()

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

        await self.__drain()

        await backup.backup(self._connection)
        await backup.close()

        logger.info("Restored database from %s", str(path))

    async def role_create(
        self,
        role: hikari.Role,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        mapper: RowMapper = ROLE_MAPPER
        sql: str = self._sql_upsert_replace("roles", mapper.names)

        return await self._execute(sql, mapper.to_row(role, sync=self._cache._sync), confirm)

    async def role_delete(
        self,
        role_id: hikari.Snowflake,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        sql: str = self._sql_delete("roles", ("id",))
        return await self._execute(sql, (role_id,), confirm)

    async def role_update(
        self,
        role: hikari.Role,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        set_fields: tuple[str, ...] = tuple(f for f in ROLES.fields if f.name != "id")
        set_mapper: RowMapper = RowMapper(ROLES, factory=None, fields=set_fields)

        sql: str = self._sql_update("roles", set_mapper.names, ("id",))
        values: tuple[Any, ...] = (*set_mapper.to_row(role, sync=self._cache._sync), role.id)

        return await self._execute(sql, values, confirm)

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
            temp.unlink(True)
            return

        temp.rename(path)

        logger.info("Database snapshot to %s", str(path))
