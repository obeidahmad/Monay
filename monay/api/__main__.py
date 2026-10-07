"""Entry point: serve the API with uvicorn.

Run with ``python -m monay.api`` (or ``uv run python -m monay.api``). Host, port
and database come from the environment — see ``settings.py``.
"""

from __future__ import annotations

import uvicorn

from monay.api.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    # One process, on purpose: SQLite has a single writer and the undo journal
    # lives in memory (app/budgeting.py), so extra workers would only add ways
    # for an undo token to miss the worker that issued it.
    uvicorn.run(
        "monay.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
