"""The Docs tab (docs/DEVELOPING.md): a man-style reference of every command.

Driven entirely by the command registry, so it can never drift from what the app
actually accepts. ``help`` selects this tab; ``help <command>`` filters it. Needs
no profile or month, so it renders even before a profile exists.
"""

from __future__ import annotations

from rich import box
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from monay.app.commands.registry import CommandSpec
from monay.tui import theme


def render_docs(specs: list[CommandSpec], query: str | None = None) -> RenderableType:
    if query:
        specs = [s for s in specs if s.name.startswith(query)]
        if not specs:
            return Text(f"No command matching {query!r}.", style="dim")

    # Group by top-level verb, preserving the registry's declaration order.
    groups: dict[str, list[CommandSpec]] = {}
    for spec in specs:
        groups.setdefault(spec.path[0], []).append(spec)

    blocks: list[RenderableType] = [
        Text("Command reference", style="bold"),
        Text("Arguments: <required>  [optional]  name… variadic", style="dim"),
        Text(""),
    ]
    for verb, verb_specs in groups.items():
        table = Table(box=box.SIMPLE, pad_edge=False, expand=False, show_header=False)
        table.add_column("Usage", style=theme.INFO, no_wrap=True)
        table.add_column("What it does", style=theme.TEXT)
        for spec in verb_specs:
            table.add_row(spec.usage(), spec.help)
        blocks.append(Text(verb, style="bold"))
        blocks.append(table)

    return Group(*blocks)
