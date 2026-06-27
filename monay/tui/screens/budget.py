"""The Budget tab content (docs/DEVELOPING.md).

Shows the section list, or a section's field table when drilled in (``open
<section>``). ``open income`` drills into the synthetic income pseudo-section.
Returns a Rich renderable for the app's content area.
"""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.text import Text

from monay.domain.entities import INCOME_SECTION_NAME
from monay.domain.errors import NotFoundError
from monay.domain.month import Month
from monay.tui.widgets import income_detail, section_detail, section_list

_NO_SECTIONS = "No sections yet — section add post Need 50%   (see docs)"


def render_budget(
    month: Month | None, drilled_section: str | None, currency: str = "€"
) -> RenderableType:
    if month is None:
        return Text("No month yet.", style="dim")
    if drilled_section and drilled_section.lower() == INCOME_SECTION_NAME:
        return income_detail.build(month, currency)
    if not month.sections:
        hint = Text(_NO_SECTIONS, style="dim")
        # Show income even before any section exists (#32): the income row still
        # renders via the section list; the hint nudges adding a section.
        if not month.incomes:
            return hint
        return Group(section_list.build(month, currency), hint)
    if drilled_section:
        try:
            return section_detail.build(month, drilled_section, currency)
        except NotFoundError:
            pass  # section gone (e.g. deleted) — fall back to the list
    return section_list.build(month, currency)
