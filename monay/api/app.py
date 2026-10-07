"""The FastAPI application factory.

``create_app()`` only *declares* the API; the composition root is resolved in
the lifespan hook, when the server actually starts. That keeps importing this
module — or dumping its OpenAPI document (``api/openapi.py``) — free of side
effects: no database is opened or migrated until there is a server to serve it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from monay import __version__
from monay.bootstrap import Container, build_container

from .errors import ERROR_RESPONSES, install_error_handlers
from .routes import incomes, meta, months, pockets, profiles, sections, transactions
from .settings import Settings


def create_app(container: Container | None = None) -> FastAPI:
    """Build the API. Pass a ``container`` to run against other wiring (tests)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        wired = container or build_container(Settings.from_env().db_url)
        app.state.budgeting = wired.budgeting()
        try:
            yield
        finally:
            if container is None:  # only dispose of an engine we created
                wired.engine().dispose()

    app = FastAPI(
        title="Monay API",
        summary="Zero-based budgeting with monthly rollover.",
        version=__version__,
        lifespan=lifespan,
        # Everything lives under /api so one reverse-proxy rule covers it.
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        generate_unique_id_function=_operation_id,
    )
    install_error_handlers(app)

    api = APIRouter(prefix="/api", responses=ERROR_RESPONSES)
    for module in (meta, profiles, months, incomes, sections, transactions, pockets):
        api.include_router(module.router)
    app.include_router(api)
    return app


def _operation_id(route: APIRoute) -> str:
    """Name each operation after its handler (``add_transaction``), not the
    path-derived default — these names surface in the generated client."""
    return route.name
