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
    BOOLEAN   = "boolean"
    BYTES     = "bytes"
    DATETIME  = "datetime"
    JSON      = "json"
    STRING    = "string"

    TINYINT   = "tinyint"
    SMALLINT  = "smallint"
    INTEGER   = "integer"
    BIGINT    = "bigint"

    DECIMAL   = "decimal"
    DOUBLE    = "double"
    FLOAT     = "float"

DEFAULT_CODECS: dict[DataType, Codec[Any, Any]] = {
    DataType.BOOLEAN: CodecBoolean(),
    DataType.DATETIME: CodecDatetime(),
    DataType.JSON: CodecJSON(),
}

@dataclass(frozen=True, slots=True)
class Field(Generic[T]):
    name: str
    datatype: DataType
    nullable: bool = True
    codec: Codec[Any, Any] | None = None
    serializer: Serializer[Any, T] | None = None

    def resolve_codec(self) -> Codec[Any, Any] | None:
        return self.codec or DEFAULT_CODECS.get(self.datatype)

@dataclass(frozen=True, slots=True)
class Table:
    name: str
    fields: tuple[Field, ...]
    primary_key: tuple[str, ...] = ()
