"""Forward-only migrations.

Each module exposes ``version`` and ``upgrade(conn)``. They are imported
**statically** and listed in ``ALL`` (in order) — not discovered from the
filesystem — so PyInstaller's analyzer follows the imports and bundles them into
a frozen binary. To add a migration: ``from . import mNNNN_x`` and append it to
``ALL``.
"""

from __future__ import annotations

from typing import Protocol

import sqlalchemy as sa

from . import m0001_initial, m0002_field_budget_pct


class Migration(Protocol):
    """The structural contract each migration module satisfies."""

    version: int

    def upgrade(self, conn: sa.Connection) -> None: ...


ALL: list[Migration] = [m0001_initial, m0002_field_budget_pct]
