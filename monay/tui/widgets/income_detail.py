"""The income pseudo-section's drill-in: the entries table (docs/DEVELOPING.md).

Reached via ``open income``. Header line with the month's total income, then a
row per income entry (Source · Amount · Kind) so the user can see exactly what
makes up their income — including which entries are leftovers (already taxed).
"""

from __future__ import annotations

from rich import box
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from monay.domain.entities import INCOME_SECTION_NAME
from monay.domain.month import Month
from monay.tui import theme
from monay.tui.format import money_str


def build(month: Month, currency: str = "€") -> RenderableType:
    header = Text(f"◂ {INCOME_SECTION_NAME.upper()} · ", style=theme.INCOME_ACCENT)
    header.append(f"total {money_str(month.total_income)}")

    table = Table(box=box.SIMPLE, pad_edge=False, expand=False)
    table.add_column("Source")
    table.add_column("Amount", justify="right")
    table.add_column("Kind", style="dim")

    for inc in sorted(month.incomes, key=lambda i: i.position):
        table.add_row(
            Text(inc.name),
            Text(money_str(inc.amount)),
            Text(inc.kind.value),
        )

    if not month.incomes:
        hint = Text("No income yet — income add Salary 1000", style="dim")
        return Group(header, hint)
    return Group(header, table)
