from __future__ import annotations

from collections.abc import (
    Awaitable,
    Callable,
)
from hikaripersist.backend import Backend
from hikaripersist.cached.channel import CachedChannel
from hikaripersist.cached.guild import CachedGuild
from hikaripersist.cached.member import CachedMember
from hikaripersist.cached.message import CachedMessage
from hikaripersist.cached.role import CachedRole
from hikaripersist.rule import Rule
from typing import ClassVar

import asyncio
import hikari
import inspect
import logging

__all__ = ("Cache",)

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
        self._rule: Rule = rule or Rule()

        self._listeners: dict[
            type[hikari.Event], list[Callable[[hikari.Event], Awaitable[None]]]
        ] = {}
        self._handlers: dict[
            type[hikari.Event], Callable[[hikari.Event], Awaitable[None]]
        ] = {
            hikari.GuildChannelCreateEvent: self.__channel_create,
            hikari.GuildChannelDeleteEvent: self.__channel_delete,
            hikari.GuildChannelUpdateEvent: self.__channel_update,
            hikari.GuildJoinEvent:   self.__guild_join,
            hikari.GuildLeaveEvent:  self.__guild_leave,
            hikari.GuildUpdateEvent: self.__guild_update,
            hikari.MemberCreateEvent: self.__member_create,
            hikari.MemberDeleteEvent: self.__member_delete,
            hikari.MemberUpdateEvent: self.__member_update,
            hikari.GuildMessageCreateEvent: self.__message_create,
            hikari.GuildMessageDeleteEvent: self.__message_delete,
            hikari.GuildMessageUpdateEvent: self.__message_update,
            hikari.RoleCreateEvent: self.__role_create,
            hikari.RoleDeleteEvent: self.__role_delete,
            hikari.RoleUpdateEvent: self.__role_update,
            hikari.StartingEvent: self.__bot_starting,
            hikari.StoppingEvent: self.__bot_stopping,
        }

        for event in self._handlers:
            self._bot.subscribe(event, self.__event)

    async def __bot_starting(self, _: hikari.StartingEvent) -> None:
        await self._backend.connect()

    async def __bot_stopping(self, _: hikari.StoppingEvent) -> None:
        await self._backend.disconnect()

    async def __event(self, event: hikari.Event) -> None:
        event_type: type[hikari.Event] = type(event)

        if event_type in self._handlers:
            await self._handlers[event_type](event)

        if event_type in self._listeners:
            await asyncio.gather(
                *(listener(event) for listener in self._listeners[event_type]),
                return_exceptions=True,
            )

    async def __channel_create(self, event: hikari.GuildChannelCreateEvent) -> None:
        if not self._rule._channel.can_cache(
            event.channel_id,
            event.guild_id,
        ):
            logger.debug(
                f"Ignoring CHANNEL_CREATE - ruleset violation: ChannelID={event.channel_id}"
            )
            return

        await self._backend.channel_create(event.channel)
        logger.debug(f"Cached CHANNEL_CREATE: ChannelID={event.channel_id}")

    async def __channel_delete(self, event: hikari.GuildChannelDeleteEvent) -> None:
        await self._backend.channel_delete(event.channel_id)
        logger.debug(f"Cached CHANNEL_DELETE: ChannelID={event.channel_id}")

    async def __channel_update(self, event: hikari.GuildChannelUpdateEvent) -> None:
        if not self._rule._channel.can_cache(
            event.channel_id,
            event.guild_id,
        ):
            logger.debug(
                f"Ignoring CHANNEL_UPDATE - ruleset violation: ChannelID={event.channel_id}"
            )
            return

        await self._backend.channel_update(event.channel)
        logger.debug(f"Cached CHANNEL_UPDATE: ChannelID={event.channel_id}")

    async def __guild_join(self, event: hikari.GuildJoinEvent) -> None:
        if not self._rule._guild.can_cache(
            event.guild_id,
        ):
            logger.debug(
                f"Ignoring GUILD_JOIN - ruleset violation: GuildID={event.guild_id}"
            )
            return

        await self._backend.guild_join(event.guild)
        logger.debug(f"Cached GUILD_JOIN: GuildID={event.guild_id}")

    async def __guild_leave(self, event: hikari.GuildLeaveEvent) -> None:
        await self._backend.guild_leave(event.guild_id)
        logger.debug(f"Cached GUILD_LEAVE: GuildID={event.guild_id}")

    async def __guild_update(self, event: hikari.GuildUpdateEvent) -> None:
        if not self._rule._guild.can_cache(
            event.guild_id,
        ):
            logger.debug(
                f"Ignoring GUILD_UPDATE - ruleset violation: GuildID={event.guild_id}"
            )
            return

        await self._backend.guild_update(event.guild)
        logger.debug(f"Cached GUILD_UPDATE: GuildID={event.guild_id}")

    async def __member_create(self, event: hikari.MemberCreateEvent) -> None:
        if not self._rule._member.can_cache(
            event.guild_id,
            event.user_id,
        ):
            logger.debug(
                "Ignoring MEMBER_CREATE - ruleset violation:"
                f"UserID={event.user_id}, GuildID={event.guild_id}"
            )
            return

        await self._backend.member_create(event.member)
        logger.debug(f"Cached MEMBER_CREATE: UserID={event.user_id}, GuildID={event.guild_id}")

    async def __member_delete(self, event: hikari.MemberDeleteEvent) -> None:
        await self._backend.member_delete(event.user_id, event.guild_id)
        logger.debug(f"Cached MEMBER_DELETE: UserID={event.user_id}, GuildID={event.guild_id}")

    async def __member_update(self, event: hikari.MemberUpdateEvent) -> None:
        if not self._rule._member.can_cache(
            event.guild_id,
            event.user_id,
        ):
            logger.debug(
                "Ignoring MEMBER_UPDATE - ruleset violation:"
                f"UserID={event.user_id}, GuildID={event.guild_id}"
            )
            return

        await self._backend.member_update(event.member)
        logger.debug(f"Cached MEMBER_UPDATE: UserID={event.user_id}, GuildID={event.guild_id}")

    async def __message_create(self, event: hikari.GuildMessageCreateEvent) -> None:
        if not self._rule._message.can_cache(
            event.channel_id,
            event.message.guild_id,
            event.message_id,
            event.author_id,
        ):
            logger.debug(
                "Ignoring MESSAGE_CREATE - ruleset violation:"
                f"MessageID={event.message_id}, ChannelID={event.channel_id}"
            )
            return

        await self._backend.message_create(event.message)
        logger.debug(
            f"Cached MESSAGE_CREATE: MessageID={event.message_id}, ChannelID={event.channel_id}"
        )

    async def __message_delete(self, event: hikari.GuildMessageDeleteEvent) -> None:
        await self._backend.message_delete(event.message_id, event.channel_id)
        logger.debug(
            f"Cached MESSAGE_DELETE: MessageID={event.message_id}, ChannelID={event.channel_id}"
        )

    async def __message_update(self, event: hikari.GuildMessageUpdateEvent) -> None:
        if not self._rule._message.can_cache(
            event.channel_id,
            event.message.guild_id,
            event.message_id,
            event.author_id,
        ):
            logger.debug(
                "Ignoring MESSAGE_UPDATE - ruleset violation:"
                f"MessageID={event.message_id}, ChannelID={event.channel_id}"
            )
            return

        await self._backend.message_update(event.message)
        logger.debug(
            f"Cached MESSAGE_UPDATE: MessageID={event.message_id}, ChannelID={event.channel_id}"
        )

    async def __role_create(self, event: hikari.RoleCreateEvent) -> None:
        if not self._rule._role.can_cache(
            event.guild_id,
            event.role_id,
        ):
            logger.debug(
                "Ignoring ROLE_CREATE - ruleset violation:"
                f"RoleID={event.role_id}, GuildID={event.guild_id}"
            )
            return

        await self._backend.role_create(event.role)
        logger.debug(f"Cached ROLE_CREATE: RoleID={event.role_id}, GuildID={event.guild_id}")

    async def __role_delete(self, event: hikari.RoleDeleteEvent) -> None:
        await self._backend.role_delete(event.role_id)
        logger.debug(f"Cached ROLE_DELETE: RoleID={event.role_id}, GuildID={event.guild_id}")

    async def __role_update(self, event: hikari.RoleUpdateEvent) -> None:
        if not self._rule._role.can_cache(
            event.guild_id,
            event.role_id,
        ):
            logger.debug(
                "Ignoring ROLE_UPDATE - ruleset violation:"
                f"RoleID={event.role_id}, GuildID={event.guild_id}"
            )
            return

        await self._backend.role_update(event.role)
        logger.debug(f"Cached ROLE_UPDATE: RoleID={event.role_id}, GuildID={event.guild_id}")

    @property
    def bot(self) -> hikari.GatewayBot:
        """The bot interfaced with this cache."""
        return self._bot

    async def get_channel(
        self,
        channel_id: hikari.Snowflakeish,
    ) -> CachedChannel | None:
        """
        Retrieve a cached channel.

        Parameters
        ----------
        channel_id : hikari.Snowflakeish
            The ID of the channel to retrieve.

        Returns
        -------
        CachedChannel | None
            If found, the cached channel.

        Raises
        ------
        TypeError
            If `channel_id` is not `hikari.Snowflakeish`.
        """

        if not isinstance(channel_id, hikari.Snowflakeish):
            error: str = "Provided channel_id must be hikari.Snowflakeish"
            raise TypeError(error)

        return await self._backend.get_channel(channel_id)

    async def get_guild(
        self,
        guild_id: hikari.Snowflakeish,
    ) -> CachedGuild | None:
        """
        Retrieve a cached guild.

        Parameters
        ----------
        guild_id : hikari.Snowflakeish
            The ID of the guild to retrieve.

        Returns
        -------
        CachedGuild | None
            If found, the cached guild.

        Raises
        ------
        TypeError
            If `guild_id` is not `hikari.Snowflakeish`.
        """

        if not isinstance(guild_id, hikari.Snowflakeish):
            error: str = "Provided guild_id must be hikari.Snowflakeish"
            raise TypeError(error)

        return await self._backend.get_guild(guild_id)

    async def get_member(
        self,
        user_id: hikari.Snowflakeish,
        guild_id: hikari.Snowflakeish,
    ) -> CachedMember | None:
        """
        Retrieve a cached member.

        Parameters
        ----------
        user_id : hikari.Snowflakeish
            The ID of the member to retrieve.
        guild_id : hikari.Snowflakeish
            The ID of the member's bounded guild.

        Returns
        -------
        CachedMember | None
            If found, the cached member.

        Raises
        ------
        TypeError
            - If `user_id` is not `hikari.Snowflakeish`.
            - If `guild_id` is not `hikari.Snowflakeish`.
        """

        if not isinstance(user_id, hikari.Snowflakeish):
            error: str = "Provided user_id must be hikari.Snowflakeish"
            raise TypeError(error)

        if not isinstance(guild_id, hikari.Snowflakeish):
            error: str = "Provided guild_id must be hikari.Snowflakeish"
            raise TypeError(error)

        return await self._backend.get_member(user_id, guild_id)

    async def get_message(
        self,
        message_id: hikari.Snowflakeish,
        channel_id: hikari.Snowflakeish,
    ) -> CachedMessage | None:
        """
        Retrieve a cached message.

        Parameters
        ----------
        message_id : hikari.Snowflakeish
            The ID of the message to retrieve.
        channel_id : hikari.Snowflakeish
            The ID of the channel the message is in.

        Returns
        -------
        CachedMessage | None
            If found, the cached message.

        Raises
        ------
        TypeError
            - If `message_id` is not `hikari.Snowflakeish`.
            - If `channel_id` is not `hikari.Snowflakeish`.
        """

        if not isinstance(message_id, hikari.Snowflakeish):
            error: str = "Provided message_id must be hikari.Snowflakeish"
            raise TypeError(error)

        if not isinstance(channel_id, hikari.Snowflakeish):
            error: str = "Provided channel_id must be hikari.Snowflakeish"
            raise TypeError(error)

        return await self._backend.get_message(message_id, channel_id)

    async def get_role(
        self,
        role_id: hikari.Snowflakeish,
    ) -> CachedRole | None:
        """
        Retrieve a cached role.

        Parameters
        ----------
        role_id : hikari.Snowflakeish
            The ID of the role to retrieve.

        Returns
        -------
        CachedRole | None
            If found, the cached role.

        Raises
        ------
        TypeError
            If `role_id` is not `hikari.Snowflakeish`.
        """

        if not isinstance(role_id, hikari.Snowflakeish):
            error: str = "Provided role_id must be hikari.Snowflakeish"
            raise TypeError(error)

        return await self._backend.get_role(role_id)

    def listen(
        self,
        event: type[hikari.Event] | None = None,
    ) -> Callable[[Callable[[hikari.Event], Awaitable[None]]], None]:
        """
        Listen for an event and add this method as a callback.

        Parameters
        ----------
        event : type[hikari.Event] | None
            The event object to listen for, if provided, otherwise
            extracted from callback's first parameter type.
        """

        def wrapper(func: Callable[[hikari.Event], Awaitable[None]]) -> None:
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

            if event in self._listeners:
                self._listeners[event].append(func)
            else:
                self._listeners[event] = [func]

        return wrapper

    def subscribe(
        self,
        event: type[hikari.Event],
        callback: Callable[[hikari.Event], Awaitable[None]],
    ) -> None:
        """
        Subscribe to an event with a handler callback.

        Parameters
        ----------
        event : type[hikari.Event]
            The event object to subscribe to.
        callback : Callable[[hikari.Event], Awaitable[None]]
            The handler callback method.
        """

        if event in self._listeners:
            self._listeners[event].append(callback)
        else:
            self._listeners[event] = [callback]

    def unsubscribe(
        self,
        event: type[hikari.Event],
        callback: Callable[[hikari.Event], Awaitable[None]],
    ) -> None:
        """
        Unsubscribe a handler callback from an event.

        Parameters
        ----------
        event : type[hikari.Event]
            The event object to unsubscribe from.
        callback : Callable[[hikari.Event], Awaitable[None]]
            The handler callback method to unsubscribe.
        """

        if event not in self._listeners:
            return

        try:
            self._listeners[event].remove(callback)
        except ValueError:
            return
