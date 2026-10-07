"""Write the API's OpenAPI document — the contract the web app is typed from.

    python -m monay.api.openapi web/openapi.json

The web build turns that file into TypeScript types (``web/README.md``), so the
schema in ``api/schemas.py`` stays the single definition of the wire format.
Nothing here starts the app: no database is touched. With no path, the document
goes to stdout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from monay.api.app import create_app


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    # sort_keys: a stable file, so regenerating without changes is a no-op.
    document = json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"
    if args:
        Path(args[0]).write_text(document, encoding="utf-8")
    else:
        sys.stdout.write(document)


if __name__ == "__main__":
    main()
