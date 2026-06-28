"""The Budget tab content (docs/DEVELOPING.md).

Shows the section accordion: one summary row per section (plus the income
pseudo-section), with any number expanded inline to show their field tables
(``expand``/``collapse``, or clicking a row). Returns a Rich renderable for the
app's content area.
"""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.text import Text

from monay.domain.month import Month
from monay.tui.widgets import accordion

_NO_SECTIONS = "No sections yet — section add post Need 50%   (see docs)"


def render_budget(month: Month | None, expanded: set[str]) -> RenderableType:
    if month is None:
        return Text("No month yet.", style="dim")
    if not month.sections:
        hint = Text(_NO_SECTIONS, style="dim")
        # Show income even before any section exists (#32): the income row still
        # renders via the accordion; the hint nudges adding a section.
        if not month.incomes:
            return hint
        return Group(accordion.build(month, expanded), hint)
    return accordion.build(month, expanded)
