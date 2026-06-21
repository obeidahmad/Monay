"""SQLAlchemy adapters implementing the domain repository ports.

They translate rows ↔ domain objects via ``mappers`` and run on the connection
the Unit of Work hands them. ``MonthRepository.get`` returns a recomputed month;
``save`` refuses to modify a month already closed in storage (docs/DEVELOPING.md).
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy import select, update

from monay.domain.entities import Profile
from monay.domain.errors import MonthClosedError
from monay.domain.month import Month, MonthState
from monay.domain.values import MonthKey

from .mappers import (
    delete_profile,
    insert_month,
    inserted_id,
    load_month,
    update_month,
)
from .schema import months, profiles


class SqlAlchemyMonthRepository:
    def __init__(self, conn: sa.Connection) -> None:
        self._conn = conn

    def get(self, profile_id: int, key: MonthKey) -> Month | None:
        month = load_month(self._conn, profile_id, key)
        if month is not None:
            month.recompute()
        return month

    def add(self, month: Month) -> None:
        insert_month(self._conn, month)

    def save(self, month: Month) -> None:
        stored_state = self._conn.execute(
            select(months.c.state).where(months.c.id == month.id)
        ).scalar_one_or_none()
        if stored_state == MonthState.CLOSED.value:
            raise MonthClosedError(
                f"month {month.key} is closed in storage; "
                "corrections go in the open month"
            )
        update_month(self._conn, month)

    def keys(self, profile_id: int) -> list[MonthKey]:
        rows = self._conn.execute(
            select(months.c.key).where(months.c.profile_id == profile_id)
        ).scalars()
        return sorted(MonthKey.from_string(k) for k in rows)


class SqlAlchemyProfileRepository:
    def __init__(self, conn: sa.Connection) -> None:
        self._conn = conn

    def get(self, profile_id: int) -> Profile | None:
        row = conn_one(self._conn, select(profiles).where(profiles.c.id == profile_id))
        return _to_profile(row) if row is not None else None

    def by_name(self, name: str) -> Profile | None:
        row = conn_one(self._conn, select(profiles).where(profiles.c.name == name))
        return _to_profile(row) if row is not None else None

    def add(self, profile: Profile) -> Profile:
        profile.id = inserted_id(
            self._conn.execute(
                profiles.insert().values(
                    name=profile.name,
                    currency_symbol=profile.currency_symbol,
                    created_at=profile.created_at,
                )
            )
        )
        return profile

    def update(self, profile: Profile) -> None:
        self._conn.execute(
            update(profiles)
            .where(profiles.c.id == profile.id)
            .values(name=profile.name, currency_symbol=profile.currency_symbol)
        )

    def all(self) -> list[Profile]:
        rows = self._conn.execute(select(profiles).order_by(profiles.c.id))
        return [_to_profile(r) for r in rows]

    def delete(self, profile_id: int) -> None:
        delete_profile(self._conn, profile_id)


def conn_one(conn: sa.Connection, stmt: sa.Select[Any]) -> sa.Row[Any] | None:
    return conn.execute(stmt).one_or_none()


def _to_profile(row: sa.Row[Any]) -> Profile:
    return Profile(
        name=row.name,
        currency_symbol=row.currency_symbol,
        id=row.id,
        created_at=row.created_at,
    )
