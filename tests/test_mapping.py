from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from persist.internal.codecs import CodecTimedelta
from persist.internal.definitions import DataType, Field, Table
from persist.internal.mapping import RowMapper, decode_row
from persist.internal.serializers import Attr, SerializerObject


# ------------------------------------------------------------- decode_row

class TestDecodeRow:
    def test_basic_decode(self, widgets_table):
        row = (1, "Widget A", 1, 1704067200.0, None)
        result = decode_row(widgets_table.fields, row)

        assert result == {
            "id": 1,
            "name": "Widget A",
            "is_enabled": True,
            "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "metadata": None,
        }

    def test_none_values_preserved_as_none_not_falsy_decoded_value(self, widgets_table):
        # regression guard: None must not become False/0/etc. via the codec
        row = (1, None, None, None, None)
        result = decode_row(widgets_table.fields, row)

        assert result["name"] is None
        assert result["is_enabled"] is None  # NOT False
        assert result["created_at"] is None
        assert result["metadata"] is None

    def test_falsy_but_non_none_boolean_survives(self, widgets_table):
        row = (1, "x", 0, 1704067200.0, None)
        result = decode_row(widgets_table.fields, row)
        assert result["is_enabled"] is False  # decoded, not skipped

    def test_json_field_decodes_string_to_python_value(self, widgets_table):
        row = (1, "x", 1, 1704067200.0, '{"a": 1, "b": [2, 3]}')
        result = decode_row(widgets_table.fields, row)
        assert result["metadata"] == {"a": 1, "b": [2, 3]}

    def test_field_with_no_default_codec_and_no_serializer_passes_through(self):
        # e.g. STRING has no DEFAULT_CODECS entry and no serializer set
        fields = (Field("name", DataType.STRING),)
        result = decode_row(fields, ("raw string",))
        assert result == {"name": "raw string"}

    def test_field_with_explicit_serializer_and_no_default_codec(self, widgets_table_with_status, status_enum): # noqa: E501
        row = (1, 2)
        result = decode_row(widgets_table_with_status.fields, row)
        assert result == {"id": 1, "status": status_enum.INACTIVE}

    def test_mismatched_row_length_raises(self, widgets_table):
        # strict=True zip: a partial SELECT against full Table.fields must fail
        # loudly instead of silently misaligning columns
        short_row = (1, "Widget A")  # missing 3 columns
        with pytest.raises(ValueError):
            decode_row(widgets_table.fields, short_row)

    def test_too_many_row_values_raises(self, widgets_table):
        long_row = (1, "Widget A", 1, 1704067200.0, None, "extra")
        with pytest.raises(ValueError):
            decode_row(widgets_table.fields, long_row)

    def test_empty_fields_and_row(self):
        assert decode_row((), ()) == {}

    def test_field_order_maps_positionally_not_by_name(self):
        # decode_row trusts row-order == fields-order; verify it doesn't
        # accidentally rely on anything else (e.g. sorting by name)
        fields = (
            Field("b", DataType.STRING),
            Field("a", DataType.STRING),
        )
        result = decode_row(fields, ("second-col-value", "first-col-value"))
        assert result == {"b": "second-col-value", "a": "first-col-value"}


# ------------------------------------------------------------- RowMapper

class TestRowMapperConstruction:
    def test_defaults_to_all_table_fields(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: widget_factory(**k))
        assert mapper.fields == widgets_table.fields
        assert mapper.table is widgets_table

    def test_custom_field_subset(self, widgets_table, widget_factory):
        subset = (widgets_table.fields[0], widgets_table.fields[1])  # id, name
        mapper = RowMapper(widgets_table, factory=lambda k: k, fields=subset)
        assert mapper.fields == subset
        assert mapper.names == ("id", "name")

    def test_default_extract_uses_getattr(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: k)
        w = widget_factory(1, "x", True, None, None)
        assert mapper.extract(w, "name") == "x"

    def test_default_extract_missing_attr_returns_none(self, widgets_table):
        mapper = RowMapper(widgets_table, factory=lambda k: k)

        class Empty:
            pass

        assert mapper.extract(Empty(), "name") is None

    def test_custom_extract_overrides_default(self, widgets_table):
        calls = []

        def custom_extract(obj, name):
            calls.append(name)
            return obj.get(name)

        mapper = RowMapper(widgets_table, factory=lambda k: k, extract=custom_extract)
        mapper.to_row({"id": 1, "name": "x", "is_enabled": True, "created_at": None, "metadata": None}) # noqa: E501

        assert calls == ["id", "name", "is_enabled", "created_at", "metadata"]

    def test_names_property_reflects_field_subset(self, widgets_table):
        subset = tuple(f for f in widgets_table.fields if f.name != "metadata")
        mapper = RowMapper(widgets_table, factory=lambda k: k, fields=subset)
        assert "metadata" not in mapper.names
        assert mapper.names == ("id", "name", "is_enabled", "created_at")


class TestRowMapperToRow:
    def test_full_width_encode(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: widget_factory(**k))
        w = widget_factory(
            id=1, name="Widget A", is_enabled=True,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            metadata={"tag": "x"},
        )
        row = mapper.to_row(w)

        assert row == (1, "Widget A", 1, pytest.approx(1704067200.0), '{"tag": "x"}')

    def test_none_fields_encode_to_none(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: widget_factory(**k))
        w = widget_factory(id=1, name=None, is_enabled=None, created_at=None, metadata=None)
        row = mapper.to_row(w)

        assert row == (1, None, None, None, None)

    def test_falsy_boolean_encodes_correctly_not_as_none(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: widget_factory(**k))
        w = widget_factory(id=1, name="x", is_enabled=False, created_at=None, metadata=None)
        row = mapper.to_row(w)

        idx = mapper.names.index("is_enabled")
        assert row[idx] == 0  # not None

    def test_field_subset_produces_matching_tuple_length(self, widgets_table, widget_factory):
        subset = tuple(f for f in widgets_table.fields if f.name in ("id", "name"))
        mapper = RowMapper(widgets_table, factory=lambda k: k, fields=subset)
        w = widget_factory(id=1, name="x", is_enabled=True, created_at=None, metadata=None)

        row = mapper.to_row(w)
        assert row == (1, "x")

    def test_row_order_matches_names_order(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: k)
        w = widget_factory(id=42, name="ordered", is_enabled=True, created_at=None, metadata=None)
        row = mapper.to_row(w)

        for name, value in zip(mapper.names, row, strict=True):
            assert getattr(w, name) is not None or value is None  # sanity: positional alignment holds # noqa: E501

        assert dict(zip(mapper.names, row, strict=True))["name"] == "ordered"


class TestRowMapperFromRow:
    def test_full_width_decode_calls_factory_with_kwargs(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: widget_factory(**k))
        row = (1, "Widget A", 1, 1704067200.0, None)

        result = mapper.from_row(row)
        assert result == widget_factory(
            id=1, name="Widget A", is_enabled=True,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc), metadata=None,
        )

    def test_factory_receives_exactly_decode_row_output(self, widgets_table):
        received = {}

        def capturing_factory(kwargs):
            received.update(kwargs)
            return kwargs

        mapper = RowMapper(widgets_table, factory=capturing_factory)
        row = (1, "x", 1, 1704067200.0, '{"a": 1}')
        mapper.from_row(row)

        assert received == {
            "id": 1, "name": "x", "is_enabled": True,
            "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "metadata": {"a": 1},
        }

    def test_mismatched_row_length_propagates_from_decode_row(self, widgets_table):
        mapper = RowMapper(widgets_table, factory=lambda k: k)
        with pytest.raises(ValueError):
            mapper.from_row((1, "x"))  # too short


class TestRowMapperRoundtrip:
    """The property that actually matters for correctness: from_row(to_row(x)) == x
    for every field type combination the schema uses."""

    def test_full_roundtrip_all_fields(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: widget_factory(**k))
        original = widget_factory(
            id=7, name="Roundtrip", is_enabled=True,
            created_at=datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc),
            metadata={"nested": [1, 2, {"three": 3}]},
        )

        result = mapper.from_row(mapper.to_row(original))
        assert result == original

    def test_roundtrip_with_all_none_optional_fields(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: widget_factory(**k))
        original = widget_factory(id=1, name=None, is_enabled=None, created_at=None, metadata=None)

        result = mapper.from_row(mapper.to_row(original))
        assert result == original

    def test_roundtrip_with_serializer_and_no_default_codec(self, widgets_table_with_status, status_enum): # noqa: E501
        mapper = RowMapper(
            widgets_table_with_status,
            factory=lambda k: k,
            extract=lambda obj, name: obj.get(name),  # original is a dict, not an attr-object
        )
        original = {"id": 1, "status": status_enum.ACTIVE}

        row = mapper.to_row(original)
        assert row == (1, status_enum.ACTIVE.value)

        result = mapper.from_row(row)
        assert result == original

    def test_roundtrip_with_nested_serializer_object(self, status_enum):
        class Container: # noqa: PLW1641
            __slots__ = ("id", "inner")

            def __init__(self, id, inner):  # noqa: A002
                self.id = id
                self.inner = inner

            def __eq__(self, other):
                return isinstance(other, Container) and (self.id, self.inner) == (other.id, other.inner) # noqa: E501

        class Inner: # noqa: PLW1641
            __slots__ = ("value",)

            def __init__(self, value):
                self.value = value

            def __eq__(self, other):
                return isinstance(other, Inner) and self.value == other.value

        inner_serializer = SerializerObject(
            factory=lambda **kw: Inner(**kw),
            attrs=(Attr("value"),),
        )
        table = Table(
            name="containers",
            fields=(
                Field("id", DataType.BIGINT, nullable=False),
                Field("inner", DataType.JSON, serializer=inner_serializer),
            ),
            primary_key=("id",),
        )
        mapper = RowMapper(table, factory=lambda k: Container(**k))
        original = Container(id=1, inner=Inner(value="nested"))

        row = mapper.to_row(original)
        assert row == (1, '{"value": "nested"}')

        result = mapper.from_row(row)
        assert result == original

    def test_roundtrip_preserves_timedelta_zero_not_as_none(self):
        table = Table(
            name="durations",
            fields=(
                Field("id", DataType.BIGINT, nullable=False),
                Field("duration", DataType.SMALLINT, codec=CodecTimedelta()),
            ),
            primary_key=("id",),
        )
        mapper = RowMapper(
            table,
            factory=lambda k: k,
            extract=lambda obj, name: obj.get(name),  # same fix
        )
        original = {"id": 1, "duration": timedelta(0)}

        row = mapper.to_row(original)
        assert row == (1, 0.0)

        result = mapper.from_row(row)
        assert result["duration"] == timedelta(0)
        assert result["duration"] is not None


class TestRowMapperUpdateExclusionPattern:
    """Exercises the `fields=tuple(f for f in T.fields if f.name != "id")`
    pattern used repeatedly in SQLiteBackend's *_update methods."""

    def test_excluding_primary_key_from_set_clause(self, widgets_table, widget_factory):
        set_fields = tuple(f for f in widgets_table.fields if f.name != "id")
        mapper = RowMapper(widgets_table, factory=lambda k: k, fields=set_fields)

        w = widget_factory(id=999, name="x", is_enabled=True, created_at=None, metadata=None)
        row = mapper.to_row(w)

        assert "id" not in mapper.names
        assert len(row) == len(widgets_table.fields) - 1

    def test_excluding_composite_primary_key(self, widget_factory):
        table = Table(
            name="members",
            fields=(
                Field("id", DataType.BIGINT, nullable=False),
                Field("guild_id", DataType.BIGINT, nullable=False),
                Field("nickname", DataType.STRING),
            ),
            primary_key=("id", "guild_id"),
        )
        set_fields = tuple(f for f in table.fields if f.name not in ("id", "guild_id"))
        mapper = RowMapper(table, factory=lambda k: k, fields=set_fields)

        assert mapper.names == ("nickname",)


# ------------------------------------------------------- async usage sanity

class TestAsyncUsage:
    """RowMapper/decode_row are synchronous CPU-bound transforms; these confirm
    they behave correctly when called from within async backend methods,
    matching how SQLiteBackend actually invokes them."""

    @pytest.mark.asyncio
    async def test_to_row_inside_async_method(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: widget_factory(**k))

        async def fake_execute(row):
            return row  # stand-in for self._execute(sql, row, confirm)

        w = widget_factory(id=1, name="async", is_enabled=True, created_at=None, metadata=None)
        result = await fake_execute(mapper.to_row(w))

        assert result[1] == "async"

    @pytest.mark.asyncio
    async def test_from_row_inside_async_generator(self, widgets_table, widget_factory):
        mapper = RowMapper(widgets_table, factory=lambda k: widget_factory(**k))
        rows = [
            (1, "a", 1, None, None),
            (2, "b", 0, None, None),
        ]

        async def fake_iter_rows():
            for row in rows:
                yield mapper.from_row(row)

        results = [w async for w in fake_iter_rows()]

        assert results[0].name == "a"
        assert results[1].is_enabled is False  # falsy-but-decoded, not skipped
