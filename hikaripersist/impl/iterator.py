from __future__ import annotations

from collections.abc import (
    AsyncIterator,
    Callable,
)
from typing import (
    Any,
    cast,
    Generic,
    Literal,
    TypeVar,
)

__all__ = ("CacheIterator",)

T = TypeVar('T')
U = TypeVar('U')

class CacheIterator(Generic[T]):
    """Asynchronous iterator for cached objects."""

    __slots__ = (
        "_batch_size",
        "_limit",
        "_pipeline",
        "_source",
    )

    def __init__(self, source: AsyncIterator[T]) -> None:
        """
        Create a new cache iterator from an async iterator.

        Parameters
        ----------
        source : AsyncIterator[T]
            The source iterator.
        """

        self._source: AsyncIterator[T] = source

        self._pipeline: list[tuple[Literal["filter", "map"], Callable[[Any], Any]]] = []

        self._limit: int | None = None
        self._batch_size: int | None = None

    def __aiter__(self) -> AsyncIterator[Any]:
        return self.__iterate()

    def __clone(self) -> CacheIterator[T]:
        new: CacheIterator[T] = CacheIterator(self._source)
        new._pipeline = self._pipeline.copy()
        new._limit = self._limit
        new._batch_size = self._batch_size
        return new

    async def __iterate(self) -> AsyncIterator[Any]:
        yielded: int = 0
        batch: list[T] = []

        async for item in self._source:
            value: Any = item
            skip: bool = False

            for kind, func in self._pipeline:
                if kind == "filter":
                    if not func(value):
                        skip = True
                        break
                else:
                    value = func(value)

            if skip:
                continue

            if self._batch_size:
                batch.append(value)

                if len(batch) >= self._batch_size:
                    yield batch

                    yielded += 1
                    batch = []
            else:
                yield value
                yielded += 1

            if self._limit is not None and yielded >= self._limit:
                break

        if self._batch_size and batch and (self._limit is None or yielded < self._limit):
            yield batch

    def batch(self, size: int) -> CacheIterator[list[T]]:
        """
        Set the amount of results to be handled at once.

        Parameters
        ----------
        size : int
            The amount of results.

        Returns
        -------
        CacheIterator[list[T]]
            A chain-callable async iterator over the results.
        """

        new: CacheIterator[T] = self.__clone()
        new._batch_size = size
        return cast(CacheIterator[list[T]], new)

    async def collect(self) -> list[T]:
        """
        Collect all items in the iterator into a list.

        Returns
        -------
        list[T]
            All iterator items.
        """

        result: list[T] = []

        async for item in self:
            result.append(item)

        return result

    async def count(self) -> int:
        """
        Get the total amount of items in the iterator.

        Returns
        -------
        int
            The amount of items.
        """

        total: int = 0

        async for _ in self:
            total += 1

        return total

    def filter(self, predicate: Callable[[T], bool]) -> CacheIterator[T]:
        """
        Filter through each item in the iterator and check it against a predicate.

        Parameters
        ----------
        predicate : Callable[[T], bool]
            The predicate method to check against each item.
            If `True`, adds the item to the iterator chain.
            If `False`, discards it from the iterator chain.

        Returns
        -------
        CacheIterator[T]
            A chain-callable async iterator over the results.
        """

        new: CacheIterator[T] = self.__clone()
        new._pipeline.append(("filter", predicate))
        return new

    async def first(self) -> T | None:
        """
        Get the first item in the iterator.

        Returns
        -------
        T | None
            If present, the first item.
        """

        async for item in self:
            return item

        return None

    def limit(self, size: int) -> CacheIterator[T]:
        """
        Limit the size of the iterator.

        Parameters
        ----------
        size : int
            The size limit of the iterator.

        Returns
        -------
        CacheIterator[T]
            A chain-callable async iterator over the results.
        """

        new: CacheIterator[T] = self.__clone()
        new._limit = size
        return new

    def map(self, func: Callable[[T], U]) -> CacheIterator[U]:
        """
        Map each iterator item through a mapping method.

        Parameters
        ----------
        func : Callable[[T], U]
            The mapping method.

        Returns
        -------
        CacheIterator[U]
            A chain-callable async iterator over the results.
        """

        new: CacheIterator[T] = self.__clone()
        new._pipeline.append(("map", func))
        return cast(CacheIterator[U], new)

    async def reduce(self, func: Callable[[U, T], U], initial: U) -> U:
        """
        Aggregate all iterator items into one value using a reducing method.

        Parameters
        ----------
        func : Callable[[U, T], U]
            The reducing method.
        initial : U
            The initial value.

        Returns
        -------
        U
            The reduced iterator items.
        """

        result: U = initial

        async for item in self:
            result = func(result, item)

        return result
