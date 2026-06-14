"""Shared pytest fixtures.

The project root is added to ``sys.path`` via ``[tool.pytest.ini_options]
pythonpath`` in pyproject.toml, so ``import monay`` works without installing
the package (``[tool.uv] package = false``).
"""
