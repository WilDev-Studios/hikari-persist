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
    """Base serialization object."""

    @abstractmethod
    def deserialize(self, value: T) -> U:
        """
        Deserialize a native Python object into a higher class type.

        Parameters
        ----------
        value : T
            The value to deserialize.

        Returns
        -------
        U
            The deserialize value.
        """

        raise NotImplementedError
    @abstractmethod
    def serialize(self, value: U) -> T:
        """
        Serialize a higher class type into a native Python object.

        Parameters
        ----------
        value : U
            The value to serialize.

        Returns
        -------
        T
            The serialized value.
        """

        raise NotImplementedError

class SerializerCast(Serializer[T, U]):
    """Serializer used to serialize between a primitive and a safe reducible."""

    def __init__(self, wrapper: Callable[[T], U], primitive: type[T]) -> None:
        self.wrapper: Callable[[T], U] = wrapper
        self.primitive: type[T] = primitive

    def deserialize(self, value: T) -> U:
        return self.wrapper(value)
    def serialize(self, value: U) -> T:
        return self.primitive(value)

class SerializerIdentity(Serializer[JSONValue, JSONValue]):
    """Serializer used to serialize between different `JSON`-compatible values."""

    def deserialize(self, value: JSONValue) -> JSONValue: return value
    def serialize(self, value: JSONValue) -> JSONValue: return value

class SerializerCodec(Serializer[T, U]):
    """Serializer used to serialize between a database value and a higher class type."""

    def __init__(self, codec: Codec[T, U]) -> None:
        self.codec: Codec[T, U] = codec
    def deserialize(self, value: T) -> U: return self.codec.decode(value)
    def serialize(self, value: U) -> T: return self.codec.encode(value)

class SerializerEnum(Serializer[int | str, E]):
    """Serializer used to serialize between a Python type and an enum."""

    def __init__(self, enum: type[E]) -> None:
        self.enum: type[E] = enum
    def deserialize(self, value: int | str) -> E: return self.enum(value)
    def serialize(self, value: E) -> int | str: return value.value

class SerializerEnumLenient(Serializer[int | str, E | str]):
    """
    Serializer used to serialize between a Python type and an enum with leniency on the end result.
    """

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
    """Serializer used to serialize between a Python type and a flag."""

    def __init__(self, flag: type[F]) -> None:
        self.flag: type[F] = flag
    def deserialize(self, value: int) -> F: return self.flag(value)
    def serialize(self, value: F) -> int: return value.value

class SerializerList(Serializer[list[JSONValue], Sequence[U]]):
    """Serializer used to serialize between a list of `JSON`-compatible values and a native list."""

    def __init__(self, item: Serializer[JSONValue, U]) -> None:
        self.item: Serializer[JSONValue, U] = item
    def deserialize(self, value: list[JSONValue]) -> Sequence[U]:
        return [self.item.deserialize(v) for v in value] if value else []
    def serialize(self, value: Sequence[U]) -> list[JSONValue]:
        return [self.item.serialize(v) for v in value] if value else []

class SerializerKeyedMapping(Serializer[list[JSONValue], Mapping[Any, U]]):
    """
    Serializer used to serialize between a list of `JSON`-compatible values and a native mapping of
    those values linked to their own names as keys of the mapping.
    """

    def __init__(self, item: Serializer[JSONValue, U], key_attr: str = "id") -> None:
        self.item: Serializer[JSONValue, U] = item
        self.key_attr: str = key_attr
    def deserialize(self, value: list[JSONValue]) -> Mapping[Any, U]:
        items: list[U] = [self.item.deserialize(v) for v in value] if value else []
        return {getattr(i, self.key_attr): i for i in items}
    def serialize(self, value: Mapping[Any, U]) -> list[JSONValue]:
        return [self.item.serialize(v) for v in value.values()] if value else []

class Attr:
    """Represents an attribute of a higher class type dynamically created by a serializer."""

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
        """
        Create a new higher class type attribute.

        Parameters
        ----------
        name : str
            The name of the class attribute.
        key : str | None
            The key of the class attribute in a `JSON` mapping otherwise `name`.
        serializer : Serializer[Any, Any] | None
            If provided, a serializer used to convert a `JSON` mapping of this class attribute to a
            higher class type.
        """

        self.name: str = name
        self.key: str | None = key or name
        self.serializer: Serializer[Any, Any] | None = serializer

class SerializerObject(Serializer[dict[str, JSONValue], U]):
    """
    Serializer used to serialize between a Python mapping to a custom object based on its
    attributes.
    """

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
