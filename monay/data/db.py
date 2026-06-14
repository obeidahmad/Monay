"""Engine factory + the forward-only migration runner (docs/DEVELOPING.md).

One ``monay.db``. For tests, ``sqlite://`` (in-memory) uses a ``StaticPool`` so
every connection shares the same database. ``PRAGMA foreign_keys=ON`` is enabled
per connection so the schema's foreign keys are actually enforced.
"""

from __future__ import annotations

import importlib
import pkgutil

import sqlalchemy as sa
from sqlalchemy import delete, event, select
from sqlalchemy.pool import StaticPool

from . import migrations as _migrations
from .schema import metadata, schema_version

_IN_MEMORY = {"sqlite://", "sqlite:///:memory:"}


def make_engine(url: str = "sqlite:///monay.db", echo: bool = False) -> sa.Engine:
    kwargs: dict = {"echo": echo}
    if url in _IN_MEMORY:
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = sa.create_engine(url, **kwargs)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_conn, _record):  # noqa: ANN001
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


def _ordered_migrations() -> list:
    modules = []
    for info in pkgutil.iter_modules(_migrations.__path__):
        if info.name[0].isdigit():
            modules.append(importlib.import_module(f"{_migrations.__name__}.{info.name}"))
    return sorted(modules, key=lambda m: m.version)