from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

__all__ = ("CachedObject",)

class CachedObject(ABC):
    """Base persistently cached object."""

    @classmethod
    @abstractmethod
    def from_sqlite(
        cls: type[CachedObject],
        row: aiosqlite.Row,
    ) -> CachedObject:
        """
        Create a new cached object from a SQLite row.

        Parameters
        ----------
        row : aiosqlite.Row
            The row to create the message from.

        Returns
        -------
        CachedObject
            The newly created object instance.
        """
