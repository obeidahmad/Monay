"""The Budget tab content (docs/DEVELOPING.md).

Shows the section list, or a section's field table when drilled in (``open
<section>``). Returns a Rich renderable for the app's content area.
"""

from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text

from monay.domain.errors import NotFoundError
from monay.domain.month import Month
from monay.tui.widgets import section_detail, section_list


def render_budget(
    month: Month | None, drilled_section: str | None, currency: str = "€"
) -> RenderableType:
    if month is None:
        return Text("No month yet.", style="dim")
    if not month.sections:
        return Text(
            "No sections yet — section add post Need 50%   (see docs)", style="dim"
        )
    if drilled_section:
        try:
            return section_detail.build(month, drilled_section, currency)
        except NotFoundError:
            pass  # section gone (e.g. deleted) — fall back to the list
    return section_list.build(month, currency)
