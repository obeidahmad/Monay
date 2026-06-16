"""Entry point: build the composition root, then launch the Textual app.

Run with ``python -m monay`` (or ``uv run python -m monay``).
"""

from __future__ import annotations

import os

from monay.bootstrap import build_container


def main() -> None:
    container = build_container()
    service = container.app_service()
    from monay.tui.app import Monay  # imported lazily so non-TUI uses stay light

    app = Monay(service, container.registry())

    # MONAY_SELFCHECK builds + wires everything and hits the database (so a
    # missing migration / table surfaces) without starting the event loop — a
    # no-TTY smoke test for the packaged binary. See .github/workflows/build.yml.
    if os.environ.get("MONAY_SELFCHECK"):
        service.resume()  # queries the profiles table
        from monay import __version__  # confirms the baked-in version resolved

        print(f"monay {__version__} selfcheck ok")
        return

    app.run()


if __name__ == "__main__":
    main()