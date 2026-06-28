"""Command handlers — thin glue from parsed args to ``MonayApp`` use cases.

Each ``h_*`` takes ``(app, args)`` and returns a :class:`Result`. Domain/app
errors raised here are caught by the registry and turned into an error Result.
Handlers do the last bit of text→type interpretation that depends on the command
(``inf`` caps, ``50%`` allocations, ``income``/``self``/``<section>`` routing).
"""

from __future__ import annotations

from monay.app.services import MonayApp, month_label
from monay.domain.expressions import evaluate
from monay.domain.money import Money
from monay.domain.month import Month
from monay.domain.values import Cap, Percentage, RestRouting

from .registry import Args, Result, SummaryFn


# --- small interpreters ---------------------------------------------------
def _cap(token: str) -> Cap:
    if token.lower() in ("inf", "infinite", "∞"):
        return Cap.infinite()
    return Cap.finite(evaluate(token))


def _percentage(token: str) -> Percentage:
    return Percentage(token[:-1] if token.endswith("%") else token)


def _routing(token: str) -> RestRouting:
    low = token.lower()
    if low == "income":
        return RestRouting.to_income()
    if low == "self":
        return RestRouting.to_self()
    return RestRouting.to_section(token)


def _field_line(month: Month, field_name: str, verb: str) -> str:
    section, f = month.locate_field(field_name)
    rest = month.section(section).rest
    return (
        f"✓ {verb} {field_name}: LEFT {f.left.display()} "
        f"({section} REST {rest.display()})"
    )


# --- transactions / transfers --------------------------------------------
def h_add(app: MonayApp, a: Args) -> Result:
    m = app.add_transaction(a["field"], a["amount"], a["day"], a["description"] or "")
    return Result.ok(_field_line(m, a["field"], f"−{a['amount'].display()}"), m)


def h_transfer(app: MonayApp, a: Args) -> Result:
    m = app.transfer(a["amount"], a["from"], a["to"], a["day"], a["note"] or "")
    return Result.ok(f"✓ moved {a['amount'].display()} {a['from']} → {a['to']}", m)


def h_tx(app: MonayApp, a: Args) -> Result:
    flt = (a["filter"] or "").strip() or None
    app.set_tx_filter(flt)
    return Result.info(
        f"transactions filtered by {flt!r}" if flt else "showing all transactions"
    )


def h_tx_edit(app: MonayApp, a: Args) -> Result:
    attr, value = a["attr"], a["value"]
    kw: Args = {}
    if attr == "amount":
        kw["amount"] = evaluate(value)
    elif attr == "day":
        kw["day"] = int(value)
    elif attr == "desc":
        kw["description"] = value
    m = app.edit_transaction(a["index"], **kw)
    return Result.ok(f"✓ transaction #{a['index']} updated", m)


def h_tx_del(app: MonayApp, a: Args) -> Result:
    m = app.delete_transaction(a["index"])
    return Result.ok(f"✓ transaction #{a['index']} deleted", m)


# --- sections -------------------------------------------------------------
def h_section_add(app: MonayApp, a: Args) -> Result:
    token = a["alloc"]
    if token.endswith("%"):
        m = app.add_section(a["kind"], a["name"], percentage=_percentage(token))
    else:
        m = app.add_section(a["kind"], a["name"], amount=evaluate(token))
    return Result.ok(f"✓ section {a['name']} ({a['kind']})", m)


def h_section_set(app: MonayApp, a: Args) -> Result:
    attr, name, value = a["attr"], a["name"], a["value"]
    if attr == "pct":
        m = app.set_section_pct(name, _percentage(value))
    elif attr == "amount":
        m = app.set_section_amount(name, evaluate(value))
    elif attr == "name":
        m = app.rename_section(name, value)
    else:  # rest
        m = app.set_section_routing(name, _routing(value))
    return Result.ok(f"✓ section {name} updated", m)


def h_section_order(app: MonayApp, a: Args) -> Result:
    m = app.order_section(a["name"], a["position"])
    return Result.ok(f"✓ section {a['name']} → position {a['position']}", m)


def h_section_del(app: MonayApp, a: Args) -> Result:
    m = app.delete_section(a["name"])
    return Result.ok(f"✓ section {a['name']} deleted", m)


# --- fields ---------------------------------------------------------------
def h_field_add(app: MonayApp, a: Args) -> Result:
    budget = a["budget"] if a["budget"] is not None else Money("0")
    cap = _cap(a["cap"]) if a["cap"] is not None else Cap.infinite()
    m = app.add_field(a["section"], a["name"], budget, cap)
    return Result.ok(f"✓ field {a['name']} added to {a['section']}", m)


def h_field_set(app: MonayApp, a: Args) -> Result:
    attr, name, value = a["attr"], a["name"], a["value"]
    if attr == "budget":
        m = app.set_field_budget(name, evaluate(value))
    elif attr == "max":
        m = app.set_field_cap(name, _cap(value))
    elif attr == "pocket":
        m = app.set_field_pocket(name, value)
    elif attr == "name":
        m = app.rename_field(name, value)
    else:  # current
        m = app.set_field_current(name, evaluate(value))
    return Result.ok(
        _field_line(m, name if attr != "name" else value, f"{attr} set"), m
    )


def h_field_del(app: MonayApp, a: Args) -> Result:
    m = app.delete_field(a["name"])
    return Result.ok(f"✓ field {a['name']} deleted", m)


# --- income ---------------------------------------------------------------
def h_income_add(app: MonayApp, a: Args) -> Result:
    m = app.add_income(a["name"], a["amount"])
    return Result.ok(
        f"✓ income {a['name']} {a['amount'].display()} "
        f"(total {m.total_income.display()})",
        m,
    )


def h_income_set(app: MonayApp, a: Args) -> Result:
    if a["attr"] == "name":
        m = app.set_income(a["name"], new_name=a["value"])
    else:
        m = app.set_income(a["name"], amount=evaluate(a["value"]))
    return Result.ok(f"✓ income {a['name']} updated", m)


def h_income_del(app: MonayApp, a: Args) -> Result:
    m = app.delete_income(a["name"])
    return Result.ok(f"✓ income {a['name']} deleted", m)


# --- pockets --------------------------------------------------------------
def h_pocket_add(app: MonayApp, a: Args) -> Result:
    m = app.add_pocket(a["name"])
    return Result.ok(f"✓ pocket {a['name']} added", m)


def h_pocket_rename(app: MonayApp, a: Args) -> Result:
    m = app.rename_pocket(a["old"], a["new"])
    return Result.ok(f"✓ pocket {a['old']} → {a['new']}", m)


def h_pocket_del(app: MonayApp, a: Args) -> Result:
    m = app.delete_pocket(a["name"])
    return Result.ok(f"✓ pocket {a['name']} deleted", m)


def h_pocket_main(app: MonayApp, a: Args) -> Result:
    m = app.set_main_pocket(a["name"])
    return Result.ok(f"✓ {a['name']} is now the default pocket", m)


# --- months / nav / profiles ---------------------------------------------
def h_month(app: MonayApp, a: Args) -> Result:
    if a["key"] is None:
        key = app.view_open_month()
        return Result.info(f"viewing the open month {month_label(key)}")
    key, closed = app.view_month(a["key"])
    state = "🔒 closed — viewing history" if closed else "● open"
    return Result.info(f"viewing {month_label(key)} ({state})")


def h_close(app: MonayApp, a: Args) -> Result:
    nxt = app.close_active()
    return Result.ok(f"✓ closed — now in {month_label(nxt.key)}", nxt)


def h_goto(app: MonayApp, a: Args) -> Result:
    app.goto(a["tab"])
    return Result.info(f"→ {a['tab']}")


def h_expand(app: MonayApp, a: Args) -> Result:
    app.expand_section(a["section"])
    return Result.info(f"expanded {a['section']}")


def h_collapse(app: MonayApp, a: Args) -> Result:
    section = a["section"]
    if section:
        app.collapse_section(section)
        return Result.info(f"collapsed {section}")
    app.collapse_all()
    return Result.info("collapsed all sections")


def h_profile_add(app: MonayApp, a: Args) -> Result:
    p = app.create_profile(a["name"])
    return Result.info(f"✓ profile {p.name} created and selected")


def h_profile_switch(app: MonayApp, a: Args) -> Result:
    p = app.switch_profile(a["name"])
    return Result.info(f"✓ switched to {p.name}")


def h_profile_rename(app: MonayApp, a: Args) -> Result:
    app.rename_profile(a["name"])
    return Result.info(f"✓ profile renamed to {a['name']}")


def h_profile_del(app: MonayApp, a: Args) -> Result:
    app.delete_profile(a["name"])
    return Result.info(f"✓ profile {a['name']} deleted")


def h_quit(app: MonayApp, a: Args) -> Result:
    app.quit()
    return Result.info("bye")


# --- help (registry-generated) -------------------------------------------
def h_help(app: MonayApp, a: Args) -> Result:
    """Open the Docs tab (the man-style reference lives there, not the feedback
    line). An optional argument filters the Docs view to matching commands."""
    from .specs import REGISTRY

    # NOTE: validates against the module-level REGISTRY singleton, while the TUI
    # renders the Docs tab from its injected registry (`self._commands.specs()`).
    # Both are built from the same SPECS in production, so they match; a test that
    # injects a different registry would be the only way they could diverge.
    query = (a["command"] or "").strip().lower() or None
    if query and not any(s.name.startswith(query) for s in REGISTRY.specs()):
        return Result.error(f"no command matching {query!r}")
    app.show_docs(query)
    target = f"commands matching {query!r}" if query else "the command reference"
    return Result.info(f"showing {target} in the Docs tab →")


# --- close summary (confirmation prompt) ----------------------------------
def close_summary(app: MonayApp, a: Args) -> str:
    return app.close_summary()


def _del_summary(noun: str) -> SummaryFn:
    def summary(app: MonayApp, a: Args) -> str:
        target = a.get("name") or a.get("index")
        return f"Delete {noun} {target}?"

    return summary
