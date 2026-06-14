"""SQLAlchemy Unit of Work — one transaction exposing the repositories.

``with uow:`` opens a connection + transaction; the repositories share it.
``commit()`` is explicit; leaving the block without committing (or on an
exception) rolls back (docs/DEVELOPING.md).
"""

from __future__ import annotations

import sqlalchemy as sa

from .repositories import SqlAlchemyMonthRepository, SqlAlchemyProfileRepository


class SqlAlchemyUnitOfWork:
    months: SqlAlchemyMonthRepository
    profiles: SqlAlchemyProfileRepository

    def __init__(self, engine: sa.Engine) -> None:
        self._engine = engine
        self._conn: sa.Connection | None = None
        self._tx = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._conn = self._engine.connect()
        self._tx = self._conn.begin()
        self.months = SqlAlchemyMonthRepository(self._conn)
        self.profiles = SqlAlchemyProfileRepository(self._conn)
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            if self._tx is not None and self._tx.is_active:
                self._tx.rollback()  # no-op if already committed
        finally:
            if self._conn is not None:
                self._conn.close()
            self._conn = None
            self._tx = None

    def commit(self) -> None:
        self._tx.commit()

    def rollback(self) -> None:
        if self._tx is not None and self._tx.is_active:
            self._tx.rollback()
