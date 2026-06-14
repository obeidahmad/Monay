"""Monay — a modern terminal budget app with monthly rollover logic.

Layering (see docs/DEVELOPING.md): ``tui`` -> ``app`` -> ``domain``;
``data`` <-> ``app``. ``domain`` is pure (no DB, no UI). ``data`` and
``domain`` never import each other.
"""

__version__ = "1.0.1"