from __future__ import annotations

from collections.abc import (
    Awaitable,
    Callable,
)
from hikaripersist.backend import Backend
from hikaripersist.impl.query import (
    ChannelQuery,
    GuildQuery,
    MemberQuery,
    RoleQuery,
)
from hikaripersist.rule import Rule
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
        if not self._rule._channel.can_cache(
            event.channel_id,
            event.guild_id,
        ):
            logger.debug(
                "Ignoring CHANNEL_CREATE - ruleset violation: ChannelID=%s",
                event.channel_id,
            )
            return None

        logger.debug(
            "Cached CHANNEL_CREATE: ChannelID=%s",
            event.channel_id,
        )
        return await self._backend.channel_create(event.channel, confirm)

    async def __channel_delete(
        self,
        event: hikari.GuildChannelDeleteEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        logger.debug(
            "Cached CHANNEL_DELETE: ChannelID=%s",
            event.channel_id,
        )
        return await self._backend.channel_delete(event.channel_id, confirm)

    async def __channel_update(
        self,
        event: hikari.GuildChannelUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._channel.can_cache(
            event.channel_id,
            event.guild_id,
        ):
            logger.debug(
                "Ignoring CHANNEL_UPDATE - ruleset violation: ChannelID=%s",
                event.channel_id,
            )
            return None

        logger.debug(
            "Cached CHANNEL_UPDATE: ChannelID=%s",
            event.channel_id,
        )
        return await self._backend.channel_update(event.channel, confirm)

    async def __guild_available( # noqa: PLR0912
        self,
        event: hikari.GuildAvailableEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        futures: list[asyncio.Future[None]] = []

        channels: set[hikari.PermissibleGuildChannel] = set()
        for channel in event.channels.values():
            if self._rule._channel.can_cache(
                channel.id, channel.guild_id
            ):
                channels.add(channel)
            else:
                logger.debug(
                    "Ignoring GUILD_AVAILABLE:Channel - ruleset violation: ChannelID=%s",
                    channel.id,
                )

        if channels:
            logger.debug(
                "Cached GUILD_AVAILABLE:Channel: GuildID=%s, Channels=%s",
                event.guild_id,
                len(channels),
            )
            future: asyncio.Future[None] | None = await self._backend.startup_guild_channels(
                channels,
                confirm,
            )
            if future:
                futures.append(future)

        if self._rule._guild.can_cache(
            event.guild_id,
        ):
            logger.debug(
                "Cached GUILD_AVAILABLE:Guild: GuildID=%s",
                event.guild_id,
            )
            future: asyncio.Future[None] | None = await self._backend.startup_guild(
                event.guild,
                confirm,
            )
            if future:
                futures.append(future)
        else:
            logger.debug(
                "Ignoring GUILD_AVAILABLE:Guild - ruleset violation: GuildID=%s",
                event.guild_id,
            )

        members: set[hikari.Member] = set()
        for member in event.members.values():
            if self._rule._member.can_cache(
                member.guild_id, member.id,
            ):
                members.add(member)
            else:
                logger.debug(
                    "Ignoring GUILD_AVAILABLE:Member - ruleset violation: MemberID=%s",
                    member.id,
                )

        if members:
            logger.debug(
                "Cached GUILD_AVAILABLE:Member: GuildID=%s, Members=%s",
                event.guild_id,
                len(members),
            )
            future: asyncio.Future[None] | None = await self._backend.startup_guild_members(
                members,
                confirm,
            )
            if future:
                futures.append(future)

        roles: set[hikari.Role] = set()
        for role in event.roles.values():
            if self._rule._role.can_cache(
                role.guild_id, role.id,
            ):
                roles.add(role)
            else:
                logger.debug(
                    "Ignoring GUILD_AVAILABLE:Role - ruleset violation: RoleID=%s",
                    role.id,
                )

        if roles:
            logger.debug(
                "Cached GUILD_AVAILABLE:Role: GuildID=%s, Roles=%s",
                event.guild_id,
                len(roles),
            )
            future: asyncio.Future[None] | None = await self._backend.startup_guild_roles(
                roles,
                confirm,
            )
            if future:
                futures.append(future)

        if futures:
            return await asyncio.gather(*futures, return_exceptions=True)

        return None

    async def __guild_join(
        self,
        event: hikari.GuildJoinEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._guild.can_cache(
            event.guild_id,
        ):
            logger.debug(
                "Ignoring GUILD_JOIN - ruleset violation: GuildID=%s",
                event.guild_id,
            )
            return None

        logger.debug(
            "Cached GUILD_JOIN: GuildID=%s",
            event.guild_id,
        )
        return await self._backend.guild_join(event.guild, confirm)

    async def __guild_leave(
        self,
        event: hikari.GuildLeaveEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        logger.debug(
            "Cached GUILD_LEAVE: GuildID=%s",
            event.guild_id,
        )
        return await self._backend.guild_leave(event.guild_id, confirm)

    async def __guild_update(
        self,
        event: hikari.GuildUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._guild.can_cache(
            event.guild_id,
        ):
            logger.debug(
                "Ignoring GUILD_UPDATE - ruleset violation: GuildID=%s",
                event.guild_id,
            )
            return None

        logger.debug(
            "Cached GUILD_UPDATE: GuildID=%s",
            event.guild_id,
        )
        return await self._backend.guild_update(event.guild, confirm)

    async def __member_chunk(
        self,
        event: hikari.MemberChunkEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        futures: list[asyncio.Future[None]] = []

        for member in event.members.values():
            if not self._rule._member.can_cache(
                event.guild_id,
                member.id,
            ):
                logger.debug(
                    "Ignoring MEMBER_CHUNK:Member - ruleset violation: "
                    "UserID=%s, GuildID=%s",
                    member.id, event.guild_id,
                )
                continue

            future: asyncio.Future[None] | None = await self._backend.member_create(member, confirm)

            if confirm:
                futures.append(future)

        logger.debug("Cached MEMBER_CHUNK: GuildID=%s", event.guild_id)
        return asyncio.gather(*futures, return_exceptions=True)

    async def __member_create(
        self,
        event: hikari.MemberCreateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._member.can_cache(
            event.guild_id,
            event.user_id,
        ):
            logger.debug(
                "Ignoring MEMBER_CREATE - ruleset violation: "
                "UserID=%s, GuildID=%s",
                event.user_id,
                event.guild_id,
            )
            return None

        logger.debug(
            "Cached MEMBER_CREATE: UserID=%s, GuildID=%s",
            event.user_id,
            event.guild_id,
        )
        return await self._backend.member_create(event.member, confirm)

    async def __member_delete(
        self,
        event: hikari.MemberDeleteEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        logger.debug(
            "Cached MEMBER_DELETE: UserID=%s, GuildID=%s",
            event.user_id,
            event.guild_id,
        )
        return await self._backend.member_delete(event.user_id, event.guild_id, confirm)

    async def __member_update(
        self,
        event: hikari.MemberUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._member.can_cache(
            event.guild_id,
            event.user_id,
        ):
            logger.debug(
                "Ignoring MEMBER_UPDATE - ruleset violation:"
                "UserID=%s, GuildID=%s",
                event.user_id,
                event.guild_id,
            )
            return None

        logger.debug(
            "Cached MEMBER_UPDATE: UserID=%s, GuildID=%s",
            event.user_id,
            event.guild_id,
        )
        return await self._backend.member_update(event.member, confirm)

    async def __role_create(
        self,
        event: hikari.RoleCreateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._role.can_cache(
            event.guild_id,
            event.role_id,
        ):
            logger.debug(
                "Ignoring ROLE_CREATE - ruleset violation: "
                "RoleID=%s, GuildID=%s",
                event.role_id,
                event.guild_id,
            )
            return None

        logger.debug(
            "Cached ROLE_CREATE: RoleID=%s, GuildID=%s",
            event.role_id,
            event.guild_id,
        )
        return await self._backend.role_create(event.role, confirm)

    async def __role_delete(
        self,
        event: hikari.RoleDeleteEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        logger.debug(
            "Cached ROLE_DELETE: RoleID=%s, GuildID=%s",
            event.role_id,
            event.guild_id,
        )
        return await self._backend.role_delete(event.role_id, confirm)

    async def __role_update(
        self,
        event: hikari.RoleUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._role.can_cache(
            event.guild_id,
            event.role_id,
        ):
            logger.debug(
                "Ignoring ROLE_UPDATE - ruleset violation: "
                "RoleID=%s, GuildID=%s",
                event.role_id,
                event.guild_id,
            )
            return None

        logger.debug(
            "Cached ROLE_UPDATE: RoleID=%s, GuildID=%s",
            event.role_id,
            event.guild_id,
        )
        return await self._backend.role_update(event.role, confirm)

    async def __thread_create(
        self,
        event: hikari.GuildThreadCreateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._channel.can_cache(
            event.thread_id,
            event.guild_id,
        ):
            logger.debug(
                "Ignoring THREAD_CREATE - ruleset violation: ThreadID=%s",
                event.thread_id,
            )
            return None

        logger.debug(
            "Cached THREAD_CREATE: ThreadID=%s",
            event.thread_id,
        )
        return await self._backend.channel_create(event.thread, confirm)

    async def __thread_delete(
        self,
        event: hikari.GuildThreadDeleteEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        logger.debug(
            "Cached THREAD_DELETE: ThreadID=%s",
            event.thread_id,
        )
        return await self._backend.channel_delete(event.thread_id, confirm)

    async def __thread_update(
        self,
        event: hikari.GuildThreadUpdateEvent,
        confirm: bool,
    ) -> asyncio.Future[None] | None:
        if not self._rule._channel.can_cache(
            event.thread_id,
            event.guild_id,
        ):
            logger.debug(
                "Ignoring THREAD_UPDATE - ruleset violation: ThreadID=%s",
                event.thread_id,
            )
            return None

        logger.debug(
            "Cached THREAD_UPDATE: ThreadID=%s",
            event.thread_id,
        )
        return await self._backend.channel_update(event.thread, confirm)

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
