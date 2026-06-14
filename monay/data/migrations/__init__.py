"""Forward-only migrations. Each module exposes ``version`` and ``upgrade(conn)``.

The runner in ``data/db.py`` discovers the modules whose name starts with a
digit, orders them by ``version``, and applies any newer than ``schema_version``.
"""
