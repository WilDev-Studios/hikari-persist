from __future__ import annotations

from collections.abc import AsyncGenerator
from hikaripersist.impl.iterator import CacheIterator
from typing import Any

import pytest

pytest_plugins = ("pytest_asyncio",)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _source(*items: Any) -> AsyncGenerator[Any, None]:
    """Yield items one by one as an async generator."""
    for item in items:
        yield item


async def _empty() -> AsyncGenerator[Any, None]:
    """An empty async generator."""
    return
    yield  # makes it an async generator


def make(
    *items: Any,
) -> CacheIterator[Any]:
    """Shorthand to build a CacheIterator from positional items."""
    return CacheIterator(_source(*items))


def empty() -> CacheIterator[Any]:
    """Shorthand to build an empty CacheIterator."""
    return CacheIterator(_empty())


# ---------------------------------------------------------------------------
# __aiter__ / basic iteration
# ---------------------------------------------------------------------------

class TestIteration:
    @pytest.mark.asyncio
    async def test_iterates_all_items(self) -> None:
        result = []
        async for item in make(1, 2, 3):
            result.append(item)
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_empty_iterator(self) -> None:
        result = []
        async for item in empty():
            result.append(item)
        assert result == []

    @pytest.mark.asyncio
    async def test_single_item(self) -> None:
        result = []
        async for item in make(42):
            result.append(item)
        assert result == [42]


# ---------------------------------------------------------------------------
# __await__
# ---------------------------------------------------------------------------

class TestAwait:
    @pytest.mark.asyncio
    async def test_await_returns_list(self) -> None:
        result = await make(1, 2, 3)
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_await_empty(self) -> None:
        result = await empty()
        assert result == []

    @pytest.mark.asyncio
    async def test_await_equivalent_to_collect(self) -> None:
        items = [1, 2, 3, 4, 5]
        a = await CacheIterator(_source(*items))
        b = await CacheIterator(_source(*items)).collect()
        assert a == b


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

class TestCollect:
    @pytest.mark.asyncio
    async def test_collect_all(self) -> None:
        assert await make(1, 2, 3).collect() == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_collect_empty(self) -> None:
        assert await empty().collect() == []

    @pytest.mark.asyncio
    async def test_collect_preserves_order(self) -> None:
        assert await make(3, 1, 2).collect() == [3, 1, 2]


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------

class TestCount:
    @pytest.mark.asyncio
    async def test_count(self) -> None:
        assert await make(1, 2, 3).count() == 3

    @pytest.mark.asyncio
    async def test_count_empty(self) -> None:
        assert await empty().count() == 0

    @pytest.mark.asyncio
    async def test_count_respects_filter(self) -> None:
        assert await make(1, 2, 3, 4).filter(lambda x: x % 2 == 0).count() == 2

    @pytest.mark.asyncio
    async def test_count_respects_limit(self) -> None:
        assert await make(1, 2, 3, 4, 5).limit(3).count() == 3


# ---------------------------------------------------------------------------
# first / last
# ---------------------------------------------------------------------------

class TestFirstLast:
    @pytest.mark.asyncio
    async def test_first(self) -> None:
        assert await make(10, 20, 30).first() == 10

    @pytest.mark.asyncio
    async def test_first_empty(self) -> None:
        assert await empty().first() is None

    @pytest.mark.asyncio
    async def test_last(self) -> None:
        assert await make(10, 20, 30).last() == 30

    @pytest.mark.asyncio
    async def test_last_empty(self) -> None:
        assert await empty().last() is None

    @pytest.mark.asyncio
    async def test_first_single(self) -> None:
        assert await make(99).first() == 99

    @pytest.mark.asyncio
    async def test_last_single(self) -> None:
        assert await make(99).last() == 99

    @pytest.mark.asyncio
    async def test_first_does_not_consume_all(self) -> None:
        consumed = []

        async def _tracked() -> AsyncGenerator[int, None]:
            for i in range(5):
                consumed.append(i)
                yield i

        await CacheIterator(_tracked()).first()
        # Should stop after first item
        assert consumed == [0]


# ---------------------------------------------------------------------------
# filter
# ---------------------------------------------------------------------------

class TestFilter:
    @pytest.mark.asyncio
    async def test_filter_evens(self) -> None:
        result = await make(1, 2, 3, 4, 5).filter(lambda x: x % 2 == 0).collect()
        assert result == [2, 4]

    @pytest.mark.asyncio
    async def test_filter_none_match(self) -> None:
        result = await make(1, 3, 5).filter(lambda x: x % 2 == 0).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_filter_all_match(self) -> None:
        result = await make(2, 4, 6).filter(lambda x: x % 2 == 0).collect()
        assert result == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_filter_empty(self) -> None:
        result = await empty().filter(lambda x: True).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_filter_chained(self) -> None:
        result = (
            await make(1, 2, 3, 4, 5, 6)
            .filter(lambda x: x % 2 == 0)
            .filter(lambda x: x > 2)
            .collect()
        )
        assert result == [4, 6]

    @pytest.mark.asyncio
    async def test_filter_is_immutable(self) -> None:
        base = make(1, 2, 3, 4)
        evens = base.filter(lambda x: x % 2 == 0)
        odds = base.filter(lambda x: x % 2 != 0)
        # Both should work independently — but note shared source means
        # only one can be iterated; this tests that filter() doesn't mutate base
        assert evens._pipeline != base._pipeline
        assert odds._pipeline != base._pipeline
        assert evens._pipeline != odds._pipeline


# ---------------------------------------------------------------------------
# map
# ---------------------------------------------------------------------------

class TestMap:
    @pytest.mark.asyncio
    async def test_map_doubles(self) -> None:
        result = await make(1, 2, 3).map(lambda x: x * 2).collect()
        assert result == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_map_type_change(self) -> None:
        result = await make(1, 2, 3).map(str).collect()
        assert result == ["1", "2", "3"]

    @pytest.mark.asyncio
    async def test_map_empty(self) -> None:
        result = await empty().map(lambda x: x * 2).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_map_chained(self) -> None:
        result = await make(1, 2, 3).map(lambda x: x * 2).map(lambda x: x + 1).collect()
        assert result == [3, 5, 7]

    @pytest.mark.asyncio
    async def test_filter_then_map_ordering(self) -> None:
        # filter runs on original value, map runs after — ordering matters
        result = (
            await make(1, 2, 3, 4)
            .filter(lambda x: x % 2 == 0)
            .map(lambda x: x * 10)
            .collect()
        )
        assert result == [20, 40]

    @pytest.mark.asyncio
    async def test_map_then_filter_ordering(self) -> None:
        # map first, then filter on mapped value
        result = (
            await make(1, 2, 3, 4)
            .map(lambda x: x * 10)
            .filter(lambda x: x > 20)
            .collect()
        )
        assert result == [30, 40]


# ---------------------------------------------------------------------------
# limit
# ---------------------------------------------------------------------------

class TestLimit:
    @pytest.mark.asyncio
    async def test_limit(self) -> None:
        result = await make(1, 2, 3, 4, 5).limit(3).collect()
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_limit_larger_than_source(self) -> None:
        result = await make(1, 2, 3).limit(10).collect()
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_limit_zero(self) -> None:
        result = await make(1, 2, 3).limit(0).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_limit_one(self) -> None:
        result = await make(1, 2, 3).limit(1).collect()
        assert result == [1]

    @pytest.mark.asyncio
    async def test_limit_empty(self) -> None:
        result = await empty().limit(5).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_limit_after_filter(self) -> None:
        # limit applies to items that pass the filter
        result = await make(1, 2, 3, 4, 5, 6).filter(lambda x: x % 2 == 0).limit(2).collect()
        assert result == [2, 4]

    @pytest.mark.asyncio
    async def test_limit_is_immutable(self) -> None:
        base = make(1, 2, 3, 4, 5)
        limited = base.limit(2)
        assert base._limit is None
        assert limited._limit == 2


# ---------------------------------------------------------------------------
# chunk
# ---------------------------------------------------------------------------

class TestChunk:
    @pytest.mark.asyncio
    async def test_chunk_even(self) -> None:
        result = await make(1, 2, 3, 4).chunk(2).collect()
        assert result == [[1, 2], [3, 4]]

    @pytest.mark.asyncio
    async def test_chunk_with_remainder(self) -> None:
        result = await make(1, 2, 3, 4, 5).chunk(2).collect()
        assert result == [[1, 2], [3, 4], [5]]

    @pytest.mark.asyncio
    async def test_chunk_larger_than_source(self) -> None:
        result = await make(1, 2, 3).chunk(10).collect()
        assert result == [[1, 2, 3]]

    @pytest.mark.asyncio
    async def test_chunk_size_one(self) -> None:
        result = await make(1, 2, 3).chunk(1).collect()
        assert result == [[1], [2], [3]]

    @pytest.mark.asyncio
    async def test_chunk_empty(self) -> None:
        result = await empty().chunk(3).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_chunk_independent_of_limit(self) -> None:
        # limit should apply to items, not chunks
        result = await make(1, 2, 3, 4, 5).limit(4).chunk(2).collect()
        assert result == [[1, 2], [3, 4]]

    @pytest.mark.asyncio
    async def test_chunk_after_filter(self) -> None:
        result = await make(1, 2, 3, 4, 5, 6).filter(lambda x: x % 2 == 0).chunk(2).collect()
        assert result == [[2, 4], [6]]


# ---------------------------------------------------------------------------
# enumerate
# ---------------------------------------------------------------------------

class TestEnumerate:
    @pytest.mark.asyncio
    async def test_enumerate_default_start(self) -> None:
        result = await make("a", "b", "c").enumerate().collect()
        assert result == [(0, "a"), (1, "b"), (2, "c")]

    @pytest.mark.asyncio
    async def test_enumerate_custom_start(self) -> None:
        result = await make("a", "b", "c").enumerate(start=5).collect()
        assert result == [(5, "a"), (6, "b"), (7, "c")]

    @pytest.mark.asyncio
    async def test_enumerate_empty(self) -> None:
        result = await empty().enumerate().collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_enumerate_after_filter(self) -> None:
        result = await make(1, 2, 3, 4).filter(lambda x: x % 2 == 0).enumerate().collect()
        assert result == [(0, 2), (1, 4)]


# ---------------------------------------------------------------------------
# any / all
# ---------------------------------------------------------------------------

class TestAnyAll:
    @pytest.mark.asyncio
    async def test_any_true(self) -> None:
        assert await make(1, 2, 3).any(lambda x: x == 2) is True

    @pytest.mark.asyncio
    async def test_any_false(self) -> None:
        assert await make(1, 2, 3).any(lambda x: x == 99) is False

    @pytest.mark.asyncio
    async def test_any_empty(self) -> None:
        assert await empty().any(lambda x: True) is False

    @pytest.mark.asyncio
    async def test_any_short_circuits(self) -> None:
        consumed = []

        async def _tracked() -> AsyncGenerator[int, None]:
            for i in range(5):
                consumed.append(i)
                yield i

        await CacheIterator(_tracked()).any(lambda x: x == 2)
        assert consumed == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_all_true(self) -> None:
        assert await make(2, 4, 6).all(lambda x: x % 2 == 0) is True

    @pytest.mark.asyncio
    async def test_all_false(self) -> None:
        assert await make(2, 3, 6).all(lambda x: x % 2 == 0) is False

    @pytest.mark.asyncio
    async def test_all_empty(self) -> None:
        assert await empty().all(lambda x: False) is True

    @pytest.mark.asyncio
    async def test_all_short_circuits(self) -> None:
        consumed = []

        async def _tracked() -> AsyncGenerator[int, None]:
            for i in range(5):
                consumed.append(i)
                yield i

        await CacheIterator(_tracked()).all(lambda x: x < 2)
        assert consumed == [0, 1, 2]


# ---------------------------------------------------------------------------
# min / max
# ---------------------------------------------------------------------------

class TestMinMax:
    @pytest.mark.asyncio
    async def test_max(self) -> None:
        assert await make(3, 1, 4, 1, 5, 9).max(key=lambda x: x) == 9

    @pytest.mark.asyncio
    async def test_max_empty(self) -> None:
        assert await empty().max(key=lambda x: x) is None

    @pytest.mark.asyncio
    async def test_max_single(self) -> None:
        assert await make(42).max(key=lambda x: x) == 42

    @pytest.mark.asyncio
    async def test_max_by_key(self) -> None:
        items = [{"name": "a", "score": 5}, {"name": "b", "score": 10}, {"name": "c", "score": 3}]
        result = await make(*items).max(key=lambda x: x["score"])
        assert result == {"name": "b", "score": 10}

    @pytest.mark.asyncio
    async def test_min(self) -> None:
        assert await make(3, 1, 4, 1, 5, 9).min(key=lambda x: x) == 1

    @pytest.mark.asyncio
    async def test_min_empty(self) -> None:
        assert await empty().min(key=lambda x: x) is None

    @pytest.mark.asyncio
    async def test_min_single(self) -> None:
        assert await make(42).min(key=lambda x: x) == 42

    @pytest.mark.asyncio
    async def test_min_by_key(self) -> None:
        items = [{"name": "a", "score": 5}, {"name": "b", "score": 10}, {"name": "c", "score": 3}]
        result = await make(*items).min(key=lambda x: x["score"])
        assert result == {"name": "c", "score": 3}


# ---------------------------------------------------------------------------
# reduce
# ---------------------------------------------------------------------------

class TestReduce:
    @pytest.mark.asyncio
    async def test_reduce_sum(self) -> None:
        result = await make(1, 2, 3, 4).reduce(lambda acc, x: acc + x, 0)
        assert result == 10

    @pytest.mark.asyncio
    async def test_reduce_product(self) -> None:
        result = await make(1, 2, 3, 4).reduce(lambda acc, x: acc * x, 1)
        assert result == 24

    @pytest.mark.asyncio
    async def test_reduce_empty_returns_initial(self) -> None:
        result = await empty().reduce(lambda acc, x: acc + x, 99)
        assert result == 99

    @pytest.mark.asyncio
    async def test_reduce_string_concat(self) -> None:
        result = await make("a", "b", "c").reduce(lambda acc, x: acc + x, "")
        assert result == "abc"


# ---------------------------------------------------------------------------
# sort
# ---------------------------------------------------------------------------

class TestSort:
    @pytest.mark.asyncio
    async def test_sort_ascending(self) -> None:
        result = await make(3, 1, 4, 1, 5, 9).sort()
        assert result == [1, 1, 3, 4, 5, 9]

    @pytest.mark.asyncio
    async def test_sort_descending(self) -> None:
        result = await make(3, 1, 4, 1, 5, 9).sort(reverse=True)
        assert result == [9, 5, 4, 3, 1, 1]

    @pytest.mark.asyncio
    async def test_sort_by_key(self) -> None:
        items = [{"v": 3}, {"v": 1}, {"v": 2}]
        result = await make(*items).sort(key=lambda x: x["v"])
        assert result == [{"v": 1}, {"v": 2}, {"v": 3}]

    @pytest.mark.asyncio
    async def test_sort_empty(self) -> None:
        result = await empty().sort()
        assert result == []

    @pytest.mark.asyncio
    async def test_sort_returns_list(self) -> None:
        result = await make(3, 1, 2).sort()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_sort_slice_pattern(self) -> None:
        # Idiomatic usage: sort then slice
        result = (await make(5, 3, 1, 4, 2).sort())[:3]
        assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# take_while / skip_while
# ---------------------------------------------------------------------------

class TestTakeSkipWhile:
    @pytest.mark.asyncio
    async def test_take_while(self) -> None:
        result = await make(1, 2, 3, 4, 5).take_while(lambda x: x < 4).collect()
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_take_while_none_match(self) -> None:
        result = await make(5, 6, 7).take_while(lambda x: x < 3).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_take_while_all_match(self) -> None:
        result = await make(1, 2, 3).take_while(lambda x: x < 10).collect()
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_take_while_empty(self) -> None:
        result = await empty().take_while(lambda x: True).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_take_while_stops_on_first_fail(self) -> None:
        # Should not resume yielding after predicate fails once
        result = await make(1, 2, 5, 3, 4).take_while(lambda x: x < 4).collect()
        assert result == [1, 2]

    @pytest.mark.asyncio
    async def test_skip_while(self) -> None:
        result = await make(1, 2, 3, 4, 5).skip_while(lambda x: x < 3).collect()
        assert result == [3, 4, 5]

    @pytest.mark.asyncio
    async def test_skip_while_none_match(self) -> None:
        result = await make(5, 6, 7).skip_while(lambda x: x < 3).collect()
        assert result == [5, 6, 7]

    @pytest.mark.asyncio
    async def test_skip_while_all_match(self) -> None:
        result = await make(1, 2, 3).skip_while(lambda x: x < 10).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_skip_while_empty(self) -> None:
        result = await empty().skip_while(lambda x: True).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_skip_while_resumes_after_first_fail(self) -> None:
        # Items after the first failing item should all be yielded
        result = await make(1, 2, 5, 1, 2).skip_while(lambda x: x < 4).collect()
        assert result == [5, 1, 2]


# ---------------------------------------------------------------------------
# flat_map
# ---------------------------------------------------------------------------

class TestFlatMap:
    @pytest.mark.asyncio
    async def test_flat_map(self) -> None:
        result = await make(1, 2, 3).flat_map(lambda x: _source(x, x * 10)).collect()
        assert result == [1, 10, 2, 20, 3, 30]

    @pytest.mark.asyncio
    async def test_flat_map_empty_outer(self) -> None:
        result = await empty().flat_map(lambda x: _source(x)).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_flat_map_empty_inner(self) -> None:
        result = await make(1, 2, 3).flat_map(lambda x: _empty()).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_flat_map_with_cache_iterator(self) -> None:
        async def _inner(x: int) -> AsyncGenerator[int, None]:
            for i in range(x):
                yield i

        result = await make(1, 2, 3).flat_map(_inner).collect()
        assert result == [0, 0, 1, 0, 1, 2]


# ---------------------------------------------------------------------------
# unique
# ---------------------------------------------------------------------------

class TestUnique:
    @pytest.mark.asyncio
    async def test_unique(self) -> None:
        result = await make(1, 2, 2, 3, 1, 4).unique().collect()
        assert result == [1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_unique_empty(self) -> None:
        result = await empty().unique().collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_unique_no_duplicates(self) -> None:
        result = await make(1, 2, 3).unique().collect()
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_unique_all_same(self) -> None:
        result = await make(5, 5, 5).unique().collect()
        assert result == [5]

    @pytest.mark.asyncio
    async def test_unique_by_key(self) -> None:
        items = [
            {"id": 1, "name": "a"},
            {"id": 2, "name": "b"},
            {"id": 1, "name": "c"},
        ]
        result = await make(*items).unique(key=lambda x: x["id"]).collect()
        assert result == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]

    @pytest.mark.asyncio
    async def test_unique_preserves_first_occurrence(self) -> None:
        result = await make(3, 1, 2, 1, 3).unique().collect()
        assert result == [3, 1, 2]


# ---------------------------------------------------------------------------
# zip
# ---------------------------------------------------------------------------

class TestZip:
    @pytest.mark.asyncio
    async def test_zip(self) -> None:
        result = await make(1, 2, 3).zip(_source("a", "b", "c")).collect()
        assert result == [(1, "a"), (2, "b"), (3, "c")]

    @pytest.mark.asyncio
    async def test_zip_left_shorter(self) -> None:
        result = await make(1, 2).zip(_source("a", "b", "c")).collect()
        assert result == [(1, "a"), (2, "b")]

    @pytest.mark.asyncio
    async def test_zip_right_shorter(self) -> None:
        result = await make(1, 2, 3).zip(_source("a", "b")).collect()
        assert result == [(1, "a"), (2, "b")]

    @pytest.mark.asyncio
    async def test_zip_empty_left(self) -> None:
        result = await empty().zip(_source(1, 2, 3)).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_zip_empty_right(self) -> None:
        result = await make(1, 2, 3).zip(_empty()).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_zip_both_empty(self) -> None:
        result = await empty().zip(_empty()).collect()
        assert result == []

    @pytest.mark.asyncio
    async def test_zip_with_cache_iterator(self) -> None:
        result = await make(1, 2, 3).zip(make("a", "b", "c")).collect()
        assert result == [(1, "a"), (2, "b"), (3, "c")]


# ---------------------------------------------------------------------------
# Chaining combinations
# ---------------------------------------------------------------------------

class TestChaining:
    @pytest.mark.asyncio
    async def test_filter_map_limit(self) -> None:
        result = (
            await make(1, 2, 3, 4, 5, 6, 7, 8)
            .filter(lambda x: x % 2 == 0)
            .map(lambda x: x * 10)
            .limit(3)
            .collect()
        )
        assert result == [20, 40, 60]

    @pytest.mark.asyncio
    async def test_map_filter_enumerate(self) -> None:
        result = (
            await make(1, 2, 3, 4, 5)
            .map(lambda x: x * 2)
            .filter(lambda x: x > 4)
            .enumerate()
            .collect()
        )
        assert result == [(0, 6), (1, 8), (2, 10)]

    @pytest.mark.asyncio
    async def test_limit_then_chunk(self) -> None:
        result = await make(1, 2, 3, 4, 5).limit(4).chunk(2).collect()
        assert result == [[1, 2], [3, 4]]

    @pytest.mark.asyncio
    async def test_filter_skip_while(self) -> None:
        result = (
            await make(1, 2, 3, 4, 5, 6)
            .filter(lambda x: x % 2 == 0)
            .skip_while(lambda x: x < 4)
            .collect()
        )
        assert result == [4, 6]

    @pytest.mark.asyncio
    async def test_take_while_map(self) -> None:
        result = (
            await make(1, 2, 3, 10, 4)
            .take_while(lambda x: x < 5)
            .map(lambda x: x ** 2)
            .collect()
        )
        assert result == [1, 4, 9]

    @pytest.mark.asyncio
    async def test_flat_map_filter_limit(self) -> None:
        result = (
            await make(1, 2, 3)
            .flat_map(lambda x: _source(x, x * 10))
            .filter(lambda x: x > 5)
            .limit(3)
            .collect()
        )
        assert result == [10, 20, 30]

    @pytest.mark.asyncio
    async def test_unique_then_sort(self) -> None:
        result = await make(3, 1, 2, 1, 3, 2).unique().sort()
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_long_chain(self) -> None:
        result = (
            await make(*range(20))
            .filter(lambda x: x % 2 == 0)   # 0,2,4,6,8,10,12,14,16,18
            .map(lambda x: x + 1)            # 1,3,5,7,9,11,13,15,17,19
            .filter(lambda x: x < 15)        # 1,3,5,7,9,11,13
            .limit(5)                         # 1,3,5,7,9
            .collect()
        )
        assert result == [1, 3, 5, 7, 9]

    @pytest.mark.asyncio
    async def test_await_shorthand_in_chain(self) -> None:
        result = await make(1, 2, 3, 4).filter(lambda x: x > 2)
        assert result == [3, 4]

    @pytest.mark.asyncio
    async def test_any_after_map(self) -> None:
        assert await make(1, 2, 3).map(lambda x: x * 10).any(lambda x: x == 20) is True

    @pytest.mark.asyncio
    async def test_all_after_filter(self) -> None:
        assert await make(1, 2, 3, 4).filter(lambda x: x % 2 == 0).all(lambda x: x % 2 == 0) is True

    @pytest.mark.asyncio
    async def test_min_after_map(self) -> None:
        result = await make(3, 1, 2).map(lambda x: x * 10).min(key=lambda x: x)
        assert result == 10

    @pytest.mark.asyncio
    async def test_max_after_filter(self) -> None:
        result = await make(1, 2, 3, 4, 5).filter(lambda x: x % 2 == 0).max(key=lambda x: x)
        assert result == 4
