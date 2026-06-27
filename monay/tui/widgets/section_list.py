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

from monay.domain.entities import AllocKind, Section, SectionKind
from monay.domain.money import Money
from monay.domain.month import Month
from monay.tui import theme
from monay.tui.format import money_str, signed


def build(month: Month, currency: str = "€") -> RenderableType:
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


def _kind_label(s: Section) -> str:
    if s.alloc_kind is AllocKind.PCT:
        assert s.percentage is not None
        return f"{s.kind.value} · {s.percentage.value}%"
    assert s.amount is not None
    return f"{s.kind.value} · {money_str(s.amount)}"


def _summary(month: Month, sections: list[Section]) -> Text:
    # The pool POST sections split is income minus the TAX/PRE shares taken off
    # the top. Use the share (available − carried_rest), not available itself:
    # carried_rest is REST routed in from last month, not a cut of this income.
    def share(s: Section) -> Money:
        return s.available - s.carried_rest

    tax_total = sum(
        (share(s) for s in sections if s.kind is SectionKind.TAX), Money.zero()
    )
    pre_total = sum(
        (share(s) for s in sections if s.kind is SectionKind.PRE), Money.zero()
    )
    post_pool = month.total_income - tax_total - pre_total
    pct_total = sum(
        (
            s.percentage.value
            for s in sections
            if s.kind is SectionKind.POST and s.percentage
        ),
        Decimal(0),
    )
    has_post = any(s.kind is SectionKind.POST for s in sections)
    check = "✓" if pct_total == Decimal(100) else "⚠"
    parts = f"income {money_str(month.total_income)} · post pool {money_str(post_pool)}"
    if has_post:
        parts += f" · Σ% = {pct_total} {check}"
    return Text(parts, style="dim")
