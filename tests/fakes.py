"""In-memory test doubles for the domain ports (docs/PLAN.md §4, Phase 5).

The repositories store deep copies, so a loaded ``Month`` comes back as a fresh
object graph — exactly as a real SQLAlchemy adapter reconstructs one from rows.
This lets application-service tests (Phase 8) run with no database.
"""

from __future__ import annotations

import copy
import itertools
from datetime import date

from monay.domain.entities import Profile
from monay.domain.month import Month
from monay.domain.values import MonthKey


class FixedClock:
    def __init__(self, today: date) -> None:
        self._today = today

    def today(self) -> date:
        return self._today


class FakeMonthRepository:
    def __init__(self) -> None:
        self._store: dict[tuple[int, str], Month] = {}

    def get(self, profile_id: int, key: MonthKey) -> Month | None:
        stored = self._store.get((profile_id, str(key)))
        return copy.deepcopy(stored) if stored is not None else None

    def add(self, month: Month) -> None:
        self._put(month)

    def save(self, month: Month) -> None:
        self._put(month)

    def keys(self, profile_id: int) -> list[MonthKey]:
        return sorted(
            MonthKey.from_string(k) for (pid, k) in self._store if pid == profile_id
        )

    def _put(self, month: Month) -> None:
        self._store[(month.profile_id, str(month.key))] = copy.deepcopy(month)


class FakeProfileRepository:
    def __init__(self) -> None:
        self._store: dict[int, Profile] = {}
        self._ids = itertools.count(1)

    def get(self, profile_id: int) -> Profile | None:
        return self._store.get(profile_id)

    def by_name(self, name: str) -> Profile | None:
        return next((p for p in self._store.values() if p.name == name), None)

    def add(self, profile: Profile) -> Profile:
        if profile.id is None:
            profile.id = next(self._ids)
        self._store[profile.id] = profile
        return profile

    def update(self, profile: Profile) -> None:
        self._store[profile.id] = profile

    def all(self) -> list[Profile]:
        return list(self._store.values())

    def delete(self, profile_id: int) -> None:
        self._store.pop(profile_id, None)


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.months = FakeMonthRepository()
        self.profiles = FakeProfileRepository()
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, *exc: object) -> None:
        if exc and exc[0] is not None:
            self.rollback()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True
