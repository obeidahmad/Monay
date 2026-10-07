"""Runtime configuration, read from the environment (twelve-factor style).

Three variables; each has a default that suits running from a source checkout:

* ``MONAY_DB_URL`` — SQLAlchemy URL of the database. Defaults to ``monay.db``
  in the working directory, the same file the TUI uses.
* ``MONAY_API_HOST`` — interface to bind. Loopback by default: the API has no
  authentication, so it is not offered to the network unless asked to be.
* ``MONAY_API_PORT`` — port to listen on.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_DB_URL = "sqlite:///monay.db"


@dataclass(frozen=True)
class Settings:
    db_url: str = DEFAULT_DB_URL
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        return cls(
            db_url=source.get("MONAY_DB_URL", cls.db_url),
            host=source.get("MONAY_API_HOST", cls.host),
            port=int(source.get("MONAY_API_PORT", cls.port)),
        )
