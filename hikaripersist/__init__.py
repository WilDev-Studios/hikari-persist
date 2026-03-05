"""
### hikari-persist: `0.1.0a2`
A lightweight and modular persistent cache library for `hikari`-based Discord bots.

**Documentation:** https://hikari-persist.wildevstudios.net/en/0.1.0a2\n
**GitHub:** https://github.com/WilDev-Studios/hikari-persist
"""

__version__ = "0.1.0a2"
__all__ = (  # noqa: RUF022
    "Backend",
    "Cache",
    "CacheIterator",
    "CachedChannel",
    "CachedGuild",
    "CachedMember",
    "CachedMessage",
    "CachedObject",
    "CachedPermissionOverwrite",
    "CachedRole",
    "CacheMessageCreateEvent",
    "CacheMessageDeleteEvent",
    "CacheMessageUpdateEvent",
    "ChannelRule",
    "GuildRule",
    "MemberRule",
    "MessageRule",
    "RoleRule",
    "Rule",
    "SQLiteBackend",
)

from hikaripersist.backend import (
    Backend,
    SQLiteBackend,
)
from hikaripersist.cached import (
    CachedChannel,
    CachedGuild,
    CachedMember,
    CachedMessage,
    CachedObject,
    CachedPermissionOverwrite,
    CachedRole,
)
from hikaripersist.cache import Cache
from hikaripersist.impl import CacheIterator
from hikaripersist.rule import (
    ChannelRule,
    GuildRule,
    MemberRule,
    MessageRule,
    RoleRule,
    Rule,
)
