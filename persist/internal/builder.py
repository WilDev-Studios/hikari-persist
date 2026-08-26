from __future__ import annotations

from typing import (
    Any,
    TYPE_CHECKING,
)
from ..impl.objects import (
    PersistentGuildCategory,
    PersistentGuildNewsChannel,
    PersistentGuildNewsThread,
    PersistentGuildPrivateThread,
    PersistentGuildPublicThread,
    PersistentGuildTextChannel,
    PersistentGuildVoiceChannel,
    PersistentGuildMediaChannel,
    PersistentGuildForumChannel,
    PersistentGuildStageChannel,
)

import hikari

if TYPE_CHECKING:
    from ..impl.cache import Cache
    from ..impl.objects import (
        PersistentGuildChannel,
    )


__all__ = ()

def _build_channel( # noqa: PLR0911
    cache: Cache,
    ctype: hikari.ChannelType,
    k: dict[str, Any],
) -> PersistentGuildChannel:
    common = {
        "id": k["id"],
        "name": k["name"],
        "type": k["type"],
        "guild_id": k["guild_id"],
    }

    match ctype:
        case hikari.ChannelType.GUILD_TEXT:
            return PersistentGuildTextChannel(
                cache,
                **common,
                parent_id=k["parent_id"],
                position=k["position"],
                is_nsfw=bool(k["is_nsfw"]),
                permission_overwrites=k["permission_overwrites"] or {},
                topic=k["topic"],
                last_message_id=k["last_message_id"],
                rate_limit_per_user=k["rate_limit_per_user"],
                last_pin_timestamp=k["last_pin_timestamp"],
                default_auto_archive_duration=k["default_auto_archive_duration"],
                application_id=k.get("application_id"),
                flags=k["flags"],
            )
        case hikari.ChannelType.GUILD_VOICE:
            return PersistentGuildVoiceChannel(
                cache,
                **common,
                parent_id=k["parent_id"],
                position=k["position"],
                is_nsfw=bool(k["is_nsfw"]),
                permission_overwrites=k["permission_overwrites"] or {},
                bitrate=k["bitrate"],
                region=k["region"],
                user_limit=k["user_limit"],
                video_quality_mode=k["video_quality_mode"],
                last_message_id=k["last_message_id"],
                application_id=k.get("application_id"),
                flags=k["flags"],
            )
        case hikari.ChannelType.GUILD_CATEGORY:
            return PersistentGuildCategory(
                cache,
                **common,
                parent_id=k["parent_id"],
                position=k["position"],
                is_nsfw=bool(k["is_nsfw"]),
                permission_overwrites=k["permission_overwrites"] or {},
                application_id=k.get("application_id"),
                flags=k["flags"],
            )
        case hikari.ChannelType.GUILD_NEWS:
            return PersistentGuildNewsChannel(
                cache,
                **common,
                parent_id=k["parent_id"],
                position=k["position"],
                is_nsfw=bool(k["is_nsfw"]),
                permission_overwrites=k["permission_overwrites"] or {},
                topic=k["topic"],
                last_message_id=k["last_message_id"],
                last_pin_timestamp=k["last_pin_timestamp"],
                default_auto_archive_duration=k["default_auto_archive_duration"],
                application_id=k.get("application_id"),
            )
        case hikari.ChannelType.GUILD_NEWS_THREAD:
            return PersistentGuildNewsThread(
                cache,
                **common,
                parent_id=k["parent_id"],
                last_message_id=k["last_message_id"],
                last_pin_timestamp=k["last_pin_timestamp"],
                rate_limit_per_user=k["rate_limit_per_user"],
                approximate_message_count=k["approximate_message_count"],
                approximate_member_count=k["approximate_member_count"],
                member=k["member"],
                owner_id=k["owner_id"],
                metadata=k["metadata"],
                application_id=k.get("application_id"),
            )
        case hikari.ChannelType.GUILD_PUBLIC_THREAD:
            return PersistentGuildPublicThread(
                cache,
                **common,
                parent_id=k["parent_id"],
                last_message_id=k["last_message_id"],
                last_pin_timestamp=k["last_pin_timestamp"],
                rate_limit_per_user=k["rate_limit_per_user"],
                approximate_message_count=k["approximate_message_count"],
                approximate_member_count=k["approximate_member_count"],
                member=k["member"],
                owner_id=k["owner_id"],
                metadata=k["metadata"],
                applied_tag_ids=k["applied_tag_ids"],
                application_id=k.get("application_id"),
                flags=k["flags"],
            )
        case hikari.ChannelType.GUILD_PRIVATE_THREAD:
            return PersistentGuildPrivateThread(
                cache,
                **common,
                parent_id=k["parent_id"],
                last_message_id=k["last_message_id"],
                last_pin_timestamp=k["last_pin_timestamp"],
                rate_limit_per_user=k["rate_limit_per_user"],
                approximate_message_count=k["approximate_message_count"],
                approximate_member_count=k["approximate_member_count"],
                member=k["member"],
                owner_id=k["owner_id"],
                metadata=k["metadata"],
                application_id=k.get("application_id"),
            )
        case hikari.ChannelType.GUILD_STAGE:
            return PersistentGuildStageChannel(
                cache,
                **common,
                parent_id=k["parent_id"],
                position=k["position"],
                is_nsfw=bool(k["is_nsfw"]),
                permission_overwrites=k["permission_overwrites"] or {},
                bitrate=k["bitrate"],
                region=k["region"],
                user_limit=k["user_limit"],
                video_quality_mode=k["video_quality_mode"],
                last_message_id=k["last_message_id"],
                application_id=k.get("application_id"),
                flags=k["flags"],
            )
        case hikari.ChannelType.GUILD_FORUM:
            return PersistentGuildForumChannel(
                cache,
                **common,
                parent_id=k["parent_id"],
                position=k["position"],
                is_nsfw=bool(k["is_nsfw"]),
                permission_overwrites=k["permission_overwrites"] or {},
                topic=k["topic"],
                last_thread_id=k["last_thread_id"],
                rate_limit_per_user=k["rate_limit_per_user"],
                default_thread_rate_limit_per_user=k["default_thread_rate_limit_per_user"],
                default_auto_archive_duration=k["default_auto_archive_duration"],
                available_tags=k["available_tags"] or [],
                default_sort_order=k["default_sort_order"],
                default_layout=k["default_layout"],
                default_reaction_emoji_id=k["default_reaction_emoji_id"],
                default_reaction_emoji_name=k["default_reaction_emoji_name"],
                application_id=k.get("application_id"),
                flags=k["flags"],
            )
        case hikari.ChannelType.GUILD_MEDIA:
            return PersistentGuildMediaChannel(
                cache,
                **common,
                parent_id=k["parent_id"],
                position=k["position"],
                is_nsfw=bool(k["is_nsfw"]),
                permission_overwrites=k["permission_overwrites"] or {},
                topic=k["topic"],
                last_thread_id=k["last_thread_id"],
                rate_limit_per_user=k["rate_limit_per_user"],
                default_thread_rate_limit_per_user=k["default_thread_rate_limit_per_user"],
                default_auto_archive_duration=k["default_auto_archive_duration"],
                available_tags=k["available_tags"] or [],
                default_sort_order=k["default_sort_order"],
                default_layout=k["default_layout"],
                default_reaction_emoji_id=k["default_reaction_emoji_id"],
                default_reaction_emoji_name=k["default_reaction_emoji_name"],
                application_id=k.get("application_id"),
                flags=k["flags"],
            )
        case _:
            error: str = f"Unhandled channel type: {ctype!r}"
            raise ValueError(error)
