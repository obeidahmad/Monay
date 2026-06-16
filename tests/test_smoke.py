"""Phase 0 smoke test: the package tree imports cleanly."""

import importlib


def test_package_imports():
    monay = importlib.import_module("monay")
    assert isinstance(monay.__version__, str) and monay.__version__


def test_layer_packages_import():
    for pkg in ("monay.domain", "monay.data", "monay.app", "monay.tui"):
        assert importlib.import_module(pkg) is not None