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
    """
    Decode a database row into a mapping of Python values.

    Parameters
    ----------
    fields : Sequence[Field]
        All fields/columns in the desired table.
    row : Sequence[Any]
        The row from the database to decode.

    Returns
    -------
    dict[str, Any]
        The decoded mapping of all row contents.
    """

    return {f.name: _decode(f, v) for f, v in zip(fields, row, strict=True)}

class RowMapper(Generic[U]):
    """Maps database rows to Python objects and vice versa."""

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
        """
        Create a map that converts between database rows and Python objects and vice versa.

        Parameters
        ----------
        table : Table
            The database table associated with this mapper.
        factory : Callable[[dict[str, Any]], U]
            A callable used to construct an object from decoded row data.
        fields : Sequence[Field] | None
            The fields to include when mapping rows.
            If omitted, all fields defined by `table` are used.
        extract : Callable[[U, str], Any] | None
            A callable used to extract a field value from an object when converting it into a
            database row. If omitted, `getattr` is used and missing attributes resolve to `None`.

        Notes
        -----
        `RowMapper` handles the conversion pipeline around each field, including serializers and
        codecs. Values read from the database are decoded before being passed to `factory`; values
        written to the database are serialized and encoded before being returned.

        The mapper can optionally operate on a subset of a table's fields. This is useful for
        objects whose database representation differs depending on their concrete type, such as the
        different Discord channel types.
        """

        self.table: Table = table
        self.fields: tuple[Field, ...] = tuple(fields) if fields is not None else table.fields
        self.factory: Callable[[dict[str, Any]], U] = factory
        self.extract: Callable[[U, str], Any] = extract or (
            lambda obj, name: getattr(obj, name, None)
        )

    def from_row(self, row: Sequence[Any]) -> U:
        """
        Construct an object from a database row.

        Parameters
        ----------
        row : Sequence[Any]
            The raw database row, with values corresponding to the mappers's configured fields.

        Returns
        -------
        U
            The object constructed by the mapper's factory after all field values have been decoded.
        """

        return self.factory(decode_row(self.fields, row))

    @property
    def names(self) -> tuple[str, ...]:
        """Get the database column names/fields handled by this mapper."""

        return tuple(f.name for f in self.fields)

    def to_row(self, obj: U, *, sync: int | None = None) -> tuple[Any, ...]:
        """
        Convert an object into a database row.

        Parameters
        ----------
        obj : U
            The object whose attributes should be written to the database.
        sync : int | None
            Optional synchronization value used for the special `_sync` field.
            When present, this value overrides the object's `_sync` attribute.

        Returns
        -------
        tuple[Any, ...]
            A database-ready row containing serialized and encoded field values.
        """

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
"""Specialized row mappers for each channel type."""

GUILD_MAPPER: RowMapper  = RowMapper(GUILDS, factory=None)
"""A row mapper specific to guilds."""
ROLE_MAPPER: RowMapper   = RowMapper(ROLES, factory=None)
"""A row mapper specific to roles."""
MEMBER_MAPPER: RowMapper = RowMapper(MEMBERS, factory=None)
"""A row mapper specific to members."""
USER_MAPPER: RowMapper   = RowMapper(USERS, factory=None)
"""A row mapper specific to users."""
