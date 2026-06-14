"""Palette and color helpers (docs/DEVELOPING.md).

Dark, color-coded: each section gets an accent from a fixed palette (assigned in
order), and each table column has a consistent color. The Budget tab (Phase 10)
uses these; the shell here uses the base + feedback colors.
"""

from __future__ import annotations

# Background steps
BG = "#0e0e12"
PANEL = "#1c1c24"
TABS_BG = "#14141a"
TEXT = "#cfcfd6"

# Feedback line
OK = "#98c379"
ERROR = "#e06c75"
WARN = "#e5c07b"
INFO = "#56b6c2"

# Section accents, assigned in order (Zakat gold, Need blue, Want magenta,
# Save green, then cyan/amber/… cycling).
SECTION_PALETTE = (
    "#d4af37",  # gold
    "#5b9bd5",  # blue
    "#c678dd",  # magenta
    "#98c379",  # green
    "#56b6c2",  # cyan
    "#e5c07b",  # amber
    "#61afef",  # azure
    "#e06c75",  # red
)

# Fixed per-column colors (Budget tab).
COLUMN_COLORS = {
    "budget": "#56b6c2",   # cyan
    "current": TEXT,       # dim white
    "paid": "#d19a66",     # orange
    "left": OK,            # green/red by sign (handled per-cell)
    "max": "#7f848e",      # dim
    "pocket": "#7f848e",   # grey
}


def section_accent(index: int) -> str:
    return SECTION_PALETTE[index % len(SECTION_PALETTE)]
