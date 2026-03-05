from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)

__all__ = ("CachedObject",)

class CachedObject(ABC):
    """Base persistently cached object."""

    @classmethod
    @abstractmethod
    def from_sqlite(
        cls: type[CachedObject],
        row, # noqa: ANN001 - Ambiguous because aiosqlite is optional
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
