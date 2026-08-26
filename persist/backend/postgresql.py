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
from ..internal.builder import _build_channel
from ..internal.definitions import (
    DataType,
    Table,
)
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
from datetime import timedelta
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
    import asyncpg
    import asyncpg.cursor as asyncpg_cursor
    INSTALLED: bool = True
except ImportError:
    INSTALLED: bool = False

if TYPE_CHECKING:
    from ..internal.common import MaybeFuture
    from ..internal.query import (
        BaseQuery,
        ChannelQuery,
        GuildQuery,
        MemberQuery,
        RoleQuery,
    )


__all__ = ("PostgreSQLBackend",)

logger: logging.Logger = logging.getLogger("persist.postgresql")

_TRANSIENT_ERRORS: tuple[type[BaseException], ...] = ()
if INSTALLED:
    _TRANSIENT_ERRORS = (
        asyncpg.PostgresConnectionError,
        asyncpg.TooManyConnectionsError,
        ConnectionResetError,
        ConnectionRefusedError,
        OSError,
    )

_META_TABLE: str = "_persist_meta"

class PostgreSQLBackend(SQLBackend, Backend):
    """Use `PostgreSQL` as the persistent cache backend."""

    VERSION: int = 1
    """
    The database schema version; updated for automatic migrations.

    Warning
    -------
    Automatic migrations will not occur until `1.0.0`.
    Until then, each update requires a deletion of cache.
    """
    PLACEHOLDER: ClassVar[str] = "$"

    __slots__ = (
        "_batch_size",
        "_cache",
        "_command_timeout",
        "_dsn",
        "_interval",
        "_max_inactive_lifetime",
        "_max_size",
        "_min_size",
        "_pool",
        "_queue",
        "_ready",
        "_ssl",
        "_statement_cache_size",
        "_writer",
    )

    TYPES: ClassVar[dict[DataType, str]] = {
        DataType.BOOLEAN: "SMALLINT",
        DataType.BYTES: "BYTEA",
        DataType.DATETIME: "DOUBLE PRECISION",
        DataType.JSON: "JSONB",
        DataType.STRING: "TEXT",

        DataType.TINYINT: "SMALLINT",
        DataType.SMALLINT: "SMALLINT",
        DataType.INTEGER: "INTEGER",
        DataType.BIGINT: "BIGINT",

        DataType.DECIMAL: "NUMERIC",
        DataType.DOUBLE: "DOUBLE PRECISION",
        DataType.FLOAT: "REAL",
    }

    def __init__( # noqa: PLR0913
        self,
        dsn: str,
        *,
        min_size: int = 10,
        max_size: int = 20,
        command_timeout: float | None = 60.0,
        max_inactive_connection_lifetime: float = 300.0,
        statement_cache_size: int = 1024,
        ssl: Any | None = None, # noqa: ANN401
        batch_size: int = 100,
    ) -> None:
        """
        Create a new `PostgreSQL` persistent backend.

        Parameters
        ----------
        dsn : str
            The connection string/DSN, e.g. `postgresql://user:pass@host:5432/db`.
        min_size : int
            The minimum number of connections kept open in the pool.
        max_size : int
            The maximum number of connections the pool may open.
        command_timeout : float | None
            Default timeout (seconds) for commands executed over pool connections.
        max_inactive_connection_lifetime : float
            Seconds an idle pool connection may live before being recycled.
        statement_cache_size : int
            Per-connection prepared statement cache size used by `asyncpg`.
        ssl : Any | None
            SSL context/mode passed through to `asyncpg.create_pool`.
        batch_size : int
            The size of each batched SQL execution. Iterated reads and writes will occur in batches
            of this amount. Must be `>= 1`.

        Raises
        ------
        ImportError
            If `asyncpg` is not installed.
        """

        if not INSTALLED:
            error: str = "PostgreSQLBackend requires `asyncpg` to be installed"
            raise ImportError(error)

        super().__init__(batch_size)

        self._dsn: str = dsn
        self._min_size: int = min_size
        self._max_size: int = max_size
        self._command_timeout: float | None = command_timeout
        self._max_inactive_lifetime: float = max_inactive_connection_lifetime
        self._statement_cache_size: int = statement_cache_size
        self._ssl: Any | None = ssl

        self._pool: asyncpg.Pool | None = None
        self._writer: asyncio.Task[None] | None = None

    async def __create_schema(self, connection: asyncpg.Connection) -> None:
        async with connection.transaction():
            await connection.execute(
                f"CREATE TABLE IF NOT EXISTS {_META_TABLE} "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL);",
            )

            for table in SCHEMA:
                await connection.execute(self._ddl_create(table))

            for table in SCHEMA:
                field_names: set[str] = {f.name for f in table.fields}

                if "_sync" in field_names:
                    await connection.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_{table.name}_sync "
                        f"ON {table.name}(_sync);",
                    )

                if table.name != "guilds" and "guild_id" in field_names:
                    await connection.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_{table.name}_guild "
                        f"ON {table.name}(guild_id);",
                    )

    async def __drain(self) -> None:
        remaining: list[SQLOP] = []
        while True:
            try:
                remaining.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if not remaining:
            return

        futures: list[asyncio.Future[None]] = [op.future for op in remaining if op.future]

        try:
            async with self._pool.acquire() as connection:
                await self.__run_batch(connection, remaining)
        except Exception as e:
            if not futures:
                logger.exception("PostgreSQL drain failed with no confirmation future to report to")

            for future in futures:
                if not future.done():
                    future.set_exception(e)
        else:
            for future in futures:
                if not future.done():
                    future.set_result(None)

    async def __init_connection(self, connection: asyncpg.Connection) -> None:
        for typename in ("json", "jsonb"):
            await connection.set_type_codec(
                typename,
                encoder=lambda v: v,
                decoder=lambda v: v,
                schema="pg_catalog",
                format="text",
            )

    async def __run_batch(self, connection: asyncpg.Connection, batch: list[SQLOP]) -> None:
        async with connection.transaction():
            i: int = 0
            while i < len(batch):
                op: SQLOP = batch[i]

                match op.mode:
                    case "execute":
                        await connection.execute(op.sql, *op.parameters)
                    case "executemany":
                        rows: list[tuple[Any, ...]] = list(op.parameters)

                        j: int = i + 1
                        while j < len(batch):
                            nxt: SQLOP = batch[j]

                            if nxt.mode != "executemany" or nxt.sql != op.sql:
                                break

                            rows.extend(nxt.parameters)
                            j += 1

                        await connection.executemany(op.sql, rows)
                        i = j - 1
                    case "multi":
                        for stmt, parameters in zip(op.sql, op.parameters, strict=True):
                            await connection.execute(stmt, *parameters)

                i += 1

    async def __version_get(self, connection: asyncpg.Connection) -> int:
        exists: bool = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = $1);",
            _META_TABLE,
        )

        if not exists:
            return 0

        value: str | None = await connection.fetchval(
            f"SELECT value FROM {_META_TABLE} WHERE key = 'schema_version';",
        )
        return int(value) if value is not None else 0

    async def __version_migrate(self, current: int, connection: asyncpg.Connection) -> None:
        if current > PostgreSQLBackend.VERSION:
            error: str = "Database schema newer than supported version"
            raise RuntimeError(error)

        if current == 0:
            logger.debug("Database version not found; creating schemas...")

            await self.__create_schema(connection)
            current = PostgreSQLBackend.VERSION
        #elif current < 2:
            # migrate to V2

        await connection.execute(
            f"INSERT INTO {_META_TABLE} (key, value) VALUES ('schema_version', $1) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;",
            str(current),
        )

    async def __writer(self) -> None: # noqa: PLR0912
        retries: int = 3

        try:
            while True:
                operation: SQLOP = await self._queue.get()
                batch: list[SQLOP] = [operation]

                while len(batch) < self._batch_size:
                    try:
                        batch.append(self._queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break

                futures: list[asyncio.Future[None]] = [op.future for op in batch if op.future]

                attempt: int = 0
                last_exc: Exception | None = None

                while attempt <= retries:
                    try:
                        async with self._pool.acquire() as connection:
                            await self.__run_batch(connection, batch)
                    except _TRANSIENT_ERRORS as e:
                        last_exc = e
                        attempt += 1

                        if attempt > retries:
                            break

                        backoff: float = min(0.5 * (2 ** (attempt - 1)), 5.0)
                        logger.warning(
                            "Transient PostgreSQL error, retrying batch (%d/%d) in %.1fs: %s",
                            attempt, retries, backoff, e,
                        )

                        await asyncio.sleep(backoff)
                        continue
                    except Exception as e:
                        last_exc = e
                        break
                    else:
                        last_exc = None
                        break

                if last_exc is not None:
                    if not futures:
                        logger.exception(
                            "PostgreSQL write failed with no confirmation future to report to",
                            exc_info=last_exc,
                        )

                    for future in futures:
                        if not future.done():
                            future.set_exception(last_exc)
                else:
                    for future in futures:
                        if not future.done():
                            future.set_result(None)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Writer crashed")
            raise

    @staticmethod
    def _build_query(query: BaseQuery) -> tuple[list[str], list[object]]:
        conditions: list[str] = []
        parameters: list[object] = []
        idx: int = 1

        for name, value in query.__dict__.items():
            if value is None:
                continue

            conditions.append(f"{name.removeprefix('_')} = ${idx}")
            idx += 1

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

    def _sql_delete(self, table_name: str, where: Sequence[str]) -> str:
        conditions: str = " AND ".join(f"{w} = ${i + 1}" for i, w in enumerate(where))
        return f"DELETE FROM {table_name} WHERE {conditions};"

    def _sql_insert(self, table_name: str, field_names: Sequence[str]) -> str:
        placeholder: str = ", ".join(f"${i + 1}" for i in range(len(field_names)))
        return f"INSERT INTO {table_name} ({', '.join(field_names)}) VALUES ({placeholder});"

    def _sql_update(self, table_name: str, field_names: Sequence[str], where: Sequence[str]) -> str:
        sets: str = ", ".join(f"{n} = ${i + 1}" for i, n in enumerate(field_names))
        offset: int = len(field_names)
        condition: str = " AND ".join(f"{w} = ${offset + i + 1}" for i, w in enumerate(where))
        return f"UPDATE {table_name} SET {sets} WHERE {condition};"

    def _sql_upsert(self, table: Table, field_names: Sequence[str]) -> str:
        placeholder: str = ", ".join(f"${i + 1}" for i in range(len(field_names)))
        columns: str = ", ".join(field_names)
        conflict_cols: str = ", ".join(table.primary_key)

        updates: str = ", ".join(
            f"{n} = EXCLUDED.{n}" for n in field_names if n not in table.primary_key
        )

        if not updates:
            return f"INSERT INTO {table.name} ({columns}) VALUES ({placeholder}) ON CONFLICT ({conflict_cols}) DO NOTHING;" # noqa: E501

        return f"INSERT INTO {table.name} ({columns}) VALUES ({placeholder}) ON CONFLICT ({conflict_cols}) DO UPDATE SET {updates};" # noqa: E501

    async def connect(self) -> None:
        logger.debug("Connecting to PostgreSQL pool (%s)", self._dsn)

        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
            command_timeout=self._command_timeout,
            max_inactive_connection_lifetime=self._max_inactive_lifetime,
            statement_cache_size=self._statement_cache_size,
            ssl=self._ssl,
            init=self.__init_connection,
        )

        async with self._pool.acquire() as connection:
            version: int = await self.__version_get(connection)

            if version != PostgreSQLBackend.VERSION:
                await self.__version_migrate(version, connection)

        def writer_done(task: asyncio.Task[None]) -> None:
            if task.cancelled():
                return

            exception: BaseException | None = task.exception()
            if exception is not None:
                logger.exception("Writer task crashed", exc_info=exception)

        self._writer = asyncio.create_task(self.__writer(), name="postgres-writer")
        self._writer.add_done_callback(writer_done)

        self._ready.set()

        logger.info(
            "Connected to PostgreSQL cache database (pool %d-%d)",
            self._min_size,
            self._max_size,
        )

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.cancel()

            with suppress(asyncio.CancelledError):
                await self._writer

            self._writer = None

        await self.__drain()

        await self._pool.close()
        self._pool = None

        logger.info("Disconnected from PostgreSQL cache database")

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
            rows: list[tuple[Any, ...]] = [mapper.to_row(c, sync=self._cache._sync) for c in group]
            sql: str = self._sql_upsert(mapper.table, mapper.names)

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

        m_sql: str = self._sql_upsert(mm.table, mm.names)
        future: MaybeFuture = await self._executemany(m_sql, member_rows, confirm)

        if future:
            futures.append(future)

        u_sql: str = self._sql_upsert(um.table, um.names)
        future = await self._executemany(u_sql, user_rows, confirm)

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

        sql: str = self._sql_upsert(mapper.table, mapper.names)
        return await self._executemany(sql, rows, confirm)

    async def channel_create(
        self,
        channel: hikari.GuildChannel,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        mapper: RowMapper = CHANNEL_WRITE_MAPPERS[channel.type]
        sql: str = self._sql_upsert(mapper.table, mapper.names)

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
        values: tuple[Any, ...] = (*mapper.to_row(channel, sync=self._cache._sync), channel.id)
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

        async with self._pool.acquire() as connection, connection.transaction():
            if channels:
                await connection.execute("DELETE FROM channels;")
            if guilds:
                await connection.execute("DELETE FROM guilds;")
            if members:
                await connection.execute("DELETE FROM members;")
                await connection.execute("DELETE FROM users;")
            if roles:
                await connection.execute("DELETE FROM roles;")

    async def guild_join(
        self,
        guild: hikari.GatewayGuild,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        mapper: RowMapper = GUILD_MAPPER
        sql: str = self._sql_upsert(mapper.table, mapper.names)

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

        set_fields: tuple[Any, ...] = tuple(f for f in GUILDS.fields if f.name != "id")
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
        params: list[Any] = []

        if query:
            conditions, params = self._build_query(query)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'
        type_idx: int = next(i for i, f in enumerate(CHANNELS.fields) if f.name == "type")

        async with self._pool.acquire() as connection, connection.transaction():
            async for row in connection.cursor(sql, *params, prefetch=self._batch_size):
                ctype: hikari.ChannelType = hikari.ChannelType(row[type_idx])
                kwargs: dict[str, Any] = decode_row(CHANNELS.fields, row)
                del kwargs["_sync"]
                yield _build_channel(self._cache, ctype, kwargs)

    async def iter_guilds(
        self,
        query: GuildQuery | None,
    ) -> AsyncIterator[PersistentGuild]:
        await self._ready.wait()

        sql: str = "SELECT * FROM guilds"
        params: list[Any] = []

        if query:
            conditions, params = self._build_query(query)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._pool.acquire() as connection, connection.transaction():
            async for row in connection.cursor(sql, *params, prefetch=self._batch_size):
                kwargs: dict[str, Any] = decode_row(GUILDS.fields, row)
                del kwargs["_sync"]
                yield PersistentGuild(self._cache, **kwargs)

    async def iter_members(
        self,
        query: MemberQuery | None,
    ) -> AsyncIterator[PersistentMember]:
        await self._ready.wait()

        sql: str = "SELECT * FROM members"
        params: list[Any] = []

        if query:
            conditions, params = self._build_query(query)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._pool.acquire() as connection, connection.transaction():
            cursor: asyncpg_cursor.Cursor = await connection.cursor(sql, *params)

            while True:
                members: list[asyncpg.Record] = await cursor.fetch(self._batch_size)

                if not members:
                    break

                user_ids: list[Any] = [m[0] for m in members]
                user_rows: list[asyncpg.Record] = await connection.fetch(
                    "SELECT * FROM users WHERE id = ANY($1::bigint[]);",
                    user_ids,
                )

                users_by_id: dict[hikari.Snowflake, dict[str, Any]] = {
                    row[0]: decode_row(USERS.fields, row) for row in user_rows
                }

                for row in members:
                    ukwargs: dict[str, Any] | None = users_by_id.get(row[0])

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
        params: list[Any] = []

        if query:
            conditions, params = self._build_query(query)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        sql += ';'

        async with self._pool.acquire() as connection, connection.transaction():
            async for row in connection.cursor(sql, *params, prefetch=self._batch_size):
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
        m_sql: str = self._sql_upsert(mm.table, mm.names)
        u_sql: str = self._sql_upsert(um.table, um.names)

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
            "DELETE FROM users WHERE id = $1 AND NOT EXISTS "
            "(SELECT 1 FROM members WHERE id = $1);"
        )

        return await self._executemulti(
            (
                (m_sql, (user_id, guild_id)),
                (u_sql, (user_id,)),
            ),
            confirm,
        )

    async def member_update(
        self,
        member: hikari.Member,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        m_fields: tuple[Any, ...] = tuple(
            f for f in MEMBERS.fields if f.name not in ("id", "guild_id")
        )
        m_mapper: RowMapper = RowMapper(MEMBERS, factory=None, fields=m_fields)
        m_sql: str = self._sql_update("members", m_mapper.names, ("id", "guild_id"))
        m_values: tuple[Any, ...] = (
            *m_mapper.to_row(member, sync=self._cache._sync), member.id, member.guild_id
        )

        u_fields: tuple[Any, ...] = tuple(
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

        async with self._pool.acquire() as connection, connection.transaction():
            for table in SCHEMA:
                if "_sync" not in {f.name for f in table.fields}:
                    continue

                await connection.execute(
                    f"DELETE FROM {table.name} WHERE _sync != $1;",
                    self._cache._sync,
                )

    async def restore(
        self,
        *_: tuple,
    ) -> None:
        error: str = "PostgreSQLBackend does not support restoring snapshot files"
        raise NotImplementedError(error)

    async def role_create(
        self,
        role: hikari.Role,
        confirm: bool,
    ) -> MaybeFuture:
        await self._ready.wait()

        mapper: RowMapper = ROLE_MAPPER
        sql: str = self._sql_upsert(mapper.table, mapper.names)

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

        set_fields: tuple[Any, ...] = tuple(f for f in ROLES.fields if f.name != "id")
        set_mapper: RowMapper = RowMapper(ROLES, factory=None, fields=set_fields)

        sql: str = self._sql_update("roles", set_mapper.names, ("id",))
        values: tuple[Any, ...] = (*set_mapper.to_row(role, sync=self._cache._sync), role.id)

        return await self._execute(sql, values, confirm)

    async def snapshot(
        self,
        *_: tuple,
    ) -> None:
        error: str = "PostgreSQLBackend does not support snapshotting"
        raise NotImplementedError(error)
