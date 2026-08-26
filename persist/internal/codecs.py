from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    Generic,
    TypeAlias,
    TypeVar,
)

import json


__all__ = ()

T = TypeVar('T')
U = TypeVar('U')

JSONValue: TypeAlias = (
    bool
    | int
    | float
    | str
    | list["JSONValue"]
    | dict[str, "JSONValue"]
    | None
)
"""An alias for all JSON-accepted datatypes."""

class Codec(ABC, Generic[T, U]):
    """A base codec generic mandating specific functionality."""

    @abstractmethod
    def decode(self, value: T) -> U:
        """
        Decode the database value to the native type.

        Parameters
        ----------
        value : T
            The value to decode.

        Returns
        -------
        U
            The decoded value.
        """

        raise NotImplementedError
    @abstractmethod
    def encode(self, value: U) -> T:
        """
        Encode the native type to a database value.

        Parameters
        ----------
        value : U
            The value to encode.

        Returns
        -------
        T
            The encoded value.
        """

        raise NotImplementedError

class CodecBoolean(Codec[int, bool]):
    """Codec regarding the conversion between integers and booleans."""

    def decode(self, value: int) -> bool: return bool(value)
    def encode(self, value: bool) -> int: return int(value)

class CodecDatetime(Codec[float, datetime]):
    """Codec regarding the conversion between timestamps and datetimes."""

    _EPOCH: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    def decode(self, value: float) -> datetime: return self._EPOCH + timedelta(seconds=value)
    def encode(self, value: datetime) -> float: return value.astimezone(timezone.utc).timestamp()

class CodecJSON(Codec[str, JSONValue]):
    """Codec regarding the conversion between JSON-compatible strings and JSON objects."""

    def decode(self, value: str) -> JSONValue: return json.loads(value)
    def encode(self, value: JSONValue) -> str: return json.dumps(value)

class CodecTimedelta(Codec[float, timedelta]):
    """Codec regarding the conversion between floats and timedelta seconds."""

    def decode(self, value: float) -> timedelta: return timedelta(seconds=value)
    def encode(self, value: timedelta) -> float: return value.total_seconds()
