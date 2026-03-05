from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from hikaripersist.cached.base import CachedObject
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import hikari

__all__ = ("CachedGuild",)

@dataclass(frozen=True, slots=True)
class CachedGuild(CachedObject):
    """Represents a guild in persistent cache."""

    id: hikari.Snowflake
    """The ID of the guild."""
    name: str
    """The name of the guild."""
    description: str | None
    """If present, the description of the guild."""
    owner: hikari.Snowflake
    """The ID of the guild's parent user."""
    created: datetime
    """The timestamp in which the guild was created."""
    icon: str | None
    """If present, the hash of the guild icon."""
    banner: str | None
    """If present, the hash of the guild banner."""
    nsfw: hikari.GuildNSFWLevel
    """The NSFW level of the guild."""
    mfa: hikari.GuildMFALevel
    """The MFA level of the guild."""
    verification: hikari.GuildVerificationLevel
    """The verification level of the guild."""
    features: Sequence[hikari.GuildFeature]
    """All features of the guild."""
    vanity_url: str | None
    """If present, the vanity url of the guild."""
    premium_tier: hikari.GuildPremiumTier
    """The guild's tier of premium."""

    @classmethod
    def from_sqlite(
        cls: type[CachedGuild],
        row, # noqa: ANN001 - Ambiguous because aiosqlite is optional
    ) -> CachedGuild:
        return cls(
            row[0],
            row[1],
            row[2],
            row[3],
            datetime.fromtimestamp(row[4], timezone.utc),
            row[5],
            row[6],
            hikari.GuildNSFWLevel(row[7]),
            hikari.GuildMFALevel(row[8]),
            hikari.GuildVerificationLevel(row[9]),
            set(row[10].split(',')),
            row[11],
            hikari.GuildPremiumTier(row[12]),
        )
