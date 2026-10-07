"""Domain objects → response models.

The one place that decides how the engine's values look on the wire. Positions
come from the same ``ordered_*`` helpers the service resolves them with
(``app/budgeting.py``), so an ``index`` read here is the one a change accepts.
"""

from __future__ import annotations

from decimal import Decimal

from monay.app.budgeting import (
    Changed,
    ClosePreview,
    MonthView,
    ProfileInfo,
    ordered_fields,
    ordered_incomes,
    ordered_pockets,
    ordered_sections,
    post_percentage_total,
    post_pool,
    unallocated_income,
)
from monay.app.services import MonthSummary, month_label
from monay.domain.entities import AllocKind, Section
from monay.domain.money import Money
from monay.domain.values import RestRouting

from .schemas import (
    AllocationOut,
    ChangeOut,
    ClosePreviewOut,
    FieldOut,
    FieldRefOut,
    IncomeOut,
    MonthOut,
    MonthSummaryOut,
    PocketHoldingOut,
    PocketOut,
    ProfileOut,
    RestCarryOut,
    RestRoutingModel,
    SectionOut,
    TransactionOut,
    TransferOut,
)


def money(value: Money) -> str:
    """The stored 4dp value, e.g. ``"332.9400"`` — the client does the 2dp view."""
    return str(value.amount)


def percent(value: Decimal) -> str:
    """A percentage without trailing zeros: ``50``, ``1.5`` (never ``5E+1``)."""
    return format(value.normalize(), "f")


def change_out(changed: Changed) -> ChangeOut:
    return ChangeOut(month=month_out(changed.view), undo_token=changed.undo_token)


def profile_out(info: ProfileInfo) -> ProfileOut:
    return ProfileOut(
        id=info.id,
        name=info.name,
        created_at=info.created_at,
        open_month=None if info.open_month is None else str(info.open_month),
    )


def summary_out(summary: MonthSummary) -> MonthSummaryOut:
    return MonthSummaryOut(
        key=str(summary.key),
        label=month_label(summary.key),
        state=summary.state,
        income=money(summary.income),
        spent=money(summary.spent),
        leftovers=money(summary.leftovers),
    )


def close_preview_out(preview: ClosePreview) -> ClosePreviewOut:
    return ClosePreviewOut(
        key=str(preview.key),
        label=month_label(preview.key),
        next_key=str(preview.next_key),
        next_label=month_label(preview.next_key),
        income=money(preview.income),
        spent=money(preview.spent),
        leftovers=money(preview.leftovers),
        carries=[
            RestCarryOut(section=c.section, amount=money(c.amount))
            for c in preview.carries
        ],
    )


def month_out(view: MonthView) -> MonthOut:
    month = view.month
    sections = ordered_sections(month)
    pockets = ordered_pockets(month)
    pocket_index = {id(p): i for i, p in enumerate(pockets)}

    where: dict[int, FieldRefOut] = {}  # id(field) → how a client addresses it
    holdings: dict[int, list[PocketHoldingOut]] = {id(p): [] for p in pockets}
    section_models: list[SectionOut] = []
    for si, s in enumerate(sections):
        field_models: list[FieldOut] = []
        for fi, f in enumerate(ordered_fields(s)):
            where[id(f)] = FieldRefOut(
                section_index=si, field_index=fi, section=s.name, field=f.name
            )
            holdings[id(f.pocket)].append(
                PocketHoldingOut(section=s.name, field=f.name, left=money(f.left))
            )
            field_models.append(
                FieldOut(
                    index=fi,
                    name=f.name,
                    budget=money(f.budget),
                    budget_pct=(
                        None if f.budget_pct is None else percent(f.budget_pct.value)
                    ),
                    current=money(f.current),
                    paid=money(f.paid),
                    left=money(f.left),
                    consumed=money(f.consumed),
                    max=None if f.cap.limit is None else money(f.cap.limit),
                    pocket=f.pocket.name,
                    pocket_index=pocket_index[id(f.pocket)],
                )
            )
        section_models.append(
            SectionOut(
                index=si,
                name=s.name,
                kind=s.kind,
                allocation=_allocation(s),
                rest_routing=_routing(s.rest_routing),
                carried_rest=money(s.carried_rest),
                available=money(s.available),
                consumed=money(s.consumed),
                rest=money(s.rest),
                budget_left=money(s.budget_left),
                fields=field_models,
            )
        )

    rests = sum((s.rest for s in sections), Money.zero())
    unallocated = unallocated_income(month)
    spent = sum((f.paid for s in sections for f in s.fields), Money.zero())
    pct_total = post_percentage_total(month)

    return MonthOut(
        key=str(month.key),
        label=month_label(month.key),
        state=month.state,
        is_first=view.is_first,
        revision=view.revision,
        total_income=money(month.total_income),
        fresh_income=money(month.fresh_income),
        post_pool=money(post_pool(month)),
        post_pct_total=None if pct_total is None else percent(pct_total),
        unallocated=money(unallocated),
        spent=money(spent),
        incomes=[
            IncomeOut(index=i, name=inc.name, amount=money(inc.amount), kind=inc.kind)
            for i, inc in enumerate(ordered_incomes(month))
        ],
        sections=section_models,
        pockets=[
            PocketOut(
                index=i,
                name=p.name,
                is_default=p.is_default,
                counter=money(p.counter),
                holdings=holdings[id(p)],
                # Only the default pocket holds section RESTs and income that no
                # section has claimed (Month._recompute_pockets).
                rests=money(rests if p.is_default else Money.zero()),
                unallocated=money(unallocated if p.is_default else Money.zero()),
            )
            for i, p in enumerate(pockets)
        ],
        transactions=[
            TransactionOut(
                number=n,
                day=int(tx.day),
                field=where[id(tx.field)],
                amount=money(tx.amount),
                expression=tx.amount_expr,
                description=tx.description,
            )
            for n, tx in enumerate(month.transactions, start=1)
        ],
        transfers=[
            TransferOut(
                number=n,
                day=int(t.day),
                from_field=where[id(t.from_field)],
                to_field=where[id(t.to_field)],
                amount=money(t.amount),
                note=t.note,
            )
            for n, t in enumerate(month.transfers, start=1)
        ],
    )


def _allocation(section: Section) -> AllocationOut:
    # alloc_kind pins which of percentage/amount is set (Section's invariant).
    if section.alloc_kind is AllocKind.PCT:
        assert section.percentage is not None
        return AllocationOut(type="percent", value=percent(section.percentage.value))
    assert section.amount is not None
    return AllocationOut(type="amount", value=money(section.amount))


def _routing(routing: RestRouting) -> RestRoutingModel:
    return RestRoutingModel(kind=routing.kind, target=routing.target)
