"""
### hikari-persist
A lightweight and modular persistent cache library for `hikari`-based Discord bots.

**Documentation:** https://hikari-persist.wildevstudios.net/en/latest\n
**GitHub:** https://github.com/WilDev-Studios/hikari-persist
"""

__hikari_version__ = "2.7.0"
__all__ = (
    "Backend",
    "BulkChannelEvent",
    "BulkMemberEvent",
    "BulkRoleEvent",
    "Cache",
    "CacheIterator",
    "CacheIteratorStep",
    "ChannelInsertEvent",
    "ChannelRemoveEvent",
    "ChannelRule",
    "ChannelUpdateEvent",
    "GuildInsertEvent",
    "GuildRemoveEvent",
    "GuildRule",
    "GuildUpdateEvent",
    "MemberInsertEvent",
    "MemberRemoveEvent",
    "MemberRule",
    "MemberUpdateEvent",
    "PersistEvent",
    "PostgreSQLBackend",
    "RoleInsertEvent",
    "RoleRemoveEvent",
    "RoleRule",
    "RoleUpdateEvent",
    "Rule",
    "SQLiteBackend",
)

from ._version import __version__
from .backend import (
    Backend,
    PostgreSQLBackend,
    SQLiteBackend,
)
from .impl import (
    BulkChannelEvent,
    BulkMemberEvent,
    BulkRoleEvent,
    Cache,
    CacheIterator,
    CacheIteratorStep,
    ChannelInsertEvent,
    ChannelRemoveEvent,
    ChannelRule,
    ChannelUpdateEvent,
    GuildInsertEvent,
    GuildRemoveEvent,
    GuildRule,
    GuildUpdateEvent,
    MemberInsertEvent,
    MemberRemoveEvent,
    MemberRule,
    MemberUpdateEvent,
    PersistEvent,
    RoleInsertEvent,
    RoleRemoveEvent,
    RoleRule,
    RoleUpdateEvent,
    Rule,
)
