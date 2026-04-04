from __future__ import annotations

from collections.abc import (
    Awaitable,
    Callable,
)
from hikaripersist.backend import Backend
from hikaripersist.impl.event import (
    BulkChannelEvent,
    BulkMemberEvent,
    BulkRoleEvent,
    ChannelInsertEvent,
    ChannelRemoveEvent,
    ChannelUpdateEvent,
    GuildInsertEvent,
    GuildRemoveEvent,
    GuildUpdateEvent,
    MemberInsertEvent,
    MemberRemoveEvent,
    MemberUpdateEvent,
    RoleInsertEvent,
    RoleRemoveEvent,
    RoleUpdateEvent,
)
from hikaripersist.impl.query import (
    ChannelQuery,
    GuildQuery,
    MemberQuery,
    RoleQuery,
)
from hikaripersist.rule import Rule
from pathlib import Path
from typing import (
    ClassVar,
    TypeVar,
)

import asyncio
import hikari
import inspect
import logging
import sys
import traceback

__all__ = ("Cache",)

EventT = TypeVar("EventT", bound=hikari.Event)

logger: logging.Logger = logging.getLogger("persist.cache")

class Cache:
    """Persistent cache for `hikari`-based Discord bots."""

    __instance: ClassVar[Cache | None] = None

    def __init__(
        self,
        bot: hikari.GatewayBot,
        backend: Backend,
        *,
        rule: Rule | None = None,
    ) -> None:
        """
        Create a new persistent cache.

        Parameters
        ----------
        bot : hikari.GatewayBot
            The bot to interface this cache with.
        backend : Backend
            The database backend to use with this cache.
        rule : Rule | None
            If provided, a ruleset regarding what is cached.

        Raises
        ------
        RuntimeError
            If an instance of `Cache` already exists.
        TypeError
            - If `bot` is not `hikari.GatewayBot`.
            - If `backend` is not `Backend`.
            - If `rule` is provided and is not `Rule`.
        """

        if Cache.__instance:
            error: str = "Only one Cache instance can exist at any time"
            raise RuntimeError(error)

        if not isinstance(bot, hikari.GatewayBot):
            error: str = "Provided bot must be hikari.GatewayBot"
            raise TypeError(error)

        if not isinstance(backend, Backend):
            error: str = "Provided backend must be Backend"
            raise TypeError(error)

        if rule is not None and not isinstance(rule, Rule):
            error: str = "Provided rule must be Rule"
            raise TypeError(error)

        Cache.__instance = self

        self._bot: hikari.GatewayBot = bot

        self._backend: Backend = backend
        self._backend._cache = self
        self._rule: Rule = rule or Rule()

        self._listeners: dict[
            type[hikari.Event], list[tuple[Callable[[hikari.Event], Awaitable[None]], bool]]
        ] = {}
        self._handlers: dict[
            type[hikari.Event], Callable[[hikari.Event, bool], Awaitable[None]]
        ] = {
            hikari.GuildChannelCreateEvent: self.__channel_create,
            hikari.GuildChannelDeleteEvent: self.__channel_delete,
            hikari.GuildChannelUpdateEvent: self.__channel_update,
            hikari.GuildAvailableEvent: self.__guild_available,
            hikari.GuildJoinEvent:   self.__guild_join,
            hikari.GuildLeaveEvent:  self.__guild_leave,
            hikari.GuildUpdateEvent: self.__guild_update,
            hikari.MemberChunkEvent: self.__member_chunk,
            hikari.MemberCreateEvent: self.__member_create,
            hikari.MemberDeleteEvent: self.__member_delete,
            hikari.MemberUpdateEvent: self.__member_update,
            hikari.RoleCreateEvent: self.__role_create,
            hikari.RoleDeleteEvent: self.__role_delete,
            hikari.RoleUpdateEvent: self.__role_update,
            hikari.StartingEvent: self.__bot_starting,
            hikari.StoppingEvent: self.__bot_stopping,
            hikari.GuildThreadCreateEvent: self.__thread_create,
            hikari.GuildThreadDeleteEvent: self.__thread_delete,
            hikari.GuildThreadUpdateEvent: self.__thread_update,
        }

        for event in self._handlers:
            self._bot.subscribe(event, self.__event)

    async def __bot_starting(self, _: hikari.StartingEvent, __: bool) -> None:
        await self._backend.connect()

    async def __bot_stopping(self, _: hikari.StoppingEvent, __: bool) -> None:
        await self._backend.disconnect()

    async def __event(self, event: hikari.Event) -> None:
        event_type: type[hikari.Event] = type(event)

        listeners: list[
            tuple[Callable[[EventT], Awaitable[None]], bool]
        ] = self._listeners.get(event_type, [])
        needs_confirm: bool = any(confirm for _, confirm in listeners)

        future: asyncio.Future[None] | None = None

        if event_type in self._handlers:
            future = await self._handlers[event_type](event, needs_confirm)

        if not listeners:
            return

        async def _invoke(
            func: Callable[[EventT, bool], Awaitable[None]],
            confirms: bool,
        ) -> None:
            if confirms and future is not None:
                await future

            try:
                await func(event)
            except Exception as e:
                logger.error(
                    "An exception occurred handling an event (%s)",
                    type(event).__name__,
                )
                traceback.print_exception(type(e), e, e.__traceback__.tb_next, file=sys.stderr)

        def complete(task: asyncio.Task[None]) -> None:
            if task.cancelled():
                return

            exception: BaseException | None = task.exception()
            if exception is None:
                return

            logger.error("Listener task %s failed unexpectedly", task.get_name())

        for func, confirm in listeners:
            fired: asyncio.Task[None] = asyncio.create_task(
                _invoke(func, confirm),
                name=f"event.{type(event).__name__}.{func.__name__}",
            )
            fired.add_done_callback(complete)

    async def __channel_create(
        self,
        event: hikari.GuildChannelCreateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._channel.can_cache(event.channel):
            self._bot.dispatch(ChannelInsertEvent(
                channel=event.channel,
                successful=False,
            ))
            logger.debug(
                "Ignoring CHANNEL_CREATE - ruleset violation: ChannelID=%s",
                event.channel_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.channel_create(
            event.channel,
            confirm,
        )
        self._bot.dispatch(ChannelInsertEvent(
            channel=event.channel,
            successful=True,
        ))
        logger.debug(
            "Cached CHANNEL_CREATE: ChannelID=%s",
            event.channel_id,
        )

        return future

    async def __channel_delete(
        self,
        event: hikari.GuildChannelDeleteEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self._backend.channel_delete(
            event.channel_id,
            confirm,
        )
        self._bot.dispatch(ChannelRemoveEvent(
            channel_id=event.channel_id,
            guild_id=event.guild_id,
        ))
        logger.debug(
            "Cached CHANNEL_DELETE: ChannelID=%s",
            event.channel_id,
        )

        return future

    async def __channel_update(
        self,
        event: hikari.GuildChannelUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._channel.can_cache(event.channel):
            self._bot.dispatch(ChannelUpdateEvent(
                channel=event.channel,
                successful=False,
            ))
            logger.debug(
                "Ignoring CHANNEL_UPDATE - ruleset violation: ChannelID=%s",
                event.channel_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.channel_update(
            event.channel,
            confirm,
        )
        self._bot.dispatch(ChannelUpdateEvent(
            channel=event.channel,
            successful=True,
        ))
        logger.debug(
            "Cached CHANNEL_UPDATE: ChannelID=%s",
            event.channel_id,
        )

        return future

    async def __guild_available( # noqa: PLR0912, PLR0915
        self,
        event: hikari.GuildAvailableEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        futures: list[asyncio.Future[None]] = []

        cfailed: set[hikari.PermissibleGuildChannel] = set()
        cpassed: list[hikari.PermissibleGuildChannel] = []

        for channel in event.channels.values():
            if self._rule._channel.can_cache(channel):
                cpassed.append(channel)
                continue

            cfailed.add(channel)

        if cpassed:
            future: asyncio.Future[None] | None = await self._backend.bulk_channels(
                cpassed,
                confirm,
            )
            if future:
                futures.append(future)

        if cfailed or cpassed:
            self._bot.dispatch(BulkChannelEvent(
                failed=cfailed,
                guild=event.guild,
                passed=cpassed,
            ))

        if cfailed:
            logger.debug(
                "Ignoring GUILD_AVAILABLE:Channels - ruleset violations: GuildID=%s, Channels=%s",
                event.guild_id,
                len(cfailed),
            )

        if cpassed:
            logger.debug(
                "Cached GUILD_AVAILABLE:Channels: GuildID=%s, Channels=%s",
                event.guild_id,
                len(cpassed),
            )

        if self._rule._guild.can_cache(event.guild):
            future: asyncio.Future[None] | None = await self._backend.guild_join(
                event.guild,
                confirm,
            )
            self._bot.dispatch(GuildUpdateEvent(
                guild=event.guild,
                successful=True,
            ))
            logger.debug(
                "Cached GUILD_AVAILABLE:Guild: GuildID=%s",
                event.guild_id,
            )

            if future:
                futures.append(future)
        else:
            self._bot.dispatch(GuildUpdateEvent(
                guild=event.guild,
                successful=False,
            ))
            logger.debug(
                "Ignoring GUILD_AVAILABLE:Guild - ruleset violation: GuildID=%s",
                event.guild_id,
            )

        mfailed: set[hikari.Member] = set()
        mpassed: set[hikari.Member] = set()

        for member in event.members.values():
            if self._rule._member.can_cache(member):
                mpassed.add(member)
                continue

            mfailed.add(member)

        if mpassed:
            future: asyncio.Future[None] | None = await self._backend.bulk_members(
                mpassed,
                confirm,
            )
            if future:
                futures.append(future)

        if mfailed or mpassed:
            self._bot.dispatch(BulkMemberEvent(
                failed=mfailed,
                guild_id=event.guild_id,
                passed=mpassed,
            ))

        if mfailed:
            logger.debug(
                "Ignoring GUILD_AVAILABLE:Members - ruleset violations: GuildID=%s, Members=%s",
                event.guild_id,
                len(mfailed),
            )

        if mpassed:
            logger.debug(
                "Cached GUILD_AVAILABLE:Members: GuildID=%s, Members=%s",
                event.guild_id,
                len(mpassed),
            )

        rfailed: set[hikari.Role] = set()
        rpassed: set[hikari.Role] = set()

        for role in event.roles.values():
            if self._rule._role.can_cache(role):
                rpassed.add(role)
                continue

            rfailed.add(role)

        if rpassed:
            future: asyncio.Future[None] | None = await self._backend.bulk_roles(
                rpassed,
                confirm,
            )
            if future:
                futures.append(future)

        if rfailed or rpassed:
            self._bot.dispatch(BulkRoleEvent(
                failed=rfailed,
                guild=event.guild,
                passed=rpassed,
            ))

        if rfailed:
            logger.debug(
                "Ignoring GUILD_AVAILABLE:Roles - ruleset violations: GuildID=%s, Roles=%s",
                event.guild_id,
                len(rfailed),
            )

        if rpassed:
            logger.debug(
                "Cached GUILD_AVAILABLE:Roles: GuildID=%s, Roles=%s",
                event.guild_id,
                len(rpassed),
            )

        if futures:
            return await asyncio.gather(*futures, return_exceptions=True)

        return None

    async def __guild_join(
        self,
        event: hikari.GuildJoinEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._guild.can_cache(event.guild):
            self._bot.dispatch(GuildInsertEvent(
                guild=event.guild,
                successful=False,
            ))
            logger.debug(
                "Ignoring GUILD_JOIN - ruleset violation: GuildID=%s",
                event.guild_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.guild_join(event.guild, confirm)
        self._bot.dispatch(GuildInsertEvent(
            guild=event.guild,
            successful=True,
        ))
        logger.debug(
            "Cached GUILD_JOIN: GuildID=%s",
            event.guild_id,
        )

        return future

    async def __guild_leave(
        self,
        event: hikari.GuildLeaveEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self._backend.guild_leave(
            event.guild_id,
            confirm,
        )
        self._bot.dispatch(GuildRemoveEvent(
            guild_id=event.guild_id,
        ))
        logger.debug(
            "Cached GUILD_LEAVE: GuildID=%s",
            event.guild_id,
        )

        return future

    async def __guild_update(
        self,
        event: hikari.GuildUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._guild.can_cache(event.guild):
            self._bot.dispatch(GuildUpdateEvent(
                guild=event.guild,
                successful=False,
            ))
            logger.debug(
                "Ignoring GUILD_UPDATE - ruleset violation: GuildID=%s",
                event.guild_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.guild_update(event.guild, confirm)
        self._bot.dispatch(GuildUpdateEvent(
            guild=event.guild,
            successful=True,
        ))
        logger.debug(
            "Cached GUILD_UPDATE: GuildID=%s",
            event.guild_id,
        )

        return future

    async def __member_chunk(
        self,
        event: hikari.MemberChunkEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        futures: list[asyncio.Future[None]] = []

        failed: set[hikari.Member] = set()
        passed: set[hikari.Member] = set()

        for member in event.members.values():
            if self._rule._member.can_cache(member):
                passed.add(member)
                continue

            failed.add(member)

        if passed: # TODO: Bulk update cache, not iterated updates
            for member in passed:
                future: asyncio.Future[None] | None = await self._backend.member_create(
                    member,
                    confirm,
                )

                if confirm:
                    futures.append(future)

        if failed or passed:
            self._bot.dispatch(BulkMemberEvent(
                failed=failed,
                guild_id=event.guild_id,
                passed=passed,
            ))

        if failed:
            logger.debug(
                "Ignoring MEMBER_CHUNK:Members - ruleset violations: GuildID=%s, Members=%s",
                event.guild_id,
                len(failed),
            )

        if passed:
            logger.debug(
                "Cached MEMBER_CHUNK:Members: GuildID=%s, Members=%s",
                event.guild_id,
                len(passed),
            )

        logger.debug("Cached MEMBER_CHUNK: GuildID=%s", event.guild_id)
        return asyncio.gather(*futures, return_exceptions=True)

    async def __member_create(
        self,
        event: hikari.MemberCreateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._member.can_cache(event.member):
            self._bot.dispatch(MemberInsertEvent(
                member=event.member,
                successful=False,
            ))
            logger.debug(
                "Ignoring MEMBER_CREATE - ruleset violation: "
                "UserID=%s, GuildID=%s",
                event.user_id,
                event.guild_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.member_create(
            event.member,
            confirm,
        )
        self._bot.dispatch(MemberInsertEvent(
            member=event.member,
            successful=True,
        ))
        logger.debug(
            "Cached MEMBER_CREATE: UserID=%s, GuildID=%s",
            event.user_id,
            event.guild_id,
        )

        return future

    async def __member_delete(
        self,
        event: hikari.MemberDeleteEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self._backend.member_delete(
            event.user_id,
            event.guild_id,
            confirm,
        )
        self._bot.dispatch(MemberRemoveEvent(
            guild_id=event.guild_id,
            user=event.user,
        ))
        logger.debug(
            "Cached MEMBER_DELETE: UserID=%s, GuildID=%s",
            event.user_id,
            event.guild_id,
        )

        return future

    async def __member_update(
        self,
        event: hikari.MemberUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._member.can_cache(event.member):
            self._bot.dispatch(MemberUpdateEvent(
                member=event.member,
                successful=False,
            ))
            logger.debug(
                "Ignoring MEMBER_UPDATE - ruleset violation:"
                "UserID=%s, GuildID=%s",
                event.user_id,
                event.guild_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.member_update(
            event.member,
            confirm,
        )
        self._bot.dispatch(MemberUpdateEvent(
            member=event.member,
            successful=True,
        ))
        logger.debug(
            "Cached MEMBER_UPDATE: UserID=%s, GuildID=%s",
            event.user_id,
            event.guild_id,
        )

        return future

    async def __role_create(
        self,
        event: hikari.RoleCreateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._role.can_cache(event.role):
            self._bot.dispatch(RoleInsertEvent(
                role=event.role,
                successful=False,
            ))
            logger.debug(
                "Ignoring ROLE_CREATE - ruleset violation: "
                "RoleID=%s, GuildID=%s",
                event.role_id,
                event.guild_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.role_create(event.role, confirm)
        self._bot.dispatch(RoleInsertEvent(
            role=event.role,
            successful=True,
        ))
        logger.debug(
            "Cached ROLE_CREATE: RoleID=%s, GuildID=%s",
            event.role_id,
            event.guild_id,
        )

        return future

    async def __role_delete(
        self,
        event: hikari.RoleDeleteEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self._backend.role_delete(
            event.role_id,
            confirm,
        )
        self._bot.dispatch(RoleRemoveEvent(
            guild_id=event.guild_id,
            role_id=event.role_id,
        ))
        logger.debug(
            "Cached ROLE_DELETE: RoleID=%s, GuildID=%s",
            event.role_id,
            event.guild_id,
        )

        return future

    async def __role_update(
        self,
        event: hikari.RoleUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._role.can_cache(event.role):
            self._bot.dispatch(RoleUpdateEvent(
                role=event.role,
                successful=False,
            ))
            logger.debug(
                "Ignoring ROLE_UPDATE - ruleset violation: "
                "RoleID=%s, GuildID=%s",
                event.role_id,
                event.guild_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.role_update(event.role, confirm)
        self._bot.dispatch(RoleUpdateEvent(
            role=event.role,
            successful=True,
        ))
        logger.debug(
            "Cached ROLE_UPDATE: RoleID=%s, GuildID=%s",
            event.role_id,
            event.guild_id,
        )

        return future

    async def __thread_create(
        self,
        event: hikari.GuildThreadCreateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._channel.can_cache(event.thread):
            self._bot.dispatch(ChannelInsertEvent(
                channel=event.thread,
                successful=False,
            ))
            logger.debug(
                "Ignoring THREAD_CREATE - ruleset violation: ThreadID=%s",
                event.thread_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.channel_create(
            event.thread,
            confirm,
        )
        self._bot.dispatch(ChannelInsertEvent(
            channel=event.thread,
            successful=True,
        ))
        logger.debug(
            "Cached THREAD_CREATE: ThreadID=%s",
            event.thread_id,
        )

        return future

    async def __thread_delete(
        self,
        event: hikari.GuildThreadDeleteEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        future: asyncio.Future[None] | None = await self._backend.channel_delete(
            event.thread_id,
            confirm,
        )
        self._bot.dispatch(ChannelRemoveEvent(
            channel_id=event.thread_id,
            guild_id=event.guild_id,
        ))
        logger.debug(
            "Cached THREAD_DELETE: ThreadID=%s",
            event.thread_id,
        )

        return future

    async def __thread_update(
        self,
        event: hikari.GuildThreadUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._channel.can_cache(event.thread):
            self._bot.dispatch(ChannelUpdateEvent(
                channel=event.thread,
                successful=False,
            ))
            logger.debug(
                "Ignoring THREAD_UPDATE - ruleset violation: ThreadID=%s",
                event.thread_id,
            )
            return None

        future: asyncio.Future[None] | None = await self._backend.channel_update(
            event.thread,
            confirm,
        )
        self._bot.dispatch(ChannelUpdateEvent(
            channel=event.thread,
            successful=True,
        ))
        logger.debug(
            "Cached THREAD_UPDATE: ThreadID=%s",
            event.thread_id,
        )

        return future

    async def backup(
        self,
        path: Path | str,
    ) -> None:
        """
        Snapshot the current cache backend to a file.

        Parameters
        ----------
        path : Path | str
            The path to the file to write.

        Raises
        ------
        TypeError
            If `path` is not `Path` or `str`.
        """

        if not isinstance(path, (Path, str)):
            error: str = "Provided path must be Path or str"
            raise TypeError(error)

        await self._backend.snapshot(Path(path))

    @property
    def bot(self) -> hikari.GatewayBot:
        """The bot interfaced with this cache."""
        return self._bot

    @property
    def channels(self) -> ChannelQuery:
        """
        Interact with cache channels.
        """

        return ChannelQuery(self)

    async def clear(
        self,
        *,
        channels: bool = False,
        guilds: bool = False,
        members: bool = False,
        roles: bool = False,
    ) -> None:
        """
        Clear the cache of specific data.

        Parameters
        ----------
        channels : bool
            If cache channel data should be cleared.
        guilds : bool
            If cache guild data should be cleared.
        members : bool
            If cache member data should be cleared.
        roles : bool
            If cache role data should be cleared.

        Raises
        ------
        TypeError
            If any parameter is not `bool`.
        """

        if not isinstance(channels, bool):
            error: str = "Provided channels must be bool"
            raise TypeError(error)

        if not isinstance(guilds, bool):
            error: str = "Provided guilds must be bool"
            raise TypeError(error)

        if not isinstance(members, bool):
            error: str = "Provided members must be bool"
            raise TypeError(error)

        if not isinstance(roles, bool):
            error: str = "Provided roles must be bool"
            raise TypeError(error)

        logger.debug(
            "Attempting to clear cache: Channels=%s, Guilds=%s, Members=%s, Roles=%s",
            channels, guilds, members, roles,
        )

        await self._backend.clear(channels, guilds, members, roles)

        logger.info(
            "Cache cleared: Channels=%s, Guilds=%s, Members=%s, Roles=%s",
            channels, guilds, members, roles,
        )

    @property
    def guilds(self) -> GuildQuery:
        """
        Interact with cache guilds.
        """

        return GuildQuery(self)

    def listen(
        self,
        event: type[EventT] | None = None,
        *,
        confirm: bool = False,
    ) -> Callable[[Callable[[EventT], Awaitable[None]]], Callable[[EventT], Awaitable[None]]]:
        """
        Listen for an event and add this method as a callback.

        Parameters
        ----------
        event : type[EventT] | None
            The event object to listen for, if provided, otherwise
            extracted from callback's first parameter type.
        confirm : bool
            If `True`, not dispatched until the cache has confirmed the change.
            If `False`, dispatched as soon as the cache receives the event.

        Note
        ----
        To ensure that the cache sees all event data before being handled, the cache acts as a
        middle-man in event dispatching. Instead of using `@bot.listen()`, use `@cache.listen()`
        and the cache will dispatch each event normally after it's complete.
        """

        def wrapper(
            func: Callable[[EventT], Awaitable[None]]
        ) -> Callable[[EventT], Awaitable[None]]:
            nonlocal event

            if event is None:
                signature: inspect.Signature = inspect.signature(func)
                parameters: list[inspect.Parameter] = list(signature.parameters.values())

                if not parameters:
                    error: str = f"Cannot infer event type for {func.__name__}; no parameters found"
                    raise TypeError(error)

                first_parameter: inspect.Parameter = parameters[0]
                if first_parameter.name in ("self", "cls") and len(parameters) > 1:
                    first_parameter = parameters[1]

                annotation: type = first_parameter.annotation
                if annotation is inspect.Parameter.empty:
                    error: str = (
                        f"Cannot infer event type for {func.__name__};"
                        "first parameter has no type annotation"
                    )
                    raise TypeError(error)

                if not isinstance(annotation, type) or not issubclass(annotation, hikari.Event):
                    error: str = (
                        f"First parameter of {func.__name__}"
                        "must be a subclass of hikari.Event"
                    )
                    raise TypeError(error)

                event = annotation

            if event not in self._handlers and event not in self._listeners:
                self._bot.subscribe(event, self.__event)

            self._listeners.setdefault(event, []).append((func, confirm))

            return func

        return wrapper

    @property
    def members(self) -> MemberQuery:
        """
        Interact with cache members.
        """

        return MemberQuery(self)

    async def restore(
        self,
        path: Path | str,
    ) -> None:
        """
        Restore a cache backend from a file.

        Parameters
        ----------
        path : Path | str
            The path to the file to read.

        Raises
        ------
        TypeError
            If `path` is not `Path` or `str`.
        """

        if not isinstance(path, (Path, str)):
            error: str = "Provided path must be Path or str"
            raise TypeError(error)

        await self._backend.restore(Path(path))

    @property
    def roles(self) -> RoleQuery:
        """
        Interact with cache roles.
        """

        return RoleQuery(self)

    def subscribe(
        self,
        event: type[EventT],
        callback: Callable[[EventT], Awaitable[None]],
        *,
        confirm: bool = False,
    ) -> None:
        """
        Subscribe to an event with a handler callback.

        Parameters
        ----------
        event : type[EventT]
            The event object to subscribe to.
        callback : Callable[[EventT], Awaitable[None]]
            The handler callback method.
        confirm : bool
            If `True`, not dispatched until the cache has confirmed the change.
            If `False`, dispatched as soon as the cache receives the event.
        """

        if event not in self._handlers and event not in self._listeners:
            self._bot.subscribe(event, self.__event)

        self._listeners.setdefault(event, []).append((callback, confirm))

    def unsubscribe(
        self,
        event: type[EventT],
        callback: Callable[[EventT], Awaitable[None]],
    ) -> None:
        """
        Unsubscribe a handler callback from an event.

        Parameters
        ----------
        event : type[EventT]
            The event object to unsubscribe from.
        callback : Callable[[EventT], Awaitable[None]]
            The handler callback method to unsubscribe.
        """

        if event not in self._listeners:
            return

        for listener in list(self._listeners[event]):
            if listener[0] != callback:
                continue

            self._listeners[event].remove(listener)
            break
