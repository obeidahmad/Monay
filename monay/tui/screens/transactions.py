"""The Transactions tab (docs/DEVELOPING.md).

Transactions newest-as-entered with a stable ``#`` (what ``tx edit``/``tx del``
target), then transfers with a ``⇄`` marker. ``tx <filter>`` narrows by field or
description text.
"""

from __future__ import annotations

from rich import box
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from monay.tui import theme
from monay.tui.format import money_str


def render_transactions(month, tx_filter: str | None, currency: str = "€") -> RenderableType:
    if not month.transactions and not month.transfers:
        return Text("No transactions yet — add <field> <amount>", style="dim")

    section_of = {id(f): s.name for s in month.sections for f in s.fields}
    flt = (tx_filter or "").lower().strip()
    rows = list(enumerate(month.transactions, start=1))
    if flt:
        rows = [
            (i, t)
            for i, t in rows
            if flt in t.field.name.lower() or flt in (t.description or "").lower()
        ]

    table = Table(box=box.SIMPLE, pad_edge=False, expand=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Day", justify="right")
    table.add_column("Section", style="dim")
    table.add_column("Field")
    table.add_column("Amount", justify="right", style=theme.COLUMN_COLORS["paid"])
    table.add_column("Description")
    for i, t in rows:
        table.add_row(
            str(i),
            str(int(t.day)),
            section_of.get(id(t.field), "?"),
            t.field.name,
            money_str(t.amount),
            t.description or "",
        )

    blocks: list[RenderableType] = [table]
    if not flt and month.transfers:
        transfers = Table(box=box.SIMPLE, pad_edge=False, expand=False)
        transfers.add_column("⇄", style=theme.section_accent(2))
        transfers.add_column("Day", justify="right")
        transfers.add_column("From → To")
        transfers.add_column("Amount", justify="right")
        transfers.add_column("Note")
        for t in month.transfers:
            transfers.add_row(
                "⇄",
                str(int(t.day)),
                f"{t.from_field.name} → {t.to_field.name}",
                money_str(t.amount),
                t.note or "",
            )
        blocks.append(transfers)

    if flt:
        blocks.append(Text(f"filtered by {tx_filter!r} — `tx` clears it", style="dim"))
    return Group(*blocks)
