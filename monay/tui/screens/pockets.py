"""The Pockets tab (docs/DEVELOPING.md): where money should physically be.

Counter per pocket = Σ LEFT of its fields; the default pocket also carries the
live section RESTs. Each pocket shows a one-line field breakdown.
"""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.text import Text

from monay.domain.money import Money
from monay.tui.format import money_str, signed


def render_pockets(month, currency: str = "€") -> RenderableType:
    if not month.pockets:
        return Text("No pockets — pocket add Main", style="dim")

    fields_by_pocket: dict[str, list] = {}
    for s in month.sections:
        for f in s.fields:
            fields_by_pocket.setdefault(f.pocket.name, []).append(f)
    rests = sum((s.rest for s in month.sections), Money.zero())

    blocks: list[RenderableType] = []
    for p in sorted(month.pockets, key=lambda p: p.position):
        head = Text()
        head.append(p.name, style="bold")
        head.append("   should hold  ", style="dim")
        head.append(signed(p.counter))
        if p.is_default:
            head.append("   ← incl. live RESTs", style="dim")
        blocks.append(head)

        bits = [
            f"{f.name} {money_str(f.left)}" for f in fields_by_pocket.get(p.name, [])
        ]
        if p.is_default and not rests.is_zero:
            bits.append(f"RESTs {money_str(rests)}")
        if bits:
            blocks.append(Text("   " + " · ".join(bits), style="dim"))
    return Group(*blocks)
