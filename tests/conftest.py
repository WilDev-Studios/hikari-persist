from __future__ import annotations

from enum import Enum, Flag

from persist.internal.definitions import DataType, Field, Table
from persist.internal.serializers import SerializerEnum

import pytest


@pytest.fixture
def color_enum():
    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3
    return Color


@pytest.fixture
def permission_flag():
    class Permission(Flag):
        NONE = 0
        READ = 1
        WRITE = 2
        EXECUTE = 4
    return Permission


class Point: # noqa: PLW1641
    """Plain factory target for SerializerObject tests — deliberately not a
    dataclass, to mirror hikari's attrs-style constructors."""
    __slots__ = ("label", "x", "y")

    def __init__(self, x: int, y: int, label: str | None = None) -> None:
        self.x = x
        self.y = y
        self.label = label

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Point) and (self.x, self.y, self.label) == (other.x, other.y, other.label) # noqa: E501

    def __repr__(self) -> str:
        return f"Point(x={self.x}, y={self.y}, label={self.label!r})"


@pytest.fixture
def point_factory():
    return Point

@pytest.fixture
def status_enum():
    class Status(Enum):
        ACTIVE = 1
        INACTIVE = 2
    return Status


class Widget: # noqa: PLW1641
    """Plain object standing in for a hikari-style model with mixed field types."""
    __slots__ = ("created_at", "id", "is_enabled", "metadata", "name")

    def __init__(self, id, name, is_enabled, created_at, metadata=None):  # noqa: A002
        self.id = id
        self.name = name
        self.is_enabled = is_enabled
        self.created_at = created_at
        self.metadata = metadata

    def __eq__(self, other):
        if not isinstance(other, Widget):
            return NotImplemented
        return (self.id, self.name, self.is_enabled, self.created_at, self.metadata) == \
               (other.id, other.name, other.is_enabled, other.created_at, other.metadata)

    def __repr__(self):
        return f"Widget(id={self.id}, name={self.name!r}, is_enabled={self.is_enabled}, created_at={self.created_at}, metadata={self.metadata})" # noqa: E501


@pytest.fixture
def widget_factory():
    return Widget


@pytest.fixture
def widgets_table():
    """Mirrors the real schema pattern: identity fields, an implicit-codec
    BOOLEAN, an implicit-codec DATETIME, and a JSON field with an explicit
    serializer layered on top of the JSON codec."""
    return Table(
        name="widgets",
        fields=(
            Field("id", DataType.BIGINT, nullable=False),
            Field("name", DataType.STRING),
            Field("is_enabled", DataType.BOOLEAN),
            Field("created_at", DataType.DATETIME),
            Field("metadata", DataType.JSON),
        ),
        primary_key=("id",),
    )


@pytest.fixture
def widgets_table_with_status(status_enum):
    """A TINYINT field with an explicit serializer and NO default codec —
    exercises the resolve_codec()-returns-None branch."""
    return Table(
        name="widgets",
        fields=(
            Field("id", DataType.BIGINT, nullable=False),
            Field("status", DataType.TINYINT, serializer=SerializerEnum(status_enum)),
        ),
        primary_key=("id",),
    )
