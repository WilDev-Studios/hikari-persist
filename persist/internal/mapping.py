from __future__ import annotations

from collections.abc import (
    Callable,
    Sequence,
)
from typing import (
    Any,
    Generic,
    TYPE_CHECKING,
    TypeVar,
)
from .channels import CHANNEL_FIELDS
from .schemas import (
    CHANNELS,
    GUILDS,
    MEMBERS,
    ROLES,
    USERS,
)

if TYPE_CHECKING:
    from .codecs import Codec
    from .definitions import (
        Field,
        Table,
    )

    import hikari

U = TypeVar('U')

__all__ = ()


def _decode(field: Field, value: Any) -> Any: # noqa: ANN401
    if value is None:
        return None

    codec: Codec[Any, Any] | None = field.resolve_codec()
    if codec:
        value: Any = codec.decode(value)

    return field.serializer.deserialize(value) if field.serializer else value

def _encode(field: Field, value: Any) -> Any: # noqa: ANN401
    if value is None:
        return None

    if field.serializer:
        value: Any = field.serializer.serialize(value)

    codec: Codec[Any, Any] | None = field.resolve_codec()
    return codec.encode(value) if codec else value

def decode_row(fields: Sequence[Field], row: Sequence[Any]) -> dict[str, Any]:
    return {f.name: _decode(f, v) for f, v in zip(fields, row, strict=True)}

class RowMapper(Generic[U]):
    __slots__ = (
        "extract",
        "factory",
        "fields",
        "table",
    )

    def __init__(
        self,
        table: Table,
        factory: Callable[[dict[str, Any]], U],
        fields: Sequence[Field] | None = None,
        extract: Callable[[U, str], Any] | None = None,
    ) -> None:
        self.table: Table = table
        self.fields: tuple[Field, ...] = tuple(fields) if fields is not None else table.fields
        self.factory: Callable[[dict[str, Any], U]] = factory
        self.extract: Callable[[U, str], Any] = extract or (
            lambda obj, name: getattr(obj, name, None)
        )

    def from_row(self, row: Sequence[Any]) -> U:
        return self.factory(decode_row(self.fields, row))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)

    def to_row(self, obj: U, *, sync: int | None = None) -> tuple[Any, ...]:
        return tuple(
            _encode(
                f,
                sync if f.name == "_sync" else self.extract(obj, f.name)
            ) for f in self.fields
        )

CHANNEL_WRITE_MAPPERS: dict[hikari.ChannelType, RowMapper[hikari.GuildChannel]] = {
    ctype: RowMapper(
        CHANNELS,
        factory=lambda _: None,
        fields=tuple(f for f in CHANNELS.fields if f.name in names or f.name == "_sync"),
        extract=lambda obj, name: getattr(obj, name, None),
    )
    for ctype, names in CHANNEL_FIELDS.items()
}

GUILD_MAPPER: RowMapper  = RowMapper(GUILDS, factory=None)
ROLE_MAPPER: RowMapper   = RowMapper(ROLES, factory=None)
MEMBER_MAPPER: RowMapper = RowMapper(MEMBERS, factory=None)
USER_MAPPER: RowMapper   = RowMapper(USERS, factory=None)
