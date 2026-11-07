from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datetime import (
    UTC,
    datetime,
    timedelta,
)
from persist.internal.codecs import CodecDatetime, CodecTimedelta, CodecJSON
from persist.internal.serializers import (
    Attr,
    Serializer,
    SerializerCodec,
    SerializerEnum,
    SerializerFlag,
    SerializerIdentity,
    SerializerKeyedMapping,
    SerializerList,
    SerializerObject,
)

import asyncio


def test_serializer_is_abstract():
    with pytest.raises(TypeError):
        Serializer()  # type: ignore[abstract]


# ------------------------------------------------------- SerializerIdentity

class TestSerializerIdentity:
    @pytest.fixture
    def serializer(self):
        return SerializerIdentity()

    @pytest.mark.parametrize("value", [None, True, 0, "x", [1, 2], {"a": 1}])
    def test_passthrough(self, serializer, value):
        assert serializer.serialize(value) is value or serializer.serialize(value) == value
        assert serializer.deserialize(value) is value or serializer.deserialize(value) == value


# --------------------------------------------------------- SerializerCodec

class TestSerializerCodec:
    def test_delegates_to_codec_decode(self):
        codec = MagicMock()
        codec.decode.return_value = "decoded"
        serializer = SerializerCodec(codec)

        assert serializer.deserialize(123) == "decoded"
        codec.decode.assert_called_once_with(123)

    def test_delegates_to_codec_encode(self):
        codec = MagicMock()
        codec.encode.return_value = 456
        serializer = SerializerCodec(codec)

        assert serializer.serialize("value") == 456
        codec.encode.assert_called_once_with("value")

    def test_integration_with_real_datetime_codec(self):
        serializer = SerializerCodec(CodecDatetime())
        dt = datetime(2024, 1, 1, tzinfo=UTC)

        encoded = serializer.serialize(dt)
        assert isinstance(encoded, float)
        assert serializer.deserialize(encoded) == dt

    def test_integration_with_real_timedelta_codec(self):
        serializer = SerializerCodec(CodecTimedelta())
        td = timedelta(hours=2, minutes=30)

        assert serializer.deserialize(serializer.serialize(td)) == td


# ---------------------------------------------------------- SerializerEnum

class TestSerializerEnum:
    def test_deserialize(self, color_enum):
        serializer = SerializerEnum(color_enum)
        assert serializer.deserialize(1) is color_enum.RED

    def test_serialize(self, color_enum):
        serializer = SerializerEnum(color_enum)
        assert serializer.serialize(color_enum.GREEN) == 2

    def test_invalid_value_raises(self, color_enum):
        serializer = SerializerEnum(color_enum)
        with pytest.raises(ValueError):
            serializer.deserialize(999)

    def test_roundtrip(self, color_enum):
        serializer = SerializerEnum(color_enum)
        for member in color_enum:
            assert serializer.deserialize(serializer.serialize(member)) is member


# ---------------------------------------------------------- SerializerFlag

class TestSerializerFlag:
    def test_deserialize_single_flag(self, permission_flag):
        serializer = SerializerFlag(permission_flag)
        assert serializer.deserialize(1) is permission_flag.READ

    def test_deserialize_combined_flags(self, permission_flag):
        serializer = SerializerFlag(permission_flag)
        result = serializer.deserialize(3)  # READ | WRITE
        assert result == (permission_flag.READ | permission_flag.WRITE)

    def test_serialize(self, permission_flag):
        serializer = SerializerFlag(permission_flag)
        combined = permission_flag.READ | permission_flag.EXECUTE
        assert serializer.serialize(combined) == 5

    def test_roundtrip_combined(self, permission_flag):
        serializer = SerializerFlag(permission_flag)
        combined = permission_flag.WRITE | permission_flag.EXECUTE
        assert serializer.deserialize(serializer.serialize(combined)) == combined

    def test_zero_flag_roundtrip(self, permission_flag):
        serializer = SerializerFlag(permission_flag)
        assert serializer.deserialize(serializer.serialize(permission_flag.NONE)) == permission_flag.NONE  # noqa: E501


# ---------------------------------------------------------- SerializerList

class TestSerializerList:
    def test_empty_list(self):
        serializer = SerializerList(SerializerIdentity())
        assert serializer.serialize([]) == []
        assert serializer.deserialize([]) == []

    def test_none_treated_as_empty(self):
        # falsy-check (`if value else []`) means None collapses to []
        serializer = SerializerList(SerializerIdentity())
        assert serializer.deserialize(None) == []
        assert serializer.serialize(None) == []

    def test_identity_items(self):
        serializer = SerializerList(SerializerIdentity())
        assert serializer.serialize([1, 2, 3]) == [1, 2, 3]
        assert serializer.deserialize([1, 2, 3]) == [1, 2, 3]

    def test_nested_enum_items(self, color_enum):
        serializer = SerializerList(SerializerEnum(color_enum))
        assert serializer.serialize([color_enum.RED, color_enum.BLUE]) == [1, 3]
        assert serializer.deserialize([1, 3]) == [color_enum.RED, color_enum.BLUE]

    def test_order_preserved(self, color_enum):
        serializer = SerializerList(SerializerEnum(color_enum))
        members = [color_enum.BLUE, color_enum.RED, color_enum.GREEN]
        result = serializer.deserialize(serializer.serialize(members))
        assert result == members  # order, not just membership


# ---------------------------------------------------- SerializerKeyedMapping

class TestSerializerKeyedMapping:
    def test_empty_and_none(self, point_factory):
        item = SerializerObject(factory=point_factory, attrs=(Attr("x"), Attr("y")))
        serializer = SerializerKeyedMapping(item, key_attr="x")
        assert serializer.deserialize([]) == {}
        assert serializer.deserialize(None) == {}
        assert serializer.serialize({}) == []
        assert serializer.serialize(None) == []

    def test_keys_by_default_id_attr(self, point_factory):
        item = SerializerObject(
            factory=point_factory,
            attrs=(Attr("x"), Attr("y")),
        )
        # key_attr defaults to "id", so alias x -> id for this test via custom key_attr
        serializer = SerializerKeyedMapping(item, key_attr="x")
        raw = [{"x": 1, "y": 10}, {"x": 2, "y": 20}]

        result = serializer.deserialize(raw)
        assert set(result.keys()) == {1, 2}
        assert result[1] == point_factory(1, 10)
        assert result[2] == point_factory(2, 20)

    def test_roundtrip(self, point_factory):
        item = SerializerObject(factory=point_factory, attrs=(Attr("x"), Attr("y")))
        serializer = SerializerKeyedMapping(item, key_attr="x")
        original = {1: point_factory(1, 10), 2: point_factory(2, 20)}

        result = serializer.deserialize(serializer.serialize(original))
        assert result == original

    def test_duplicate_keys_last_wins(self, point_factory):
        item = SerializerObject(factory=point_factory, attrs=(Attr("x"), Attr("y")))
        serializer = SerializerKeyedMapping(item, key_attr="x")
        raw = [{"x": 1, "y": 10}, {"x": 1, "y": 999}]

        result = serializer.deserialize(raw)
        assert len(result) == 1
        assert result[1].y == 999


# -------------------------------------------------------------------- Attr

class TestAttr:
    def test_key_defaults_to_name(self):
        attr = Attr("field_name")
        assert attr.key == "field_name"

    def test_custom_key_overrides_name(self):
        attr = Attr("python_name", key="jsonKey")
        assert attr.name == "python_name"
        assert attr.key == "jsonKey"

    def test_serializer_optional(self):
        attr = Attr("x")
        assert attr.serializer is None


# --------------------------------------------------------- SerializerObject

class TestSerializerObject:
    def test_basic_roundtrip(self, point_factory):
        serializer = SerializerObject(
            factory=point_factory,
            attrs=(Attr("x"), Attr("y"), Attr("label")),
        )
        original = point_factory(1, 2, "origin")

        serialized = serializer.serialize(original)
        assert serialized == {"x": 1, "y": 2, "label": "origin"}
        assert serializer.deserialize(serialized) == original

    def test_none_attribute_bypasses_serializer(self, permission_flag):
        # a None value must NOT be passed through the sub-serializer, since
        # e.g. SerializerFlag(None) would raise on the enum lookup
        calls = []

        class TrackingSerializer(SerializerIdentity):
            def serialize(self, value):
                calls.append(value)
                return super().serialize(value)

        class Holder:
            def __init__(self, flags):
                self.flags = flags

        serializer = SerializerObject(
            factory=lambda **kw: Holder(**kw),
            attrs=(Attr("flags", serializer=TrackingSerializer()),),
        )
        serializer.serialize(Holder(None))

        assert calls == []  # sub-serializer never invoked for None

    def test_missing_key_on_deserialize_yields_none(self, point_factory):
        serializer = SerializerObject(
            factory=point_factory,
            attrs=(Attr("x"), Attr("y"), Attr("label")),
        )
        result = serializer.deserialize({"x": 1, "y": 2})  # "label" absent
        assert result == point_factory(1, 2, None)

    def test_key_aliasing_round_trip(self):
        class Holder: # noqa: PLW1641
            def __init__(self, internal_name):
                self.internal_name = internal_name

            def __eq__(self, other):
                return isinstance(other, Holder) and self.internal_name == other.internal_name

        serializer = SerializerObject(
            factory=lambda **kw: Holder(**kw),
            attrs=(Attr("internal_name", key="external_key"),),
        )
        serialized = serializer.serialize(Holder("value"))
        assert serialized == {"external_key": "value"}
        assert serializer.deserialize(serialized) == Holder("value")

    def test_nested_serializer_object(self, point_factory):
        class Line: # noqa: PLW1641
            def __init__(self, start, end):
                self.start = start
                self.end = end

            def __eq__(self, other):
                return isinstance(other, Line) and (self.start, self.end) == (other.start, other.end) # noqa: E501

        point_ser = SerializerObject(factory=point_factory, attrs=(Attr("x"), Attr("y")))
        line_ser = SerializerObject(
            factory=lambda **kw: Line(**kw),
            attrs=(
                Attr("start", serializer=point_ser),
                Attr("end", serializer=point_ser),
            ),
        )
        original = Line(point_factory(0, 0), point_factory(3, 4))

        serialized = line_ser.serialize(original)
        assert serialized == {"start": {"x": 0, "y": 0}, "end": {"x": 3, "y": 4}}
        assert line_ser.deserialize(serialized) == original

    def test_nested_codec_serializer_for_datetime(self):
        class Event:  # noqa: PLW1641
            def __init__(self, at):
                self.at = at

            def __eq__(self, other):
                return isinstance(other, Event) and self.at == other.at

        serializer = SerializerObject(
            factory=lambda **kw: Event(**kw),
            attrs=(Attr("at", serializer=SerializerCodec(CodecDatetime())),),
        )
        dt = datetime(2024, 5, 5, 5, 5, 5, tzinfo=UTC)
        original = Event(dt)

        serialized = serializer.serialize(original)
        assert serialized == {"at": pytest.approx(dt.timestamp())}
        assert serializer.deserialize(serialized) == original

    def test_enum_and_flag_attrs_together(self, color_enum, permission_flag):
        class Config:  # noqa: PLW1641
            def __init__(self, color, perms):
                self.color = color
                self.perms = perms

            def __eq__(self, other):
                return isinstance(other, Config) and (self.color, self.perms) == (other.color, other.perms) # noqa: E501

        serializer = SerializerObject(
            factory=lambda **kw: Config(**kw),
            attrs=(
                Attr("color", serializer=SerializerEnum(color_enum)),
                Attr("perms", serializer=SerializerFlag(permission_flag)),
            ),
        )
        original = Config(color_enum.BLUE, permission_flag.READ | permission_flag.WRITE)

        serialized = serializer.serialize(original)
        assert serialized == {"color": 3, "perms": 3}
        assert serializer.deserialize(serialized) == original


# ------------------------------------------------------- async-context sanity

class TestAsyncCompatibility:
    """These serializers/codecs are pure CPU-bound transforms with no I/O —
    there's nothing to `await` here. What matters for the real backend is
    that they behave identically when invoked from inside an async method
    (e.g. RowMapper.to_row called from SQLiteBackend.channel_create), so
    these tests exercise that calling convention rather than testing new
    behavior."""

    @pytest.mark.asyncio
    async def test_codec_usable_inside_async_function(self):
        async def encode_in_async_context(value):
            return CodecJSON().encode(value)

        result = await encode_in_async_context({"a": 1})
        assert result == '{"a": 1}'

    @pytest.mark.asyncio
    async def test_serializer_object_usable_inside_gather(self, point_factory):
        serializer = SerializerObject(factory=point_factory, attrs=(Attr("x"), Attr("y")))
        points = [point_factory(i, i * 2) for i in range(5)]

        async def serialize_one(p):
            return serializer.serialize(p)

        results = await asyncio.gather(*(serialize_one(p) for p in points))
        assert results == [{"x": i, "y": i * 2} for i in range(5)]
