"""The Budget tab's default view: the section list (docs/DEVELOPING.md).

One row per section with its accent border, kind·share, AVAILABLE and REST, plus
a ⚠ chip for negative REST. A summary line shows income, the post pool, and the
Σ% balance check.
"""

from __future__ import annotations

from decimal import Decimal

from rich import box
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from monay.domain.entities import AllocKind, SectionKind
from monay.domain.money import Money
from monay.tui import theme
from monay.tui.format import money_str, signed


def build(month, currency: str = "€") -> RenderableType:
    sections = sorted(month.sections, key=lambda s: s.position)

    table = Table(box=box.SIMPLE, pad_edge=False, expand=False)
    table.add_column("SECTIONS")
    table.add_column("", style="dim")  # kind · share
    table.add_column("avail", justify="right")
    table.add_column("rest", justify="right")
    table.add_column("", width=1)  # warning chip

    for i, s in enumerate(sections):
        accent = theme.section_accent(i)
        table.add_row(
            Text(f"▍{s.name}", style=accent),
            Text(_kind_label(s)),
            Text(money_str(s.available)),
            signed(s.rest),
            Text("⚠", style=theme.WARN) if s.rest.is_negative else Text(""),
        )

    return Group(table, _summary(month, sections))


def _kind_label(s) -> str:
    if s.alloc_kind is AllocKind.PCT:
        return f"{s.kind.value} · {s.percentage.value}%"
    return f"{s.kind.value} · {money_str(s.amount)}"


def _summary(month, sections) -> Text:
    pre_total = sum((s.available for s in sections if s.kind is SectionKind.PRE), Money.zero())
    post_pool = month.total_income - pre_total
    pct_total = sum(
        (s.percentage.value for s in sections if s.kind is SectionKind.POST and s.percentage),
        Decimal(0),
    )
    has_post = any(s.kind is SectionKind.POST for s in sections)
    check = "✓" if pct_total == Decimal(100) else "⚠"
    parts = f"income {money_str(month.total_income)} · post pool {money_str(post_pool)}"
    if has_post:
        parts += f" · Σ% = {pct_total} {check}"
    return Text(parts, style="dim")