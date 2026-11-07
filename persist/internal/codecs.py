from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from datetime import (
    UTC,
    datetime,
    timedelta,
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

class Codec(ABC, Generic[T, U]):
    @abstractmethod
    def decode(self, value: T) -> U: raise NotImplementedError
    @abstractmethod
    def encode(self, value: U) -> T: raise NotImplementedError

class CodecBoolean(Codec[int, bool]):
    def decode(self, value: int) -> bool: return bool(value)
    def encode(self, value: bool) -> int: return int(value)

class CodecDatetime(Codec[float, datetime]):
    _EPOCH: datetime = datetime(1970, 1, 1, tzinfo=UTC)
    def decode(self, value: float) -> datetime: return self._EPOCH + timedelta(seconds=value)
    def encode(self, value: datetime) -> float: return value.astimezone(UTC).timestamp()

class CodecJSON(Codec[str, JSONValue]):
    def decode(self, value: str) -> JSONValue: return json.loads(value)
    def encode(self, value: JSONValue) -> str: return json.dumps(value)

class CodecTimedelta(Codec[float, timedelta]):
    def decode(self, value: float) -> timedelta: return timedelta(seconds=value)
    def encode(self, value: timedelta) -> float: return value.total_seconds()
