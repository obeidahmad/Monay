"""m0001 — initial schema: create every table.

Letter-prefixed (not ``0001_…``) so it's a valid Python identifier and gets
bundled by PyInstaller's ``collect_submodules``; ``version`` keeps the ordering.
"""

from __future__ import annotations

from ..schema import metadata

version = 1


def upgrade(conn) -> None:
    metadata.create_all(conn)
