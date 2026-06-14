"""0001 — initial schema: create every table."""

from __future__ import annotations

from ..schema import metadata

version = 1


def upgrade(conn) -> None:
    metadata.create_all(conn)
