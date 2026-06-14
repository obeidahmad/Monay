# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Monay — a one-file terminal binary.

    uv sync --no-dev --group build
    uv run --group build pyinstaller monay.spec
    # -> dist/monay   (dist/monay.exe on Windows)

PyInstaller bundles the *host* interpreter, so a binary only runs on the OS/arch
it was built on. CI (.github/workflows/build.yml) builds the matrix.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# Textual ships CSS/data files; dependency-injector has a C-extension and
# resolves providers dynamically — collect everything for both.
for package in ("textual", "dependency_injector"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

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
    console=True,  # Monay is a terminal app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # build host's native architecture
    codesign_identity=None,
    entitlements_file=None,
)
