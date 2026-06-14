"""A section's drill-in: the field table (docs/DEVELOPING.md).

Header line with the section's avail / budget left / rest, then a row per field
with the fixed per-column colors (Budget cyan · Current · Paid orange · Left
green/red · Max · Pocket grey).
"""

from __future__ import annotations

from rich import box
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from monay.domain.entities import AllocKind
from monay.tui import theme
from monay.tui.format import cap_str, money_str, signed


def build(month, section_name: str, currency: str = "€") -> RenderableType:
    s = month.section(section_name)
    accent = _accent_for(month, s)

    header = Text(f"◂ {s.name.upper()} · {_kind_label(s)} · ", style=accent)
    header.append(Text(f"avail {money_str(s.available)} · budget left {money_str(s.budget_left)} · rest "))
    header.append(signed(s.rest))

    table = Table(box=box.SIMPLE, pad_edge=False, expand=False)
    table.add_column("Field")
    table.add_column("Budget", justify="right", style=theme.COLUMN_COLORS["budget"])
    table.add_column("Current", justify="right")
    table.add_column("Paid", justify="right", style=theme.COLUMN_COLORS["paid"])
    table.add_column("Left", justify="right")
    table.add_column("Max", justify="right", style=theme.COLUMN_COLORS["max"])
    table.add_column("Pocket", style=theme.COLUMN_COLORS["pocket"])

    for f in sorted(s.fields, key=lambda f: f.position):
        table.add_row(
            Text(f.name),
            Text(money_str(f.budget)),
            signed(f.current),
            Text(money_str(f.paid)),
            signed(f.left),
            Text(cap_str(f.cap)),
            Text(f.pocket.name),
        )

    return Group(header, table)


def _kind_label(s) -> str:
    if s.alloc_kind is AllocKind.PCT:
        return f"{s.kind.value} {s.percentage.value}%"
    return f"{s.kind.value} {money_str(s.amount)}"


def _accent_for(month, section) -> str:
    order = sorted(month.sections, key=lambda s: s.position)
    return theme.section_accent(order.index(section))