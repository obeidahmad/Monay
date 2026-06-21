"""The Settings tab (docs/DEVELOPING.md): profile name/currency + profile list.

Sections/fields/pockets are managed where you see them (via commands), not here.
"""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.text import Text

from monay.app.services import MonayApp
from monay.domain.entities import Profile


def render_settings(service: MonayApp, profiles: list[Profile]) -> RenderableType:
    head = Text()
    head.append("Profile: ", style="dim")
    head.append(service.profile_name or "—", style="bold")
    head.append("        Currency: ", style="dim")
    head.append(service.currency)

    names = ", ".join(
        (f"{p.name} *" if p.id == service.profile_id else p.name) for p in profiles
    )
    listing = Text(f"Profiles: {names or '—'}", style="dim")

    hints = Text(
        "\n".join(
            (
                "Manage:  profile add|switch|rename|del <name>",
                "(* marks the current profile)",
            )
        ),
        style="dim",
    )
    return Group(head, Text(""), listing, hints)
