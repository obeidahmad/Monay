"""Domain → JSON view models for the web UI (docs/DEVELOPING.md).

Everything the React app renders comes from here, already computed: money as
2-decimal strings (the cosmetic view of the 4dp truth — the UI never does money
math), the Budget tab's headline figures, the REST routing labels, and each
pocket's field breakdown. Keeping this in Python keeps the engine the single
source of truth.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from monay.app.services import ClosePreview, MonayApp, MonthSummary, month_label
from monay.domain.entities import (
    AllocKind,
    Field,
    Pocket,
    Profile,
    Section,
    SectionKind,
)
from monay.domain.errors import MonayError
from monay.domain.money import Money
from monay.domain.month import Month

JSON = dict[str, Any]


def money(m: Money) -> str:
    """The cosmetic 2dp view, e.g. ``"1500.00"`` / ``"-17.06"``."""
    return str(m.display())


def pct(value: Decimal) -> str:
    return format(value.normalize(), "f")


def state(service: MonayApp) -> JSON:
    """The whole UI state: profile, the month being viewed, and its history."""
    profiles = service.list_profiles()
    out: JSON = {
        "profile": _profile(service),
        "profiles": [_profile_item(p) for p in profiles],
        "viewing": None,
        "month": None,
        "history": [],
    }
    if service.profile_id is None:
        return out
    try:
        month = service.active_month()
        first = service.is_first_month()
        summaries = service.month_summaries()
    except MonayError:
        return out
    out["viewing"] = {
        "key": str(month.key),
        "label": month_label(month.key),
        "closed": month.is_closed,
        "first_month": first,
    }
    out["month"] = month_view(month)
    out["history"] = [_summary(s) for s in summaries]
    return out


def month_view(month: Month) -> JSON:
    sections = sorted(month.sections, key=lambda s: s.position)
    section_of = {id(f): s.name for s in sections for f in s.fields}
    return {
        "key": str(month.key),
        "label": month_label(month.key),
        "state": month.state.value,
        "total_income": money(month.total_income),
        "fresh_income": money(month.fresh_income),
        "incomes": [
            {"name": i.name, "amount": money(i.amount), "kind": i.kind.value}
            for i in sorted(month.incomes, key=lambda i: i.position)
        ],
        "sections": [_section(s, i) for i, s in enumerate(sections)],
        "pockets": [
            _pocket(p, month, sections)
            for p in sorted(month.pockets, key=lambda p: p.position)
        ],
        "transactions": [
            {
                "index": i,
                "day": int(t.day),
                "section": section_of.get(id(t.field), "?"),
                "field": t.field.name,
                "amount": money(t.amount),
                "description": t.description,
            }
            for i, t in enumerate(month.transactions, start=1)
        ],
        "transfers": [
            {
                "day": int(t.day),
                "from_section": section_of.get(id(t.from_field), "?"),
                "from_field": t.from_field.name,
                "to_section": section_of.get(id(t.to_field), "?"),
                "to_field": t.to_field.name,
                "amount": money(t.amount),
                "note": t.note,
            }
            for t in month.transfers
        ],
        "summary": budget_summary(month),
        "warnings": list(month.warnings),
    }


def budget_summary(month: Month) -> JSON:
    """The Budget tab headline: income · post pool · Σ% balance check.

    The pool POST sections split is income minus the TAX/PRE shares taken off
    the top. It uses each share (available − carried_rest), not available
    itself: carried_rest is REST routed in from last month, not a cut of this
    income.
    """

    def share(s: Section) -> Money:
        return s.available - s.carried_rest

    tax_total = sum(
        (share(s) for s in month.sections if s.kind is SectionKind.TAX), Money.zero()
    )
    pre_total = sum(
        (share(s) for s in month.sections if s.kind is SectionKind.PRE), Money.zero()
    )
    post = [s for s in month.sections if s.kind is SectionKind.POST]
    pct_total = sum(
        (s.percentage.value for s in post if s.percentage is not None), Decimal(0)
    )
    return {
        "total_income": money(month.total_income),
        "tax_total": money(tax_total),
        "pre_total": money(pre_total),
        "post_pool": money(month.total_income - tax_total - pre_total),
        "has_post": bool(post),
        "pct_total": pct(pct_total),
        "balanced": not post or pct_total == Decimal(100),
    }


def close_preview(p: ClosePreview) -> JSON:
    return {
        "label": month_label(p.key),
        "next_label": month_label(p.next_key),
        "leftovers": money(p.leftovers),
        "carries": [{"section": n, "rest": money(r)} for n, r in p.carries],
    }


def routing_label(s: Section) -> str:
    """Where this section's REST goes at month close."""
    routing = s.rest_routing
    if routing.is_income:
        return "→ income"
    if routing.is_self:
        return "→ carries over"
    return f"→ {routing.target}"


def share_label(s: Section) -> str:
    """``post · 50%`` / ``pre · 500.00`` — the kind and the slice it takes."""
    if s.alloc_kind is AllocKind.PCT:
        assert s.percentage is not None
        return f"{s.kind.value} · {pct(s.percentage.value)}%"
    assert s.amount is not None
    return f"{s.kind.value} · {s.amount.display():,.2f}"


# --- pieces -----------------------------------------------------------------
def _profile(service: MonayApp) -> JSON | None:
    if service.profile_id is None:
        return None
    return {"id": service.profile_id, "name": service.profile_name}


def _profile_item(p: Profile) -> JSON:
    return {"id": p.id, "name": p.name}


def _summary(s: MonthSummary) -> JSON:
    return {
        "key": str(s.key),
        "label": month_label(s.key),
        "state": s.state.value,
        "income": money(s.income),
        "spent": money(s.spent),
        "leftovers": money(s.leftovers),
    }


def _section(s: Section, index: int) -> JSON:
    return {
        "name": s.name,
        "kind": s.kind.value,
        "alloc_kind": s.alloc_kind.value,
        "percentage": pct(s.percentage.value) if s.percentage is not None else None,
        "amount": money(s.amount) if s.amount is not None else None,
        "share_label": share_label(s),
        "position": s.position,
        "accent": index % 8,
        "routing": {"kind": s.rest_routing.kind.value, "target": s.rest_routing.target},
        "routing_label": routing_label(s),
        "available": money(s.available),
        "consumed": money(s.consumed),
        "rest": money(s.rest),
        "budget_left": money(s.budget_left),
        "carried_rest": money(s.carried_rest),
        "fields": [_field(f) for f in sorted(s.fields, key=lambda f: f.position)],
    }


def _field(f: Field) -> JSON:
    return {
        "name": f.name,
        "budget": money(f.budget),
        "budget_pct": pct(f.budget_pct.value) if f.budget_pct is not None else None,
        "current": money(f.current),
        "paid": money(f.paid),
        "left": money(f.left),
        "consumed": money(f.consumed),
        "cap": money(f.cap.limit) if f.cap.limit is not None else None,
        "pocket": f.pocket.name,
    }


def _pocket(p: Pocket, month: Month, sections: list[Section]) -> JSON:
    fields = [
        {"section": s.name, "field": f.name, "left": money(f.left)}
        for s in sections
        for f in sorted(s.fields, key=lambda f: f.position)
        if f.pocket is p
    ]
    rests = sum((s.rest for s in month.sections), Money.zero())
    return {
        "name": p.name,
        "is_default": p.is_default,
        "counter": money(p.counter),
        "fields": fields,
        # The default pocket also holds the live section RESTs.
        "rests": money(rests) if p.is_default else None,
    }
