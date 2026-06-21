"""Engine factory + the forward-only migration runner (docs/DEVELOPING.md).

One ``monay.db``. For tests, ``sqlite://`` (in-memory) uses a ``StaticPool`` so
every connection shares the same database. ``PRAGMA foreign_keys=ON`` is enabled
per connection so the schema's foreign keys are actually enforced.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy import delete, event, select
from sqlalchemy.pool import StaticPool

from . import migrations as _migrations
from .migrations import Migration
from .schema import schema_version

_IN_MEMORY = {"sqlite://", "sqlite:///:memory:"}


def make_engine(url: str = "sqlite:///monay.db", echo: bool = False) -> sa.Engine:
    kwargs: dict[str, Any] = {"echo": echo}
    if url in _IN_MEMORY:
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = sa.create_engine(url, **kwargs)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_conn: Any, _record: Any) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def run_migrations(engine: sa.Engine) -> None:
    """Apply every migration newer than the stored ``schema_version``."""
    with engine.begin() as conn:
        schema_version.create(conn, checkfirst=True)
        current = conn.execute(select(schema_version.c.version)).scalar() or 0
        for module in _ordered_migrations():
            if module.version > current:
                module.upgrade(conn)
                conn.execute(delete(schema_version))
                conn.execute(schema_version.insert().values(version=module.version))


def _ordered_migrations() -> list[Migration]:
    # Explicit registry (monay/data/migrations/__init__.py), not filesystem
    # discovery — so migrations also run inside a frozen PyInstaller binary.
    return sorted(_migrations.ALL, key=lambda m: m.version)
