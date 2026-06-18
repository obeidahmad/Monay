"""Monay — a modern terminal budget app with monthly rollover logic.

Layering (see docs/DEVELOPING.md): ``tui`` -> ``app`` -> ``domain``;
``data`` <-> ``app``. ``domain`` is pure (no DB, no UI). ``data`` and
``domain`` never import each other.
"""

# The version is the git tag, resolved at build time by hatch-vcs, which writes
# the gitignored monay/_version.py (see docs/RELEASING.md). There is no version
# string to hand-edit. The fallback only applies to a source checkout that was
# never built (no _version.py yet) — `uv sync` generates it.
try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.0.0+unknown"
