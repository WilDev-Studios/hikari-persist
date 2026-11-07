from __future__ import annotations

from datetime import (
    UTC,
    datetime,
    timedelta,
    timezone,
)

import json

import pytest

from persist.internal.codecs import (
    Codec,
    CodecBoolean,
    CodecDatetime,
    CodecJSON,
    CodecTimedelta,
)


# ---------------------------------------------------------------- Codec ABC

def test_codec_is_abstract():
    with pytest.raises(TypeError):
        Codec()  # type: ignore[abstract]


# --------------------------------------------------------- CodecBoolean

class TestCodecBoolean:
    @pytest.fixture
    def codec(self):
        return CodecBoolean()

    @pytest.mark.parametrize("raw,expected", [(0, False), (1, True), (2, True), (-1, True)])
    def test_decode(self, codec, raw, expected):
        assert codec.decode(raw) is expected

    @pytest.mark.parametrize("value,expected", [(True, 1), (False, 0)])
    def test_encode(self, codec, value, expected):
        assert codec.encode(value) == expected

    def test_canonical_roundtrip(self, codec):
        assert codec.decode(codec.encode(True)) is True
        assert codec.decode(codec.encode(False)) is False

    def test_non_canonical_int_normalizes_on_roundtrip(self, codec):
        # decode(2) -> True -> encode -> 1, not 2: confirms lossy normalization
        assert codec.encode(codec.decode(2)) == 1


# -------------------------------------------------------- CodecDatetime

class TestCodecDatetime:
    @pytest.fixture
    def codec(self):
        return CodecDatetime()

    def test_decode_produces_utc_aware_datetime(self, codec):
        dt = codec.decode(0.0)
        assert dt == datetime(1970, 1, 1, tzinfo=UTC)
        assert dt.tzinfo is UTC

    def test_encode_utc_input(self, codec):
        dt = datetime(2024, 1, 1, tzinfo=UTC)
        assert codec.encode(dt) == pytest.approx(1704067200.0)

    def test_encode_non_utc_input_converts_correctly(self, codec):
        tz = timezone(timedelta(hours=5))
        dt = datetime(2024, 1, 1, 5, 0, 0, tzinfo=tz)  # == 2024-01-01T00:00:00Z
        assert codec.encode(dt) == pytest.approx(1704067200.0)

    @pytest.mark.parametrize("dt", [
        datetime(2000, 1, 1, tzinfo=UTC),
        datetime(2024, 6, 15, 12, 30, 45, 123456, tzinfo=UTC),
        datetime(2038, 1, 19, 3, 14, 7, tzinfo=UTC),  # past 32-bit overflow point
    ])
    def test_roundtrip_preserves_instant(self, codec, dt):
        result = codec.decode(codec.encode(dt))
        assert result == dt

    def test_roundtrip_preserves_microsecond_precision(self, codec):
        dt = datetime(2024, 3, 3, 3, 3, 3, 987654, tzinfo=UTC)
        result = codec.decode(codec.encode(dt))
        assert abs((result - dt).total_seconds()) < 1e-6

    def test_pre_epoch_datetime(self, codec):
        dt = datetime(1969, 12, 31, tzinfo=UTC)
        encoded = codec.encode(dt)
        assert encoded < 0
        assert codec.decode(encoded) == dt


# ------------------------------------------------------------- CodecJSON

class TestCodecJSON:
    @pytest.fixture
    def codec(self):
        return CodecJSON()

    @pytest.mark.parametrize("value", [
        None, True, False, 0, -1, 3.14, "", "hello", [],
        {}, [1, 2, 3], {"a": 1, "b": [2, 3]}, {"nested": {"deep": {"value": [1, None, True]}}},
    ])
    def test_roundtrip(self, codec, value):
        assert codec.decode(codec.encode(value)) == value

    def test_encode_produces_valid_json_string(self, codec):
        encoded = codec.encode({"a": 1})
        assert isinstance(encoded, str)
        assert json.loads(encoded) == {"a": 1}

    def test_decode_raises_on_invalid_json(self, codec):
        with pytest.raises(json.JSONDecodeError):
            codec.decode("{not valid json")

    def test_unicode_round_trips(self, codec):
        value = {"name": "héllo wörld 日本語 🎉"}
        assert codec.decode(codec.encode(value)) == value

    def test_key_order_preserved(self, codec):
        value = {"z": 1, "a": 2, "m": 3}
        result = codec.decode(codec.encode(value))
        assert list(result.keys()) == ["z", "a", "m"]

    def test_encode_nested_list_of_objects(self, codec):
        value = [{"id": 1, "tags": ["a", "b"]}, {"id": 2, "tags": []}]
        assert codec.decode(codec.encode(value)) == value


# --------------------------------------------------------- CodecTimedelta

class TestCodecTimedelta:
    @pytest.fixture
    def codec(self):
        return CodecTimedelta()

    def test_decode(self, codec):
        assert codec.decode(3600.0) == timedelta(hours=1)

    def test_encode(self, codec):
        assert codec.encode(timedelta(minutes=90)) == 5400.0

    @pytest.mark.parametrize("td", [
        timedelta(0),
        timedelta(seconds=1),
        timedelta(days=7),
        timedelta(seconds=-30),          # negative durations must survive
        timedelta(milliseconds=500),      # fractional seconds
        timedelta(days=365, hours=6),
    ])
    def test_roundtrip(self, codec, td):
        assert codec.decode(codec.encode(td)) == td

    def test_zero_is_falsy_but_not_none(self, codec):
        # regression guard: code elsewhere does `if value else None`-style checks;
        # timedelta(0) is falsy in Python, so a caller checking `if value` before
        # calling the codec would silently drop a legitimate zero-duration field.
        assert not timedelta(0)
        assert codec.encode(timedelta(0)) == 0.0
