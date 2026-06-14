"""Entry point: build the composition root, then launch the Textual app.

Run with ``python -m monay`` (or ``uv run python -m monay``).
"""

from __future__ import annotations

import os

from monay.bootstrap import build_container


def main() -> None:
    container = build_container()
    from monay.tui.app import Monay  # imported lazily so non-TUI uses stay light

    app = Monay(container.app_service(), container.registry())

    # MONAY_SELFCHECK builds + wires everything (migrations, services, the TUI
    # app object) without starting the event loop — a no-TTY smoke test for the
    # packaged binary. See .github/workflows/build.yml.
    if os.environ.get("MONAY_SELFCHECK"):
        print("monay selfcheck ok")
        return

    app.run()


if __name__ == "__main__":
    main()