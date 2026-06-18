"""The History tab (docs/DEVELOPING.md): every month, newest first.

``month <yyyy-mm>`` opens any month read-only; ``month`` returns to the open one.
"""

from __future__ import annotations

from rich import box
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from monay.tui.format import money_str


def render_history(summaries, viewing) -> RenderableType:
    if not summaries:
        return Text("No months yet.", style="dim")

    table = Table(box=box.SIMPLE, pad_edge=False, expand=False)
    table.add_column("Month")
    table.add_column("State")
    table.add_column("Income", justify="right")
    table.add_column("Spent", justify="right")
    table.add_column("Leftovers", justify="right")
    for s in summaries:
        state = "● open" if s.state.value == "open" else "🔒 closed"
        marker = "›" if s.key == viewing else " "
        table.add_row(
            f"{marker} {s.key}",
            state,
            money_str(s.income),
            money_str(s.spent),
            money_str(s.leftovers),
        )

    hint = Text(
        "month <yyyy-mm> opens a month read-only · month returns to the open one",
        style="dim",
    )
    return Group(table, hint)
