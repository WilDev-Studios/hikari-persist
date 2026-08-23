from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from collections.abc import (
    Callable,
    Mapping,
    Sequence,
)
from enum import (
    Enum,
    Flag,
)
from typing import (
    Any,
    Generic,
    TYPE_CHECKING,
    TypeVar,
)
from .codecs import JSONValue

if TYPE_CHECKING:
    from .codecs import Codec

E = TypeVar('E', bound=Enum)
F = TypeVar('F', bound=Flag)
T = TypeVar('T')
U = TypeVar('U')

__all__ = ()


class Serializer(ABC, Generic[T, U]):
    @abstractmethod
    def deserialize(self, value: T) -> U: raise NotImplementedError
    @abstractmethod
    def serialize(self, value: U) -> T: raise NotImplementedError

class SerializerIdentity(Serializer[JSONValue, JSONValue]):
    def deserialize(self, value: JSONValue) -> JSONValue: return value
    def serialize(self, value: JSONValue) -> JSONValue: return value

class SerializerCodec(Serializer[T, U]):
    def __init__(self, codec: Codec[T, U]) -> None:
        self.codec: Codec[T, U] = codec
    def deserialize(self, value: T) -> U: return self.codec.decode(value)
    def serialize(self, value: U) -> T: return self.codec.encode(value)

class SerializerEnum(Serializer[int | str, E]):
    def __init__(self, enum: type[E]) -> None:
        self.enum: type[E] = enum
    def deserialize(self, value: int | str) -> E: return self.enum(value)
    def serialize(self, value: E) -> int | str: return value.value

class SerializerEnumLenient(Serializer[int | str, E | str]):
    def __init__(self, enum: type[E]) -> None:
        self.enum: type[E] = enum
    def deserialize(self, value: int | str) -> E | str:
        try:
            return self.enum(value)
        except ValueError:
            return value
    def serialize(self, value: E | str) -> int | str:
        return value.value if isinstance(value, self.enum) else value

class SerializerFlag(Serializer[int, F]):
    def __init__(self, flag: type[F]) -> None:
        self.flag: type[F] = flag
    def deserialize(self, value: int) -> F: return self.flag(value)
    def serialize(self, value: F) -> int: return value.value

class SerializerList(Serializer[list[JSONValue], Sequence[U]]):
    def __init__(self, item: Serializer[JSONValue, U]) -> None:
        self.item: Serializer[JSONValue, U] = item
    def deserialize(self, value: list[JSONValue]) -> Sequence[U]:
        return [self.item.deserialize(v) for v in value] if value else []
    def serialize(self, value: Sequence[U]) -> list[JSONValue]:
        return [self.item.serialize(v) for v in value] if value else []

class SerializerKeyedMapping(Serializer[list[JSONValue], Mapping[Any, U]]):
    def __init__(self, item: Serializer[JSONValue, U], key_attr: str = "id") -> None:
        self.item: Serializer[JSONValue, U] = item
        self.key_attr: str = key_attr
    def deserialize(self, value: list[JSONValue]) -> Mapping[Any, U]:
        items: list[U] = [self.item.deserialize(v) for v in value] if value else []
        return {getattr(i, self.key_attr): i for i in items}
    def serialize(self, value: Mapping[Any, U]) -> list[JSONValue]:
        return [self.item.serialize(v) for v in value.values()] if value else []

class Attr:
    __slots__ = (
        "key",
        "name",
        "serializer",
    )

    def __init__(
        self,
        name: str,
        key: str | None = None,
        serializer: Serializer[Any, Any] | None = None
    ) -> None:
        self.name: str = name
        self.key: str | None = key or name
        self.serializer: Serializer[Any, Any] | None = serializer

class SerializerObject(Serializer[dict[str, JSONValue], U]):
    def __init__(self, factory: Callable[..., U], attrs: Sequence[Attr]) -> None:
        self.factory: Callable[..., U] = factory
        self.attrs: Sequence[Attr] = attrs

    def deserialize(self, value: dict[str, JSONValue]) -> U:
        kwargs: dict[str, Any] = {}
        for a in self.attrs:
            raw: JSONValue = value.get(a.key)
            kwargs[a.name] = a.serializer.deserialize(raw) if (raw is not None and a.serializer) else raw # noqa: E501

        return self.factory(**kwargs)

    def serialize(self, value: U) -> dict[str, JSONValue]:
        out: dict[str, JSONValue] = {}
        for a in self.attrs:
            v: Any = getattr(value, a.name)
            out[a.key] = a.serializer.serialize(v) if (v is not None and a.serializer) else v

        return out
