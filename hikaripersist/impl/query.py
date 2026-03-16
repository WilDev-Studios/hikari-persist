from __future__ import annotations

from dataclasses import dataclass
from hikaripersist.impl.iterator import CacheIterator
from typing import (
    Literal,
    overload,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from datetime import timedelta
    from hikaripersist.cache import Cache

    import hikari

__all__ = ()

@dataclass(slots=True)
class BaseQuery:
    """Base backend query blueprint."""

    _cache: Cache
    """Reference to the handling cache."""

class ChannelQuery(BaseQuery):
    """Channel backend query."""

    def __init__(self, cache: Cache) -> None:
        super().__init__(cache)

        self._id: hikari.Snowflake | None = None
        self._name: str | None = None
        self._type: hikari.ChannelType | None = None
        self._guild_id: hikari.Snowflake | None = None
        self._parent_id: hikari.Snowflake | None = None
        self._position: int | None = None
        self._is_nsfw: bool | None = None

    def all(self) -> CacheIterator[hikari.GuildChannel]:
        """
        Retrieve all results.

        Returns
        -------
        CacheIterator[hikari.GuildChannel]
            An asynchronous iterator providing lazy access to the results.
        """

        return CacheIterator(self._cache._backend.iter_channels(self))

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_TEXT],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildTextChannel]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_VOICE],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildVoiceChannel]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_CATEGORY],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildCategory]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_NEWS],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildNewsChannel]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_NEWS_THREAD],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildNewsThread]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_PUBLIC_THREAD],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildPublicThread]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_PRIVATE_THREAD],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildPrivateThread]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_STAGE],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildStageChannel]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_FORUM],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildForumChannel]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: Literal[hikari.ChannelType.GUILD_MEDIA],
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildMediaChannel]:...

    @overload
    def where(
        self,
        *,
        id: hikari.Snowflake | None = None,
        name: str | None = None,
        type: hikari.ChannelType | None = None,
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildChannel]:
        ...

    def where( # noqa: PLR0913
        self,
        *,
        id: hikari.Snowflake | None = None, # noqa: A002
        name: str | None = None,
        type: hikari.ChannelType | None = None, # noqa: A002
        guild_id: hikari.Snowflake | None = None,
        parent_id: hikari.Snowflake | None = None,
        position: int | None = None,
        is_nsfw: bool | None = None,
    ) -> CacheIterator[hikari.GuildChannel]:
        """
        Filter the results using various metadata options.

        Returns
        -------
        CacheIterator[hikari.GuildChannel]
            An asynchronous iterator providing lazy access to the results.
        """

        self._id = id
        self._name = name
        self._type = type
        self._guild_id = guild_id
        self._parent_id = parent_id
        self._position = position
        self._is_nsfw = is_nsfw

        return CacheIterator(self._cache._backend.iter_channels(self))

class GuildQuery(BaseQuery):
    """Guild backend query."""

    def __init__(self, cache: Cache) -> None:
        super().__init__(cache)

        self._id: hikari.Snowflake | None = None
        self._icon_hash: str | None = None
        self._name: str | None = None
        self._application_id: hikari.Snowflake | None = None
        self._afk_channel_id: hikari.Snowflake | None = None
        self._afk_timeout: timedelta | None = None
        self._banner_hash: str | None = None
        self._default_message_notifications: hikari.GuildMessageNotificationsLevel | None = None
        self._description: str | None = None
        self._discovery_splash_hash: str | None = None
        self._explicit_content_filter: hikari.GuildExplicitContentFilterLevel | None = None
        self._is_widget_enabled: bool | None = None
        self._max_video_channel_users: int | None = None
        self._mfa_level: hikari.GuildMFALevel | None = None
        self._owner_id: hikari.Snowflake | None = None
        self._preferred_locale: hikari.Locale | None = None
        self._premium_subscription_count: int | None = None
        self._premium_tier: hikari.GuildPremiumTier | None = None
        self._public_updates_channel_id: hikari.Snowflake | None = None
        self._rules_channel_id: hikari.Snowflake | None = None
        self._splash_hash: str | None = None
        self._system_channel_flags: hikari.GuildSystemChannelFlag | None = None
        self._system_channel_id: hikari.Snowflake | None = None
        self._vanity_url_code: str | None = None
        self._verification_level: hikari.GuildVerificationLevel | None = None
        self._widget_channel_id: hikari.Snowflake | None = None
        self._nsfw_level: hikari.GuildNSFWLevel | None = None

    def all(self) -> CacheIterator[hikari.Guild]:
        """
        Retrieve all results.

        Returns
        -------
        CacheIterator[hikari.Guild]
            An asynchronous iterator providing lazy access to the results.
        """

        return CacheIterator(self._cache._backend.iter_guilds(self))

    def where( # noqa: PLR0913
        self,
        *,
        id: hikari.Snowflake | None = None, # noqa: A002
        icon_hash: str | None = None,
        name: str | None = None,
        application_id: hikari.Snowflake | None = None,
        afk_channel_id: hikari.Snowflake | None = None,
        afk_timeout: timedelta | None = None,
        banner_hash: str | None = None,
        default_message_notifications: hikari.GuildMessageNotificationsLevel | None = None,
        description: str | None = None,
        discovery_splash_hash: str | None = None,
        explicit_content_filter: hikari.GuildExplicitContentFilterLevel | None = None,
        is_widget_enabled: bool | None = None,
        max_video_channel_users: int | None = None,
        mfa_level: hikari.GuildMFALevel | None = None,
        owner_id: hikari.Snowflake | None = None,
        preferred_locale: hikari.Locale | None = None,
        premium_subscription_count: int | None = None,
        premium_tier: hikari.GuildPremiumTier | None = None,
        public_updates_channel_id: hikari.Snowflake | None = None,
        rules_channel_id: hikari.Snowflake | None = None,
        splash_hash: str | None = None,
        system_channel_flags: hikari.GuildSystemChannelFlag | None = None,
        system_channel_id: hikari.Snowflake | None = None,
        vanity_url_code: str | None = None,
        verification_level: hikari.GuildVerificationLevel | None = None,
        widget_channel_id: hikari.Snowflake | None = None,
        nsfw_level: hikari.GuildNSFWLevel | None = None,
    ) -> CacheIterator[hikari.Guild]:
        """
        Filter the results using various metadata options.

        Returns
        -------
        CacheIterator[hikari.Guild]
            An asynchronous iterator providing lazy access to the results.
        """

        self._id = id
        self._icon_hash = icon_hash
        self._name = name
        self._application_id = application_id
        self._afk_channel_id = afk_channel_id
        self._afk_timeout = afk_timeout
        self._banner_hash = banner_hash
        self._default_message_notifications = default_message_notifications
        self._description = description
        self._discovery_splash_hash = discovery_splash_hash
        self._explicit_content_filter = explicit_content_filter
        self._is_widget_enabled = is_widget_enabled
        self._max_video_channel_users = max_video_channel_users
        self._mfa_level = mfa_level
        self._owner_id = owner_id
        self._preferred_locale = preferred_locale
        self._premium_subscription_count = premium_subscription_count
        self._premium_tier = premium_tier
        self._public_updates_channel_id = public_updates_channel_id
        self._rules_channel_id = rules_channel_id
        self._splash_hash = splash_hash
        self._system_channel_flags = system_channel_flags
        self._system_channel_id = system_channel_id
        self._vanity_url_code = vanity_url_code
        self._verification_level = verification_level
        self._widget_channel_id = widget_channel_id
        self._nsfw_level = nsfw_level

        return CacheIterator(self._cache._backend.iter_guilds(self))

class MemberQuery(BaseQuery):
    """Member backend query."""

    def __init__(self, cache: Cache) -> None:
        super().__init__(cache)

        self._guild_id: hikari.Snowflake | None = None
        self._id: hikari.Snowflake | None = None
        self._nickname: str | None = None
        self._guild_avatar_hash: str | None = None
        self._guild_banner_hash: str | None = None
        self._guild_flags: hikari.GuildMemberFlags | None = None

    def all(self) -> CacheIterator[hikari.Member]:
        """
        Retrieve all results.

        Returns
        -------
        CacheIterator[hikari.Member]
            An asynchronous iterator providing lazy access to the results.
        """

        return CacheIterator(self._cache._backend.iter_members(self))

    def where( # noqa: PLR0913
        self,
        guild_id: hikari.Snowflake | None = None,
        member_id: hikari.Snowflake | None = None,
        nickname: str | None = None,
        guild_avatar_hash: str | None = None,
        guild_banner_hash: str | None = None,
        guild_flags: hikari.GuildMemberFlags | None = None,
    ) -> CacheIterator[hikari.Member]:
        """
        Filter the results using various metadata options.

        Returns
        -------
        CacheIterator[hikari.Member]
            An asynchronous iterator providing lazy access to the results.
        """

        self._guild_id = guild_id
        self._id = member_id
        self._nickname = nickname
        self._guild_avatar_hash = guild_avatar_hash
        self._guild_banner_hash = guild_banner_hash
        self._guild_flags = guild_flags

        return CacheIterator(self._cache._backend.iter_members(self))

class RoleQuery(BaseQuery):
    """Message backend query."""

    def __init__(self, cache: Cache) -> None:
        super().__init__(cache)

        self._id: hikari.Snowflake | None = None
        self._name: str | None = None
        self._color: hikari.Color | None = None
        self._guild_id: hikari.Snowflake | None = None
        self._is_hoisted: bool | None = None
        self._icon_hash: str | None = None
        self._unicode_emoji: hikari.UnicodeEmoji | None = None
        self._is_managed: bool | None = None
        self._is_mentionable: bool | None = None
        self._permissions: hikari.Permissions | None = None
        self._position: int | None = None
        self._bot_id: hikari.Snowflake | None = None
        self._integration_id: hikari.Snowflake | None = None
        self._is_premium_subscriber_role: bool | None = None
        self._is_available_for_purchase: bool | None = None
        self._is_guild_linked_role: bool | None = None

    def all(self) -> CacheIterator[hikari.Role]:
        """
        Retrieve all results.

        Returns
        -------
        CacheIterator[hikari.Role]
            An asynchronous iterator providing lazy access to the results.
        """

        return CacheIterator(self._cache._backend.iter_roles(self))

    def where( # noqa: PLR0913
        self,
        *,
        id: hikari.Snowflake | None = None, # noqa: A002
        name: str | None = None,
        color: hikari.Color | None = None,
        guild_id: hikari.Snowflake | None = None,
        is_hoisted: bool | None = None,
        icon_hash: str | None = None,
        unicode_emoji: hikari.UnicodeEmoji | None = None,
        is_managed: bool | None = None,
        is_mentionable: bool | None = None,
        permissions: hikari.Permissions | None = None,
        position: int | None = None,
        bot_id: hikari.Snowflake | None = None,
        integration_id: hikari.Snowflake | None = None,
        is_premium_subscriber_role: bool | None = None,
        is_available_for_purchase: bool | None = None,
        is_guild_linked_role: bool | None = None,
    ) -> CacheIterator[hikari.Role]:
        """
        Filter the results using various metadata options.

        Returns
        -------
        CacheIterator[hikari.Role]
            An asynchronous iterator providing lazy access to the results.
        """

        self._id = id
        self._name = name
        self._color = color
        self._guild_id = guild_id
        self._is_hoisted = is_hoisted
        self._icon_hash = icon_hash
        self._unicode_emoji = unicode_emoji
        self._is_managed = is_managed
        self._is_mentionable = is_mentionable
        self._permissions = permissions
        self._position = position
        self._bot_id = bot_id
        self._integration_id = integration_id
        self._is_premium_subscriber_role = is_premium_subscriber_role
        self._is_available_for_purchase = is_available_for_purchase
        self._is_guild_linked_role = is_guild_linked_role

        return CacheIterator(self._cache._backend.iter_roles(self))
