"""Shared number formatting for the TUI (docs/DEVELOPING.md).

Two decimals, thousands separators; negatives in red wherever they appear.
"""

from __future__ import annotations

from rich.text import Text

from monay.domain.entities import Field
from monay.domain.money import Money
from monay.domain.values import Cap
from monay.tui import theme


def money_str(m: Money) -> str:
    return f"{m.display():,.2f}"


def budget_str(f: Field) -> str:
    """The budget, prefixed with its % for percentage-budgeted fields."""
    if f.budget_pct is None:
        return money_str(f.budget)
    return f"{f.budget_pct.value}% → {money_str(f.budget)}"


def signed(m: Money) -> Text:
    """The amount, red when negative (LEFT / CURRENT / REST / leftovers)."""
    return Text(money_str(m), style=theme.ERROR if m.is_negative else "")


def cap_str(cap: Cap) -> str:
    if cap.is_infinite:
        return "∞"
    assert cap.limit is not None  # finite ⟺ a concrete limit
    return money_str(cap.limit)
