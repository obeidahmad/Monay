"""``SystemClock`` — the real :class:`monay.domain.ports.Clock` adapter."""

from __future__ import annotations

from datetime import date


class SystemClock:
    def today(self) -> date:
        return date.today()
