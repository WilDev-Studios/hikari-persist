from __future__ import annotations

from collections.abc import (
    AsyncGenerator,
    AsyncIterator,
    Callable,
    Generator,
    Hashable,
)
from dataclasses import dataclass
from itertools import count as i_count
from typing import (
    Any,
    cast,
    Generic,
    Protocol,
    TYPE_CHECKING,
    TypeVar,
)

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

__all__ = (
    "CacheIterator",
    "CacheIteratorStep",
)

T = TypeVar('T')
U = TypeVar('U')

class CacheIteratorStep(Protocol[T, U]):
    """
    Implement a custom iterator pipeline step.
    """

    def __call__(self, item: T) -> tuple[U, bool, bool]:
        """
        Return (value, skip, stop).

        ```
        stop = True, skip = True   -> Skip this value, then stop.
        stop = True, skip = False  -> Yield this value, then stop.
        stop = False, skip = True  -> Skip this value, continue.
        stop = False, skip = False -> Yield this value, continue.
        ```
        """

@dataclass(slots=True)
class _Filter(CacheIteratorStep[T, T]):
    fn: Callable[[T], bool]

    def __call__(self, item: T) -> tuple[T, bool, bool]:
        return item, not self.fn(item), False

@dataclass(slots=True)
class _Map(CacheIteratorStep[T, U]):
    fn: Callable[[T], U]

    def __call__(self, item: T) -> tuple[U, bool, bool]:
        return self.fn(item), False, False

@dataclass(slots=True)
class _TakeWhile(CacheIteratorStep[T, T]):
    fn: Callable[[T], bool]

    def __call__(self, item: T) -> tuple[T, bool, bool]:
        if not self.fn(item):
            return item, True, True

        return item, False, False

class CacheIterator(Generic[T]):
    """Asynchronous iterator for cached objects."""

    __slots__ = (
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

        Note
        ----
        The source iterator is shared across transformations created from this iterator.
        Multiple concurrent iterations are not supported.
        """

        self._source: AsyncIterator[T] = source
        self._pipeline: list[CacheIteratorStep[Any, Any]] = []

        self._limit: int | None = None

    def __aiter__(self) -> AsyncIterator[T]:
        return self.__iterate()

    def __await__(self) -> Generator[Any, None, list[T]]:
        return self.collect().__await__()

    async def __iterate(self) -> AsyncGenerator[T, None]:
        pipeline: tuple[CacheIteratorStep[Any, Any], ...] = tuple(self._pipeline)
        limit: int | None = self._limit

        yielded: int = 0

        async for item in self._source:
            if limit is not None and yielded >= limit:
                break

            value: Any = item
            skip: bool = False
            stop: bool = False

            for step in pipeline:
                value, skip, stop_step = step(value)

                if stop_step:
                    stop = True

                if skip:
                    break

            if not skip:
                yield value
                yielded = yielded + 1

            if stop:
                return

    def add_step(self, step: CacheIteratorStep[T, U]) -> CacheIterator[U]:
        """
        Add a custom-implemented CacheIteratorStep into the iterator's pipeline.

        Parameters
        ----------
        step : CacheIteratorStep[T, U]
            The iterator step to add.

        Returns
        -------
        CacheIterator[U]
            A chain-callable async iterator over the results.
        """

        self._pipeline.append(step)
        return self

    async def all(self, predicate: Callable[[T], bool]) -> bool:
        """
        Check if all items in the iterator satisfy a predicate.

        Parameters
        ----------
        predicate : Callable[[T], bool]
            The predicate to check each item against.

        Returns
        -------
        bool
            `True` if all items satisfy the predicate, `False` otherwise.
            Returns `True` if the iterator is empty.
        """

        async for item in self:
            if not predicate(item):
                return False

        return True

    async def any(self, predicate: Callable[[T], bool]) -> bool:
        """
        Check if any item in the iterator satifies a predicate.

        Parameters
        ----------
        predicate : Callable[[T], bool]
            The predicate to check each item against.

        Returns
        -------
        bool
            `True` if any item satisfies the predicate, `False` otherwise.
            Returns `False` if the iterator is empty.
        """

        async for item in self:
            if predicate(item):
                return True

        return False

    def chunk(self, size: int) -> CacheIterator[list[T]]:
        """
        Set the amount of results to be handled in each chunk.

        Parameters
        ----------
        size : int
            The amount of results.

        Returns
        -------
        CacheIterator[list[T]]
            A chain-callable async iterator over the results.
        """

        async def _chunk_source() -> AsyncGenerator[list[T], None]:
            bucket: list[T] = []

            async for item in self:
                bucket.append(item)

                if len(bucket) >= size:
                    yield bucket
                    bucket = []

            if bucket:
                yield bucket

        return CacheIterator(_chunk_source())

    async def collect(self) -> list[T]:
        """
        Collect all items in the iterator into a list.

        Returns
        -------
        list[T]
            All iterator items.
        """

        result: list[T] = []
        append: Callable[[T], None] = result.append

        async for item in self:
            append(item)

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
            total = total + 1

        return total

    def enumerate(self, start: int = 0) -> CacheIterator[tuple[int, T]]:
        """
        Enumerate each item, yielding a `(index, item)` tuple for each result.

        Parameters
        ----------
        start : int
            The starting index.

        Returns
        -------
        CacheIterator[tuple[int, T]]
            A chain-callable async iterator over the enumerated results.
        """

        counter: i_count = i_count(start)

        def _enumerate(item: T) -> tuple[int, T]:
            return next(counter), item

        return self.map(_enumerate)

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

        self._pipeline.append(_Filter(predicate))
        return self

    def flat_map(self, func: Callable[[T], AsyncIterator[U]]) -> CacheIterator[U]:
        """
        Map each item to an async iterator and flatten all results into a single iterator.

        Parameters
        ----------
        func : Callable[[T], AsyncIterator[U]]
            A method that takes each item and returns an async iterator of results.

        Returns
        -------
        CacheIterator[U]
            A chain-callable async iterator over the flatten results.
        """

        async def _flat_source() -> AsyncGenerator[U, None]:
            async for item in self:
                async for sub in func(item):
                    yield sub

        return CacheIterator(_flat_source())

    async def find(self, predicate: Callable[[T], bool]) -> T | None:
        """
        Find the first item in the iterator that passes the predicate.

        Parameters
        ----------
        predicate : Callable[[T], bool]
            The predicate method to check against each item.

        Returns
        -------
        T | None
            If passed, the first item.
        """

        async for item in self:
            if not predicate(item):
                continue

            return item

        return None

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

    async def last(self) -> T | None:
        """
        Get the last item in the iterator.

        Returns
        -------
        T | None
            If present, the last item.
        """

        result: T | None = None

        async for item in self:
            result = item

        return result

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

        self._limit = size
        return self

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

        self._pipeline.append(_Map(func))
        return cast(CacheIterator[U], self)

    async def max(self, *, key: Callable[[T], Any]) -> T | None:
        """
        Get the item with the highest key value.

        Parameters
        ----------
        key : Callable[[T], Any]
            A method used to extract a comparison key from each item.

        Returns
        -------
        T | None
            If present, the item with the highest key value.
        """

        result: T | None = None
        result_key: Any = None

        found: bool = False

        async for item in self:
            item_key: Any = key(item)

            if not found or item_key > result_key:
                result = item
                result_key = item_key
                found = True

        return result

    async def min(self, *, key: Callable[[T], Any]) -> T | None:
        """
        Get the item with the lowest key value.

        Parameters
        ----------
        key : Callable[[T], Any]
            A method used to extract a comparison key from each item.

        Returns
        -------
        T | None
            If present, the item with the lowest key value.
        """

        result: T | None = None
        result_key: Any = None

        found: bool = False

        async for item in self:
            item_key: Any = key(item)

            if not found or item_key < result_key:
                result = item
                result_key = item_key
                found = True

        return result

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

    def skip_while(self, predicate: Callable[[T], bool]) -> CacheIterator[T]:
        """
        Skip items while the predicate returns `True`, then yield all remaining items.

        Parameters
        ----------
        predicate : Callable[[T], bool]
            The predicate to check each item against.

        Returns
        -------
        CacheIterator[T]
            A chain-callable async iterator over the results.
        """

        async def _skip_source() -> AsyncGenerator[T, None]:
            skipping: bool = True

            async for item in self:
                if skipping:
                    if predicate(item):
                        continue

                    skipping = False

                yield item

        return CacheIterator(_skip_source())

    async def sort(
        self,
        *,
        key: Callable[[T], SupportsRichComparison] | None = None,
        reverse: bool = False,
    ) -> list[T]:
        """
        Collect all items (consuming them) and return them sorted.

        Parameters
        ----------
        key : Callable[[T], SupportsRichComparison] | None
            If provided, a method used to extract a comparison key from each item.
        reverse : bool
            If `True`, sorts in descending order.

        Returns
        -------
        list[T]
            All iterator items, sorted.
        """

        return sorted(await self.collect(), key=key, reverse=reverse)

    def take_while(self, predicate: Callable[[T], bool]) -> CacheIterator[T]:
        """
        Yield items while the predicate returns `True`, then stop.

        Parameters
        ----------
        predicate : Callable[[T], bool]
            The predicate to check each item against.

        Returns
        -------
        CacheIterator[T]
            A chain-callable async iterator over the results.
        """

        self._pipeline.append(_TakeWhile(predicate))
        return self

    def unique(self, *, key: Callable[[T], Hashable] | None = None) -> CacheIterator[T]:
        """
        Yield only unique items, discarding duplicates.

        Parameters
        ----------
        key : Callable[[T], Hashable] | None
            If provided, uniqueness is determined by the key value rather than the item itself.

        Returns
        -------
        CacheIterator[T]
            A chain-callable async iterator over the unique results.
        """

        async def _unique_source() -> AsyncGenerator[T, None]:
            seen: set[Hashable] = set()

            async for item in self:
                item_key: Hashable = cast(Hashable, item) if key is None else key(item)

                if item_key in seen:
                    continue

                seen.add(item_key)
                yield item

        return CacheIterator(_unique_source())

    def zip(self, other: CacheIterator[U] | AsyncIterator[U]) -> CacheIterator[tuple[T, U]]:
        """
        Pair each item with the corresponding item from another async iterator.
        Stops when either iterator is exhausted.

        Parameters
        ----------
        other : CacheIterator[U] | AsyncIterator[U]
            The async iterator to zip with.

        Returns
        -------
        CacheIterator[tuple[T, U]]
            A chain-callable async iterator over the paired results.
        """

        async def _zip_source() -> AsyncGenerator[tuple[T, U], None]:
            other_iter: AsyncIterator[U] = aiter(other)

            async for item in self:
                try:
                    other_item: U = await anext(other_iter)
                except StopAsyncIteration:
                    break

                yield item, other_item

        return CacheIterator(_zip_source())
