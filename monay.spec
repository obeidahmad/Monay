# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Monay — a one-file binary that serves the web app.

    (cd web && npm ci && npm run build)   # the UI must be built first
    uv sync --no-dev --group build
    uv run --group build pyinstaller monay.spec
    # -> dist/monay   (dist/monay.exe on Windows)

PyInstaller bundles the *host* interpreter, so a binary only runs on the OS/arch
it was built on. CI (.github/workflows/build.yml) builds the matrix.
"""

import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# dependency-injector has a C-extension and resolves providers dynamically;
# uvicorn picks its loop/protocol implementations by import string — collect
# everything for both.
for package in ("dependency_injector", "uvicorn"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# The built React UI (web/ → monay/web/static), served by the FastAPI app.
if not os.path.isfile("monay/web/static/index.html"):
    raise SystemExit("monay/web/static is missing — run `npm run build` in web/ first")
datas += [("monay/web/static", "monay/web/static")]

# Migrations are discovered at runtime via pkgutil, so a static analysis can't
# see them — collect them explicitly or the frozen app can't build its schema.
hiddenimports += collect_submodules("monay.data.migrations")

a = Analysis(
    ["monay/__main__.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["openpyxl", "pytest", "tkinter"],  # dev-only / unused
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="monay",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,  # keeps a window with the URL; Ctrl+C stops the server
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # build host's native architecture
    codesign_identity=None,
    entitlements_file=None,
)
