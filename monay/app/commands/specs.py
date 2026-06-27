"""Every command declared once (docs/DEVELOPING.md). One spec drives parse, help,
and execution; the module-level ``REGISTRY`` is the app's command table.
"""

from __future__ import annotations

from . import handlers as h
from .registry import (
    AMOUNT,
    CAP,
    CHOICE,
    DAY,
    FIELD,
    INT,
    MONTH,
    POCKET,
    SECTION,
    TEXT,
    WORD,
    Arg,
    CommandRegistry,
    CommandSpec,
)

# Working tabs (left pane) and helper tabs (right pane). ``goto`` accepts either.
_WORKING_TABS = ("budget", "transactions", "pockets", "settings")
_HELPER_TABS = ("docs", "history")
_TABS = _WORKING_TABS + _HELPER_TABS

SPECS: list[CommandSpec] = [
    CommandSpec(
        ("add",),
        (
            Arg("field", FIELD),
            Arg("amount", AMOUNT),
            Arg("day", DAY, required=False),
            Arg("description", TEXT, required=False, variadic=True),
        ),
        "Record a transaction (money leaving a field's pot).",
        h.h_add,
    ),
    CommandSpec(
        ("transfer",),
        (
            Arg("amount", AMOUNT),
            Arg("from", FIELD),
            Arg("to", FIELD),
            Arg("day", DAY, required=False),
            Arg("note", TEXT, required=False, variadic=True),
        ),
        "Move accumulated pot money between fields "
        "(refused if it breaks the target's MAX).",
        h.h_transfer,
    ),
    CommandSpec(
        ("tx",),
        (Arg("filter", TEXT, required=False, variadic=True),),
        "Show/filter transactions (by field or text).",
        h.h_tx,
    ),
    CommandSpec(
        ("tx", "edit"),
        (
            Arg("index", INT),
            Arg("attr", CHOICE, choices=("amount", "day", "desc")),
            Arg("value", WORD),
        ),
        "Edit a transaction by its #.",
        h.h_tx_edit,
    ),
    CommandSpec(
        ("tx", "del"),
        (Arg("index", INT),),
        "Delete a transaction by its #.",
        h.h_tx_del,
        confirm=True,
        summary=h._del_summary("transaction"),
    ),
    CommandSpec(
        ("open",), (Arg("section", SECTION),), "Drill into a section.", h.h_open
    ),
    CommandSpec(("back",), (), "Return to the section list.", h.h_back),
    CommandSpec(
        ("section", "add"),
        (
            Arg("kind", CHOICE, choices=("pre", "post")),
            Arg("name", WORD),
            Arg("alloc", WORD),
        ),
        "Create a section (pre: %% or fixed amount; post: %%).",
        h.h_section_add,
    ),
    CommandSpec(
        ("section", "set"),
        (
            Arg("name", SECTION),
            Arg("attr", CHOICE, choices=("pct", "amount", "name", "rest")),
            Arg("value", WORD),
        ),
        "Edit a section; rest = routing (income / self / <section>).",
        h.h_section_set,
    ),
    CommandSpec(
        ("section", "order"),
        (Arg("name", SECTION), Arg("position", INT)),
        "Reorder a section (pre-order matters).",
        h.h_section_order,
    ),
    CommandSpec(
        ("section", "del"),
        (Arg("name", SECTION),),
        "Delete an empty section.",
        h.h_section_del,
        confirm=True,
        summary=h._del_summary("section"),
    ),
    CommandSpec(
        ("field", "add"),
        (
            Arg("section", SECTION),
            Arg("name", WORD),
            Arg("budget", AMOUNT, required=False),
            Arg("cap", CAP, required=False),
        ),
        "Create a field (budget defaults 0; cap defaults ∞; pass a number or inf).",
        h.h_field_add,
    ),
    CommandSpec(
        ("field", "set"),
        (
            Arg("name", FIELD),
            Arg("attr", CHOICE, choices=("budget", "max", "pocket", "name", "current")),
            Arg("value", WORD),
        ),
        "Edit a field (max inf for ∞; current only in a first month).",
        h.h_field_set,
    ),
    CommandSpec(
        ("field", "del"),
        (Arg("name", FIELD),),
        "Delete a field (only when LEFT = 0 and it has no activity).",
        h.h_field_del,
        confirm=True,
        summary=h._del_summary("field"),
    ),
    CommandSpec(
        ("income", "add"),
        (Arg("name", WORD), Arg("amount", AMOUNT)),
        "Add an income entry.",
        h.h_income_add,
    ),
    CommandSpec(
        ("income", "set"),
        (
            Arg("name", WORD),
            Arg("attr", CHOICE, choices=("name", "amount")),
            Arg("value", WORD),
        ),
        "Edit an income entry.",
        h.h_income_set,
    ),
    CommandSpec(
        ("income", "del"),
        (Arg("name", WORD),),
        "Delete an income entry.",
        h.h_income_del,
        confirm=True,
        summary=h._del_summary("income"),
    ),
    CommandSpec(
        ("pocket", "add"), (Arg("name", WORD),), "Add a pocket.", h.h_pocket_add
    ),
    CommandSpec(
        ("pocket", "rename"),
        (Arg("old", POCKET), Arg("new", WORD)),
        "Rename a pocket.",
        h.h_pocket_rename,
    ),
    CommandSpec(
        ("pocket", "del"),
        (Arg("name", POCKET),),
        "Delete an unused pocket.",
        h.h_pocket_del,
    ),
    CommandSpec(
        ("pocket", "main"),
        (Arg("name", POCKET),),
        "Make a pocket the default.",
        h.h_pocket_main,
    ),
    CommandSpec(
        ("month",),
        (Arg("key", MONTH, required=False),),
        "View a month (read-only if closed), or return to the open month.",
        h.h_month,
    ),
    CommandSpec(
        ("close",),
        (),
        "Close the open month (creates the next).",
        h.h_close,
        confirm=True,
        summary=h.close_summary,
    ),
    CommandSpec(
        ("goto",), (Arg("tab", CHOICE, choices=_TABS),), "Switch tab.", h.h_goto
    ),
    CommandSpec(
        ("profile", "add"),
        (Arg("name", WORD),),
        "Create and select a profile.",
        h.h_profile_add,
    ),
    CommandSpec(
        ("profile", "switch"),
        (Arg("name", WORD),),
        "Switch to a profile.",
        h.h_profile_switch,
    ),
    CommandSpec(
        ("profile", "rename"),
        (Arg("name", WORD),),
        "Rename the current profile.",
        h.h_profile_rename,
    ),
    CommandSpec(
        ("profile", "del"),
        (Arg("name", WORD),),
        "Delete a profile and all its months.",
        h.h_profile_del,
        confirm=True,
        summary=h._del_summary("profile"),
    ),
    CommandSpec(
        ("help",),
        (Arg("command", TEXT, required=False, variadic=True),),
        "Quick syntax reference.",
        h.h_help,
    ),
    CommandSpec(("quit",), (), "Exit Monay.", h.h_quit),
]


def build_registry() -> CommandRegistry:
    return CommandRegistry(SPECS)


REGISTRY = build_registry()
