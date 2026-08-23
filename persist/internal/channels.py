from __future__ import annotations

import hikari


__all__ = ()

CHANNEL_FIELDS: dict[hikari.ChannelType, tuple[str, ...]] = {
    hikari.ChannelType.GUILD_TEXT: (
        "id", "name", "type", "guild_id", "parent_id", "position", "is_nsfw",
        "permission_overwrites", "topic", "last_message_id", "rate_limit_per_user",
        "last_pin_timestamp", "default_auto_archive_duration", "application_id", "flags",
    ),
    hikari.ChannelType.GUILD_VOICE: (
        "id", "name", "type", "guild_id", "parent_id", "position", "is_nsfw",
        "permission_overwrites", "bitrate", "region", "user_limit",
        "video_quality_mode", "last_message_id", "application_id", "flags",
    ),
    hikari.ChannelType.GUILD_CATEGORY: (
        "id", "name", "type", "guild_id", "parent_id", "position", "is_nsfw",
        "permission_overwrites", "application_id", "flags",
    ),
    hikari.ChannelType.GUILD_NEWS: (
        "id", "name", "type", "guild_id", "parent_id", "position", "is_nsfw",
        "permission_overwrites", "topic", "last_message_id",
        "last_pin_timestamp", "default_auto_archive_duration", "application_id",
    ),
    hikari.ChannelType.GUILD_NEWS_THREAD: (
        "id", "name", "type", "guild_id", "parent_id", "last_message_id",
        "last_pin_timestamp", "rate_limit_per_user", "approximate_message_count",
        "approximate_member_count", "member", "owner_id", "metadata", "application_id",
    ),
    hikari.ChannelType.GUILD_PUBLIC_THREAD: (
        "id", "name", "type", "guild_id", "parent_id", "last_message_id",
        "last_pin_timestamp", "rate_limit_per_user", "approximate_message_count",
        "approximate_member_count", "member", "owner_id", "metadata",
        "applied_tag_ids", "flags", "application_id",
    ),
    hikari.ChannelType.GUILD_PRIVATE_THREAD: (
        "id", "name", "type", "guild_id", "parent_id", "last_message_id",
        "last_pin_timestamp", "rate_limit_per_user", "approximate_message_count",
        "approximate_member_count", "member", "owner_id", "metadata", "application_id",
    ),
    hikari.ChannelType.GUILD_STAGE: (
        "id", "name", "type", "guild_id", "parent_id", "position", "is_nsfw",
        "permission_overwrites", "bitrate", "region", "user_limit",
        "video_quality_mode", "last_message_id", "application_id", "flags",
    ),
    hikari.ChannelType.GUILD_FORUM: (
        "id", "name", "type", "guild_id", "parent_id", "position", "is_nsfw",
        "permission_overwrites", "topic", "last_thread_id", "rate_limit_per_user",
        "default_thread_rate_limit_per_user", "default_auto_archive_duration",
        "flags", "available_tags", "default_sort_order", "default_layout",
        "default_reaction_emoji_id", "default_reaction_emoji_name", "application_id",
    ),
    hikari.ChannelType.GUILD_MEDIA: (
        "id", "name", "type", "guild_id", "parent_id", "position", "is_nsfw",
        "permission_overwrites", "topic", "last_thread_id", "rate_limit_per_user",
        "default_thread_rate_limit_per_user", "default_auto_archive_duration",
        "flags", "available_tags", "default_sort_order", "default_layout",
        "default_reaction_emoji_id", "default_reaction_emoji_name", "application_id", "flags",
    ),
}
