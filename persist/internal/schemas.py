from __future__ import annotations

from .codecs import (
    CodecDatetime,
    CodecTimedelta,
)
from .definitions import (
    DataType,
    Field,
    Table,
)
from .serializers import (
    Attr,
    SerializerCodec,
    SerializerEnum,
    SerializerEnumLenient,
    SerializerFlag,
    SerializerIdentity,
    SerializerList,
    SerializerKeyedMapping,
    SerializerObject,
)

import hikari
import hikari.users


__all__ = ()

CHANNELS: Table = Table(
    name="channels",
    fields=(
        Field("id", DataType.BIGINT, nullable=False),
        Field("_sync", DataType.INTEGER, nullable=False),
        Field("name", DataType.STRING),
        Field("type", DataType.TINYINT, nullable=False, serializer=SerializerEnum(
            hikari.ChannelType,
        )),
        Field("guild_id", DataType.BIGINT, nullable=False),
        Field("parent_id", DataType.BIGINT),
        Field("position", DataType.SMALLINT),
        Field("is_nsfw", DataType.BOOLEAN),
        Field("permission_overwrites", DataType.JSON, serializer=SerializerKeyedMapping(
            SerializerObject(
                factory=hikari.PermissionOverwrite,
                attrs=(
                    Attr("id"),
                    Attr("type", serializer=SerializerEnum(hikari.PermissionOverwriteType)),
                    Attr("allow", serializer=SerializerFlag(hikari.Permissions)),
                    Attr("deny", serializer=SerializerFlag(hikari.Permissions)),
                ),
            ),
        )),
        Field("topic", DataType.STRING),
        Field("last_message_id", DataType.BIGINT),
        Field("rate_limit_per_user", DataType.SMALLINT, codec=CodecTimedelta()),
        Field("last_pin_timestamp", DataType.DATETIME),
        Field("default_auto_archive_duration", DataType.SMALLINT, codec=CodecTimedelta()),
        Field("bitrate", DataType.INTEGER),
        Field("region", DataType.STRING),
        Field("user_limit", DataType.TINYINT),
        Field("video_quality_mode", DataType.TINYINT, serializer=SerializerEnum(
            hikari.VideoQualityMode,
        )),
        Field("approximate_message_count", DataType.INTEGER),
        Field("approximate_member_count", DataType.TINYINT),
        Field("member", DataType.JSON, serializer=SerializerObject(
            factory=hikari.ThreadMember,
            attrs=(
                Attr("thread_id"),
                Attr("user_id"),
                Attr("joined_at", serializer=SerializerCodec(CodecDatetime())),
                Attr("flags"),
            ),
        )),
        Field("owner_id", DataType.BIGINT),
        Field("metadata", DataType.JSON, serializer=SerializerObject(
            factory=hikari.ThreadMetadata,
            attrs=(
                Attr("is_archived"),
                Attr("is_invitable"),
                Attr("auto_archive_duration"),
                Attr("archive_timestamp", serializer=SerializerCodec(CodecDatetime())),
                Attr("is_locked"),
                Attr("created_at", serializer=SerializerCodec(CodecDatetime())),
            ),
        )),
        Field("applied_tag_ids", DataType.JSON, serializer=SerializerList(SerializerIdentity())),
        Field("flags", DataType.INTEGER, serializer=SerializerFlag(hikari.ChannelFlag)),
        Field("last_thread_id", DataType.BIGINT),
        Field("default_thread_rate_limit_per_user", DataType.SMALLINT, codec=CodecTimedelta()),
        Field("available_tags", DataType.JSON, serializer=SerializerList(SerializerObject(
            factory=hikari.ForumTag,
            attrs=(
                Attr("id"),
                Attr("name"),
                Attr("moderated"),
                Attr("emoji_id"),
            ),
        ))),
        Field("default_sort_order", DataType.TINYINT, serializer=SerializerEnum(
            hikari.ForumSortOrderType,
        )),
        Field("default_layout", DataType.TINYINT, serializer=SerializerEnum(
            hikari.ForumLayoutType,
        )),
        Field("default_reaction_emoji_id", DataType.BIGINT),
        Field("default_reaction_emoji_name", DataType.STRING),
    ),
    primary_key=("id",),
)
GUILDS: Table = Table(
    name="guilds",
    fields=(
        Field("id", DataType.BIGINT, nullable=False),
        Field("_sync", DataType.INTEGER, nullable=False),
        Field("icon_hash", DataType.STRING),
        Field("name", DataType.STRING, nullable=False),
        Field("features", DataType.JSON, serializer=SerializerList(SerializerEnumLenient(
            hikari.GuildFeature,
        ))),
        Field("incidents", DataType.JSON, serializer=SerializerObject(
            factory=hikari.GuildIncidents,
            attrs=(
                Attr("invites_disabled_until", serializer=SerializerCodec(CodecDatetime())),
                Attr("dms_disabled_until", serializer=SerializerCodec(CodecDatetime())),
                Attr("dm_spam_detected_at", serializer=SerializerCodec(CodecDatetime())),
                Attr("raid_detected_at", serializer=SerializerCodec(CodecDatetime())),
            ),
        )),
        Field("application_id", DataType.BIGINT),
        Field("afk_channel_id", DataType.BIGINT),
        Field("afk_timeout", DataType.SMALLINT, nullable=False, codec=CodecTimedelta()),
        Field("banner_hash", DataType.STRING),
        Field("default_message_notifications", DataType.TINYINT, serializer=SerializerEnum(
            hikari.GuildMessageNotificationsLevel,
        ), nullable=False),
        Field("description", DataType.STRING),
        Field("discovery_splash_hash", DataType.STRING),
        Field("explicit_content_filter", DataType.TINYINT, serializer=SerializerEnum(
            hikari.GuildExplicitContentFilterLevel,
        ), nullable=False),
        Field("is_widget_enabled", DataType.BOOLEAN),
        Field("max_video_channel_users", DataType.TINYINT),
        Field("mfa_level", DataType.TINYINT, serializer=SerializerEnum(
            hikari.GuildMFALevel,
        ), nullable=False),
        Field("owner_id", DataType.BIGINT, nullable=False),
        Field("preferred_locale", DataType.STRING, serializer=SerializerEnum(
            hikari.Locale,
        ), nullable=False),
        Field("premium_subscription_count", DataType.SMALLINT),
        Field("premium_tier", DataType.TINYINT, serializer=SerializerEnum(hikari.GuildPremiumTier)),
        Field("public_updates_channel_id", DataType.BIGINT),
        Field("rules_channel_id", DataType.BIGINT),
        Field("splash_hash", DataType.STRING),
        Field("system_channel_flags", DataType.SMALLINT, serializer=SerializerFlag(
            hikari.GuildSystemChannelFlag,
        ), nullable=False),
        Field("system_channel_id", DataType.BIGINT),
        Field("vanity_url_code", DataType.STRING),
        Field("verification_level", DataType.TINYINT, serializer=SerializerEnum(
            hikari.GuildVerificationLevel,
        )),
        Field("widget_channel_id", DataType.BIGINT),
        Field("nsfw_level", DataType.TINYINT, serializer=SerializerEnum(hikari.GuildNSFWLevel)),
    ),
    primary_key=("id",),
)
MEMBERS: Table = Table(
    name="members",
    fields=(
        Field("id", DataType.BIGINT, nullable=False),
        Field("guild_id", DataType.BIGINT, nullable=False),
        Field("_sync", DataType.INTEGER, nullable=False),
        Field("joined_at", DataType.DATETIME),
        Field("nickname", DataType.STRING),
        Field("premium_since", DataType.DATETIME),
        Field("raw_communication_disabled_until", DataType.DATETIME),
        Field("role_ids", DataType.JSON, serializer=SerializerList(SerializerIdentity())),
        Field("guild_avatar_decoration", DataType.JSON, serializer=SerializerObject(
            factory=hikari.users.AvatarDecoration,
            attrs=(
                Attr("asset_hash"),
                Attr("sku_id"),
                Attr("expires_at", serializer=SerializerCodec(CodecDatetime())),
            ),
        )),
        Field("guild_avatar_hash", DataType.STRING),
        Field("guild_banner_hash", DataType.STRING),
        Field("guild_flags", DataType.SMALLINT, serializer=SerializerFlag(hikari.GuildMemberFlags)),
    ),
    primary_key=("id", "guild_id",),
)
ROLES: Table = Table(
    name="roles",
    fields=(
        Field("id", DataType.BIGINT, nullable=False),
        Field("_sync", DataType.INTEGER, nullable=False),
        Field("name", DataType.STRING, nullable=False),
        Field("color", DataType.INTEGER, nullable=False),
        Field("colors", DataType.JSON, serializer=SerializerObject(
            factory=hikari.ColorGradient,
            attrs=(
                Attr("primary_color"),
                Attr("secondary_color"),
                Attr("tertiary_color"),
            ),
        )),
        Field("guild_id", DataType.BIGINT, nullable=False),
        Field("is_hoisted", DataType.BOOLEAN),
        Field("icon_hash", DataType.STRING),
        Field("unicode_emoji", DataType.STRING, serializer=SerializerEnum(hikari.UnicodeEmoji)),
        Field("is_managed", DataType.BOOLEAN, nullable=False),
        Field("is_mentionable", DataType.BOOLEAN, nullable=False),
        Field("permissions", DataType.INTEGER, serializer=SerializerFlag(
            hikari.Permissions,
        ), nullable=False),
        Field("position", DataType.SMALLINT, nullable=False),
        Field("bot_id", DataType.BIGINT),
        Field("integration_id", DataType.BIGINT),
        Field("is_premium_subscriber_role", DataType.BOOLEAN, nullable=False),
        Field("subscription_listing_id", DataType.BIGINT),
        Field("is_available_for_purchase", DataType.BOOLEAN, nullable=False),
        Field("is_guild_linked_role", DataType.BOOLEAN, nullable=False),
    ),
    primary_key=("id",),
)
USERS: Table = Table(
    name="users",
    fields=(
        Field("id", DataType.BIGINT, nullable=False),
        Field("_sync", DataType.INTEGER, nullable=False),
        Field("discriminator", DataType.STRING, nullable=False),
        Field("username", DataType.STRING, nullable=False),
        Field("global_name", DataType.STRING),
        Field("avatar_decoration", DataType.JSON, serializer=SerializerObject(
            factory=hikari.users.AvatarDecoration,
            attrs=(
                Attr("asset_hash"),
                Attr("sku_id"),
                Attr("expires_at", serializer=SerializerCodec(CodecDatetime())),
            ),
        )),
        Field("avatar_hash", DataType.STRING),
        Field("banner_hash", DataType.STRING),
        Field("accent_color", DataType.SMALLINT),
        Field("is_bot", DataType.BOOLEAN, nullable=False),
        Field("is_system", DataType.BOOLEAN, nullable=False),
        Field("flags", DataType.INTEGER, serializer=SerializerFlag(
            hikari.UserFlag,
        ), nullable=False),
        Field("primary_guild", DataType.JSON, serializer=SerializerObject(
            factory=hikari.PrimaryGuild,
            attrs=(
                Attr("identity_guild_id"),
                Attr("identity_enabled"),
                Attr("tag"),
                Attr("badge_hash"),
            ),
        )),
    ),
    primary_key=("id",),
)

SCHEMA: tuple[Table, ...] = (
    CHANNELS,
    GUILDS,
    MEMBERS,
    ROLES,
    USERS,
)
