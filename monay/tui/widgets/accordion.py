"""The Budget tab's accordion (docs/DEVELOPING.md).

One row per section (plus the income pseudo-section), each with its accent
border, kind·share, AVAILABLE and REST, and a ⚠ chip for negative REST. A row's
name is clickable: clicking it (or ``expand``/``collapse`` from the command bar)
toggles its field table **inline**, beneath the row, while every other row stays
visible. Any number of rows can be expanded at once. A summary line shows income,
the post pool, and the Σ% balance check.

This folds the former section-list, section-detail, and income-detail widgets
into a single view. The inline body of an expanded section is its field table
(Budget cyan · Current · Paid orange · Left green/red · Max · Pocket grey); the
income row expands to its per-entry table (Source · Amount · Kind).
"""

from __future__ import annotations

from decimal import Decimal

from rich import box
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.style import Style
from rich.table import Table
from rich.text import Text

from monay.domain.entities import (
    INCOME_SECTION_NAME,
    AllocKind,
    Section,
    SectionKind,
)
from monay.domain.money import Money
from monay.domain.month import Month
from monay.tui import theme
from monay.tui.format import cap_str, money_str, signed

_COLLAPSED = "▶"
_EXPANDED = "▼"


def build(month: Month, expanded: set[str]) -> RenderableType:
    sections = sorted(month.sections, key=lambda s: s.position)
    # Prune stale expansions (a section deleted/renamed since it was expanded) so
    # only rows that actually render can be open.
    valid = {s.name for s in sections} | {INCOME_SECTION_NAME}
    expanded = {name for name in expanded if name in valid}

    entries: list[_Entry] = []
    if month.incomes:
        is_open = INCOME_SECTION_NAME in expanded
        entries.append(
            _Entry(
                name=f"{_marker(is_open)} $ {INCOME_SECTION_NAME}",
                kind="",
                accent=theme.INCOME_ACCENT,
                avail=money_str(month.total_income),
                rest=Text(""),
                warn=Text(""),
                meta={"toggle_income": True},
                body=_income_table(month) if is_open else None,
            )
        )
    for i, s in enumerate(sections):
        is_open = s.name in expanded
        entries.append(
            _Entry(
                name=f"{_marker(is_open)} ▍{s.name}",
                kind=_kind_label(s),
                accent=theme.section_accent(i),
                avail=money_str(s.available),
                rest=signed(s.rest),
                warn=Text("⚠", style=theme.WARN) if s.rest.is_negative else Text(""),
                meta={"toggle_section": s.position},
                body=_field_table(s) if is_open else None,
            )
        )

    name_w = max([len("SECTIONS"), *(len(e.name) for e in entries)])
    kind_w = max([1, *(len(e.kind) for e in entries)])
    money_w = max(
        [
            len("avail"),
            len("rest"),
            *(len(e.avail) for e in entries),
            *(len(e.rest.plain) for e in entries),
        ]
    )

    blocks: list[RenderableType] = [
        _header_row(name_w, kind_w, money_w),
        _rule(name_w, kind_w, money_w),
    ]

    def add_entry(e: _Entry) -> None:
        row = _row_table(name_w, kind_w, money_w)
        # The custom meta key (not "@click") avoids Textual's link restyle, which
        # would override the accent color and underline the name; the app's
        # on_click reads this meta to toggle the row.
        label = Text(e.name, style=Style(color=e.accent, meta=e.meta))
        row.add_row(label, Text(e.kind), Text(e.avail), e.rest, e.warn)
        blocks.append(row)
        if e.body is not None:
            blocks.append(Padding(e.body, (0, 0, 1, 2)))  # indent + a trailing gap

    if month.incomes:
        add_entry(entries[0])  # income leads, set apart from the spending sections
        blocks.append(Text(""))
        section_entries = entries[1:]
    else:
        section_entries = entries
    for e in section_entries:
        add_entry(e)

    blocks.append(Text(""))  # breathe before the summary footer
    blocks.append(_summary(month, sections))
    return Group(*blocks)


class _Entry:
    """One accordion row's display data (an inline body when expanded)."""

    def __init__(
        self,
        *,
        name: str,
        kind: str,
        accent: str,
        avail: str,
        rest: Text,
        warn: Text,
        meta: dict[str, object],
        body: RenderableType | None,
    ) -> None:
        self.name = name
        self.kind = kind
        self.accent = accent
        self.avail = avail
        self.rest = rest
        self.warn = warn
        self.meta = meta
        self.body = body


def _marker(is_open: bool) -> str:
    return _EXPANDED if is_open else _COLLAPSED


def _rule(name_w: int, kind_w: int, money_w: int) -> Text:
    # A header underline spanning the table width: the five columns plus the
    # inter-column padding (4 gaps × 2 cells of padding, edges excluded).
    width = name_w + kind_w + 2 * money_w + 1 + 8
    return Text("─" * width, style="dim")


def _row_table(name_w: int, kind_w: int, money_w: int) -> Table:
    # A borderless one-row table; the shared explicit widths keep every row's
    # columns aligned even though expanded bodies sit between the rows.
    table = Table(box=None, show_header=False, pad_edge=False, expand=False)
    table.add_column(width=name_w)
    table.add_column(width=kind_w, style="dim")
    table.add_column(width=money_w, justify="right")
    table.add_column(width=money_w, justify="right")
    table.add_column(width=1)
    return table


def _header_row(name_w: int, kind_w: int, money_w: int) -> Table:
    table = _row_table(name_w, kind_w, money_w)
    table.add_row(
        Text("SECTIONS", style="bold"),
        Text(""),
        Text("avail", style="bold"),
        Text("rest", style="bold"),
        Text(""),
    )
    return table


def _field_table(s: Section) -> Table:
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
    return table


def _income_table(month: Month) -> Table:
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
    return table


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
