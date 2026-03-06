from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import (
    datetime,
    timezone,
)
from hikaripersist.impl.iterator import CacheIterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hikaripersist.cache import Cache
    from hikaripersist.cached.channel import CachedChannel
    from hikaripersist.cached.guild import CachedGuild
    from hikaripersist.cached.member import CachedMember
    from hikaripersist.cached.message import CachedMessage
    from hikaripersist.cached.role import CachedRole

    import hikari

__all__ = ()

class BaseQuery(ABC):
    """Base backend query blueprint."""

    @abstractmethod
    def __init__(self, cache: Cache) -> None:
        """
        Create a new backend query blueprint.

        Parameters
        ----------
        cache : Cache
            Reference to the cache.
        """

        self._cache: Cache = cache

        self._limit: int | None = None

class ChannelQuery(BaseQuery):
    """Channel backend query blueprint."""

    def __init__(self, cache: Cache) -> None:
        super().__init__(cache)

        self._category: hikari.Snowflake | None = None
        self._channel_id: hikari.Snowflake | None = None
        self._created_after: datetime | None = None
        self._created_before: datetime | None = None
        self._guild_id: hikari.Snowflake | None = None
        self._name: str | None = None
        self._nsfw: bool | None = None
        self._position: int | None = None
        self._topic: str | None = None
        self._type: hikari.ChannelType | None = None

    def where( # noqa: PLR0913
        self,
        *,
        category: hikari.Snowflake | None = None,
        channel_id: hikari.Snowflake | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        guild_id: hikari.Snowflake | None = None,
        name: str | None = None,
        nsfw: bool | None = None,
        position: int | None = None,
        topic: str | None = None,
        type_: hikari.ChannelType | None = None,
        limit: int | None = None,
    ) -> CacheIterator[CachedChannel]:
        """
        Filter the results using various metadata options.

        Parameters
        ----------
        category : hikari.Snowflake | None
            If provided, filter using the channel's category ID.
        channel_id : hikari.Snowflake | None
            If provided, filter using the channel's ID.
        created_after : datetime | None
            If provided, filter if created after this timestamp.
            If timezone-aware, will be converted to UTC.
        created_before : datetime | None
            If provided, filter if created before this timestamp.
            If timezone-aware, will be converted to UTC.
        guild_id : hikari.Snowflake | None
            If provided, filter using the guild's ID.
        name : str | None
            If provided, filter using the channel's name.
        nsfw : bool | None
            If provided, filter using the NSFW level.
        position : int | None
            If provided, filter using the channel's position.
        topic : str | None
            If provided, filter using the phrase.
        type_ : hikari.ChannelType | None
            If provided, filter using the channel's type.
        limit : int | None
            If provided, a limit on how many results are retrieved.

        Returns
        -------
        CacheIterator[CachedChannel]
            An asynchronous iterator providing lazy access to the results.
        """

        self._category = category
        self._channel_id = channel_id

        if created_after:
            self._created_after = created_after.astimezone(timezone.utc)

        if created_before:
            self._created_before = created_before.astimezone(timezone.utc)

        self._guild_id = guild_id
        self._name = name
        self._nsfw = nsfw
        self._position = position
        self._topic = topic
        self._type = type_

        self._limit = limit

        return CacheIterator(self._cache._backend.iter_channels(self))

class GuildQuery(BaseQuery):
    """Guild backend query blueprint."""

    def __init__(self, cache: Cache) -> None:
        super().__init__(cache)

        self._description: str | None = None
        self._created_after: datetime | None = None
        self._created_before: datetime | None = None
        self._guild_id: hikari.Snowflake | None = None
        self._mfa: hikari.GuildMFALevel | None = None
        self._name: str | None = None
        self._nsfw: hikari.GuildNSFWLevel | None = None
        self._owner_id: hikari.Snowflake | None = None
        self._premium: hikari.GuildPremiumTier | None = None
        self._vanity: str | None = None
        self._verification: hikari.GuildVerificationLevel | None = None

    def where( # noqa: PLR0913
        self,
        *,
        description: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        guild_id: hikari.Snowflake | None = None,
        mfa: hikari.GuildMFALevel | None = None,
        name: str | None = None,
        nsfw: hikari.GuildNSFWLevel | None = None,
        owner_id: hikari.Snowflake | None = None,
        premium_tier: hikari.GuildPremiumTier | None = None,
        vanity_code: str | None = None,
        verification: hikari.GuildVerificationLevel | None = None,
        limit: int | None = None,
    ) -> CacheIterator[CachedGuild]:
        """
        Filter the results using various metadata options.

        Parameters
        ----------
        description : str | None
            If provided, filter using the description.
        created_after : datetime | None
            If provided, filter if created after this timestamp.
            If timezone-aware, will be converted to UTC.
        created_before : datetime | None
            If provided, filter if created before this timestamp.
            If timezone-aware, will be converted to UTC.
        guild_id : hikari.Snowflake | None
            If provided, filter using the guild's ID.
        mfa : hikari.GuildMFALevel | None
            If provided, filter using MFA levels.
        name : str | None
            If provided, filter using the guild's name.
        nsfw : hikari.GuildNSFWLevel | None
            If provided, filter using the NSFW level.
        owner_id : hikari.Snowflake | None
            If provided, filter using the guild owner's ID.
        premium_tier : hikari.GuildPremiumTier | None
            If provided, filter using the premium tier.
        vanity_code : str | None
            If provided, filter using a vanity URL code.
        verification : hikari.GuildVerificationLevel | None
            If provided, filter using the verification level.
        limit : int | None
            If provided, a limit on how many results are retrieved.

        Returns
        -------
        CacheIterator[CachedGuild]
            An asynchronous iterator providing lazy access to the results.
        """

        self._description = description

        if created_after:
            self._created_after = created_after.astimezone(timezone.utc)

        if created_before:
            self._created_before = created_before.astimezone(timezone.utc)

        self._guild_id = guild_id
        self._mfa = mfa
        self._name = name
        self._nsfw = nsfw
        self._owner_id = owner_id
        self._premium = premium_tier
        self._vanity = vanity_code
        self._verification = verification

        self._limit = limit

        return CacheIterator(self._cache._backend.iter_guilds(self))

class MemberQuery(BaseQuery):
    """"Member backend query blueprint."""

    def __init__(self, cache: Cache) -> None:
        super().__init__(cache)

        self._boosting_after: datetime | None = None
        self._boosting_before: datetime | None = None
        self._bot: bool | None = None
        self._created_after: datetime | None = None
        self._created_before: datetime | None = None
        self._discriminator: str | None = None
        self._flags: hikari.UserFlag | None = None
        self._guild_id: hikari.Snowflake | None = None
        self._joined_after: datetime | None = None
        self._joined_before: datetime | None = None
        self._member_id: hikari.Snowflake | None = None
        self._name: str | None = None
        self._system: bool | None = None
        self._timed_out: bool | None = None
        self._username: str | None = None

    def where( # noqa: PLR0913
        self,
        *,
        boosting_after: datetime | None = None,
        boosting_before: datetime | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        discriminator: str | None = None,
        flags: hikari.UserFlag | None = None,
        guild_id: hikari.Snowflake | None = None,
        is_bot: bool | None = None,
        is_system: bool | None = None,
        is_timed_out: bool | None = None,
        joined_after: datetime | None = None,
        joined_before: datetime | None = None,
        member_id: hikari.Snowflake | None = None,
        name: str | None = None,
        username: str | None = None,
        limit: int | None = None,
    ) -> CacheIterator[CachedMember]:
        """
        Filter the results using various metadata options.

        Parameters
        ----------
        boosting_after : datetime | None
            If provided, filter if boosting since after this timestamp.
            If timezone-aware, will be converted to UTC.
        boosting_before : datetime | None
            If provided, filter if boosting since before this timestamp.
            If timezone-aware, will be converted to UTC.
        created_after : datetime | None
            If provided, filter if created after this timestamp.
            If timezone-aware, will be converted to UTC.
        created_before : datetime | None
            If provided, filter if created before this timestamp.
            If timezone-aware, will be converted to UTC.
        discriminator : str | None
            If provided, filter using a discriminator.
        flags : hikari.UserFlag | None
            If provided, filter using user flags.
        guild_id : hikari.Snowflake | None
            If provided, filter using the member's guild ID.
        is_bot : bool | None
            If provided, filter if the member is a bot.
        is_system : bool | None
            If provided, filter if the member is a system account.
        is_timed_out : bool | None
            If provided, filter if the member is timed out.
        joined_after : datetime | None
            If provided, filter if joined after this timestamp.
            If timezone-aware, will be converted to UTC.
        joined_before : datetime | None
            If provided, filter if joined before this timestamp.
            If timezone-aware, will be converted to UTC.
        member_id : hikari.Snowflake | None
            If provided, filter using a member ID.
        name : str | None
            If provided, filter using a display name.
        username : str | None
            If provided, filter members by username.
        limit : int | None
            If provided, a limit on how many results are retrieved.

        Returns
        -------
        CacheIterator[CachedMember]
            An asynchronous iterator providing lazy access to the results.
        """

        if boosting_after:
            self._boosting_after = boosting_after.astimezone(timezone.utc)

        if boosting_before:
            self._boosting_before = boosting_before.astimezone(timezone.utc)

        if created_after:
            self._created_after = created_after.astimezone(timezone.utc)

        if created_before:
            self._created_before = created_before.astimezone(timezone.utc)

        self._discriminator = discriminator
        self._flags = flags
        self._guild_id = guild_id
        self._bot = is_bot
        self._system = is_system
        self._timed_out = is_timed_out

        if joined_after:
            self._joined_after = joined_after.astimezone(timezone.utc)

        if joined_before:
            self._joined_before = joined_before.astimezone(timezone.utc)

        self._member_id = member_id
        self._name = name
        self._username = username

        self._limit = limit

        return CacheIterator(self._cache._backend.iter_members(self))

class MessageQuery(BaseQuery):
    """Message backend query blueprint."""

    def __init__(self, cache: Cache) -> None:
        super().__init__(cache)

        self._author_id: hikari.Snowflake | None = None
        self._channel_id: hikari.Snowflake | None = None
        self._contains: str | None = None
        self._created_after: datetime | None = None
        self._created_before: datetime | None = None
        self._edited_after: datetime | None = None
        self._edited_before: datetime | None = None
        self._guild_id: hikari.Snowflake | None = None
        self._message_id: hikari.Snowflake | None = None
        self._pinned: bool | None = None

    def where( # noqa: PLR0913
        self,
        *,
        author_id: hikari.Snowflake | None = None,
        channel_id: hikari.Snowflake | None = None,
        contains: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        edited_after: datetime | None = None,
        edited_before: datetime | None = None,
        guild_id: hikari.Snowflake | None = None,
        is_pinned: bool | None = None,
        message_id: hikari.Snowflake | None = None,
        limit: int | None = None,
    ) -> CacheIterator[CachedMessage]:
        """
        Filter the results using various metadata options.

        Parameters
        ----------
        author_id : hikari.Snowflake | None
            If provided, filter using the author's ID.
        channel_id : hikari.Snowflake | None
            If provided, filter using the channel's ID.
        contains : str | None
            If provided, filter using a phrase.
        created_after : datetime | None
            If provided, filter if created after this timestamp.
            If timezone-aware, will be converted to UTC.
        created_before : datetime | None
            If provided, filter if created before this timestamp.
            If timezone-aware, will be converted to UTC.
        edited_after : datetime | None
            If provided, filter if edited after this timestamp.
            If timezone-aware, will be converted to UTC.
        edited_before : datetime | None
            If provided, filter if edited before this timestamp.
            If timezone-aware, will be converted to UTC.
        guild_id : hikari.Snowflake | None
            If provided, filter using the guild's ID.
        is_pinned : bool | None
            If provided, filter through pinned messages.
        message_id : hikari.Snowflake | None
            If provided, filter using the message's ID.
        limit : int | None
            If provided, a limit on how many results are retrieved.

        Returns
        -------
        CacheIterator[CachedMessage]
            An asynchronous iterator providing lazy access to the results.
        """

        self._author_id = author_id
        self._channel_id = channel_id
        self._contains = contains

        if created_after:
            self._created_after = created_after.astimezone(timezone.utc)

        if created_before:
            self._created_before = created_before.astimezone(timezone.utc)

        if edited_after:
            self._edited_after = edited_after.astimezone(timezone.utc)

        if edited_before:
            self._edited_before = edited_before.astimezone(timezone.utc)

        self._guild_id = guild_id
        self._pinned = is_pinned
        self._message_id = message_id

        self._limit = limit

        return CacheIterator(self._cache._backend.iter_messages(self))

class RoleQuery(BaseQuery):
    """Message backend query blueprint."""

    def __init__(self, cache: Cache) -> None:
        super().__init__(cache)

        self._color: hikari.Color | None = None
        self._created_after: datetime | None = None
        self._created_before: datetime | None = None
        self._guild_id: hikari.Snowflake | None = None
        self._hoisted: bool | None = None
        self._managed: bool | None = None
        self._name: str | None = None
        self._permissions: hikari.Permissions | None = None
        self._position: int | None = None
        self._premium: bool | None = None
        self._role_id: hikari.Snowflake | None = None

    def where( # noqa: PLR0913
        self,
        *,
        color: hikari.Color | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        guild_id: hikari.Snowflake | None = None,
        is_hoisted: bool | None = None,
        is_managed: bool | None = None,
        is_premium: bool | None = None,
        name: str | None = None,
        permissions: hikari.Permissions | None = None,
        position: int | None = None,
        role_id: hikari.Snowflake | None = None,
        limit: int | None = None,
    ) -> CacheIterator[CachedRole]:
        """
        Filter the results using various metadata options.

        Parameters
        ----------
        color : hikari.Color | None
            If provided, filter by the color of the role.
        created_after : datetime | None
            If provided, filter if created after this timestamp.
            If timezone-aware, will be converted to UTC.
        created_before : datetime | None
            If provided, filter if created before this timestamp.
            If timezone-aware, will be converted to UTC.
        guild_id : hikari.Snowflake | None
            If provided, filter using the role's guild ID.
        is_hoisted : bool | None
            If provided, filter by the hoised state.
        is_managed : bool | None
            If provided, filter by managed/bot roles.
        is_premium : bool | None
            If provided, filter by boosting reward roles.
        name : str | None
            If provided, filter by the name of the role.
        permissions : hikari.Permissions | None
            If provided, filter by the permissions assigned to the role.
        position : int | None
            If provided, filter by the position of the role.
        role_id : hikari.Snowflake | None
            If provided, filter by the ID of the role.
        limit : int | None
            If provided, a limit on how many results are retrieved.

        Returns
        -------
        CacheIterator[CachedRole]
            An asynchronous iterator providing lazy access to the results.
        """

        self._color = color

        if created_after:
            self._created_after = created_after.astimezone(timezone.utc)

        if created_before:
            self._created_before = created_before.astimezone(timezone.utc)

        self._guild_id = guild_id
        self._hoisted = is_hoisted
        self._managed = is_managed
        self._premium = is_premium
        self._name = name
        self._permissions = permissions
        self._position = position
        self._role_id = role_id

        self._limit = limit

        return CacheIterator(self._cache._backend.iter_roles(self))
