"""Domain ports — the seam between the pure domain and the outside world.

These ``Protocol``s are *defined* in the domain but *implemented* in ``data/``
(SQLAlchemy) and faked in tests (docs/DEVELOPING.md).
Application services depend only on ``UnitOfWork`` + ``Clock``; the DI container
(Phase 7) wires the concrete adapters in. Dependencies point inward.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from .entities import Profile
from .month import Month
from .values import MonthKey


@runtime_checkable
class Clock(Protocol):
    """Supplies "today" so day-defaulting is deterministic in tests."""

    def today(self) -> date: ...


@runtime_checkable
class MonthRepository(Protocol):
    """Loads/saves a ``Month`` as a whole graph, scoped by profile."""

    def get(self, profile_id: int, key: MonthKey) -> Month | None: ...

    def add(self, month: Month) -> None: ...

    def save(self, month: Month) -> None: ...

    def keys(self, profile_id: int) -> list[MonthKey]: ...


@runtime_checkable
class ProfileRepository(Protocol):
    def get(self, profile_id: int) -> Profile | None: ...

    def by_name(self, name: str) -> Profile | None: ...

    def add(self, profile: Profile) -> Profile: ...

    def update(self, profile: Profile) -> None: ...

    def all(self) -> list[Profile]: ...

    def delete(self, profile_id: int) -> None: ...


@runtime_checkable
class UnitOfWork(Protocol):
    """One transaction exposing the repositories; rolls back on exception."""

    months: MonthRepository
    profiles: ProfileRepository

    def __enter__(self) -> "UnitOfWork": ...

    def __exit__(self, *exc: object) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
