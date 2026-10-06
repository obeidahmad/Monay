"""Entry point: build the composition root, then serve the web app.

Run with ``python -m monay`` (or ``uv run python -m monay``). Monay serves its
API and the built React UI on http://127.0.0.1:8765 and opens a browser tab.
``MONAY_PORT`` / ``MONAY_HOST`` change where it listens; ``MONAY_NO_BROWSER=1``
skips opening the browser.
"""

from __future__ import annotations

import os
import threading
import webbrowser

from monay.bootstrap import build_container


def main() -> None:
    container = build_container()
    service = container.app_service()

    # MONAY_SELFCHECK builds + wires everything and hits the database (so a
    # missing migration / table surfaces) without starting the server — a
    # no-TTY smoke test for the packaged binary. See .github/workflows/build.yml.
    if os.environ.get("MONAY_SELFCHECK"):
        service.resume()  # queries the profiles table
        container.web_app()  # builds the API + frontend routes
        from monay import __version__  # confirms the baked-in version resolved

        print(f"monay {__version__} selfcheck ok")
        return

    import uvicorn  # imported lazily so non-server uses stay light

    service.resume()  # re-select an existing profile + its open month
    host = os.environ.get("MONAY_HOST", "127.0.0.1")
    port = int(os.environ.get("MONAY_PORT", "8765"))
    url = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}"
    print(f"Monay is running at {url}  (Ctrl+C to stop)")
    if not os.environ.get("MONAY_NO_BROWSER"):
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(container.web_app(), host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
