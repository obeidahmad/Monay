"""Composition root — the one place that names concrete types and wires them.

A ``dependency-injector`` container (docs/DEVELOPING.md): a ``Singleton``
engine (one ``monay.db``) and ``Clock``, and a ``Factory`` Unit of Work (a fresh
transaction per use case). Application-service and app providers are added as
those types arrive (Phases 8–9). Tests swap any provider with a one-line
``.override(...)`` — e.g. the in-memory ``FakeUnitOfWork``.
"""

from __future__ import annotations

from dependency_injector import containers, providers

from monay.app.clock import SystemClock
from monay.app.commands import build_registry
from monay.app.services import MonayApp
from monay.data.db import make_engine, run_migrations
from monay.data.unit_of_work import SqlAlchemyUnitOfWork


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    engine = providers.Singleton(make_engine, url=config.db_url)
    clock = providers.Singleton(SystemClock)
    unit_of_work = providers.Factory(SqlAlchemyUnitOfWork, engine=engine)

    # The session-bearing application facade is a Singleton; it gets the UoW
    # *provider* (`.provider`) so each use case opens a fresh transaction.
    app_service = providers.Singleton(
        MonayApp, uow_factory=unit_of_work.provider, clock=clock
    )
    registry = providers.Singleton(build_registry)


def build_container(db_url: str = "sqlite:///monay.db") -> Container:
    """Build the container, configured and migrated, ready to resolve providers."""
    container = Container()
    container.config.from_dict({"db_url": db_url})
    run_migrations(container.engine())
    return container
