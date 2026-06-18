"""Shared number formatting for the TUI (docs/DEVELOPING.md).

Two decimals, thousands separators; negatives in red wherever they appear.
"""

from __future__ import annotations

from rich.text import Text

from monay.domain.money import Money
from monay.domain.values import Cap
from monay.tui import theme


def money_str(m: Money) -> str:
    return f"{m.display():,.2f}"


def signed(m: Money) -> Text:
    """The amount, red when negative (LEFT / CURRENT / REST / leftovers)."""
    return Text(money_str(m), style=theme.ERROR if m.is_negative else "")


def cap_str(cap: Cap) -> str:
    return "∞" if cap.is_infinite else money_str(cap.limit)
