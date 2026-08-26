from __future__ import annotations

from dataclasses import dataclass
from enum import (
    Enum,
)
from typing import (
    Any,
    Generic,
    TYPE_CHECKING,
    TypeVar,
)
from .codecs import (
    CodecBoolean,
    CodecDatetime,
    CodecJSON,
)
from .serializers import Serializer

if TYPE_CHECKING:
    from .codecs import Codec

T = TypeVar('T')


__all__ = ()

class DataType(Enum):
    """Enum of all supported database datatypes."""

    BOOLEAN   = "boolean"
    """Any boolean (`True`/`False`) value."""
    BYTES     = "bytes"
    """Any bytes-like (`bytes`, `memoryview`, etc.) value."""
    DATETIME  = "datetime"
    """Any `datetime` value."""
    JSON      = "json"
    """Any encoded JSON value."""
    STRING    = "string"
    """Any `str` value."""

    TINYINT   = "tinyint"
    """Any signed `int` value that occupies `1 byte` (`-128` - `127`)."""
    SMALLINT  = "smallint"
    """Any signed `int` value that occupies `2 bytes` (`-32,768` - `32,767`)."""
    INTEGER   = "integer"
    """Any signed `int` value that occupies `4 bytes` (`-2,147,483,648` - `2,147,483,647`)."""
    BIGINT    = "bigint"
    """
    Any signed `int` value that occupies `8 bytes`
    (`-9,223,372,036,854,775,808` - `9,223,372,036,854,775,807`).
    """

    DECIMAL   = "decimal"
    DOUBLE    = "double"
    FLOAT     = "float"

DEFAULT_CODECS: dict[DataType, Codec[Any, Any]] = {
    DataType.BOOLEAN: CodecBoolean(),
    DataType.DATETIME: CodecDatetime(),
    DataType.JSON: CodecJSON(),
}
"""Default codec mappings to specific datatypes."""

@dataclass(frozen=True, slots=True)
class Field(Generic[T]):
    """Represents a column in a backend database."""

    name: str
    """The name of the column/field."""
    datatype: DataType
    """The datatype of the column/field."""
    nullable: bool = True
    """If this column supports `None`/`null` values."""
    codec: Codec[Any, Any] | None = None
    """An optional codec override, ignoring the datatype."""
    serializer: Serializer[Any, T] | None = None
    """The serializer class used to convert values between the database and language."""

    def resolve_codec(self) -> Codec[Any, Any] | None:
        """
        Get the codec associated with the datatype, if any.

        Returns
        -------
        Codec[Any, Any] | None
            If a codec is associated with the field datatype.
        """

        return self.codec or DEFAULT_CODECS.get(self.datatype)

@dataclass(frozen=True, slots=True)
class Table:
    """Represents a backend database table."""

    name: str
    """The name of the table."""
    fields: tuple[Field, ...]
    """All columns/fields in the table."""
    primary_key: tuple[str, ...] = ()
    """The primary key columsn/fields to index."""
