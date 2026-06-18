"""``MonthCloser`` — the close + rollover domain service (docs/DEVELOPING.md).

Closing a month finalizes its numbers, routes each section's REST, locks the
month forever, and **creates the next month**: the whole structure copied
forward (sections with kind/order/percent/routing, fields with BUDGET/MAX/pocket),
every field's CURRENT set to its final LEFT, and a single Leftovers income entry
holding every REST that routed "to income". It spans two months, so it's a
service rather than a method on the aggregate (docs/DEVELOPING.md).
"""

from __future__ import annotations

import calendar

from .entities import Field, Income, IncomeKind, Pocket, Section
from .errors import MonthClosedError
from .money import Money
from .month import Month, MonthState
from .values import RoutingKind


class MonthCloser:
    def close(self, month: Month) -> Month:
        """Close ``month`` (locking it) and return the new open month."""
        if month.is_closed:
            raise MonthClosedError(f"month {month.key} is already closed")
        month.assert_operable()  # invariant: post-% must sum to 100
        month.recompute()

        nxt = Month(
            profile_id=month.profile_id, key=month.key.next(), state=MonthState.OPEN
        )
        pockets = self._copy_pockets(month, nxt)
        sections = self._copy_sections(month, nxt, pockets)
        leftovers = self._route_rests(month, sections)
        nxt.incomes.append(
            Income(
                name=(
                    f"{calendar.month_name[month.key.month]} {month.key.year} Leftovers"
                ),
                amount=leftovers,
                kind=IncomeKind.LEFTOVER,
                position=0,
            )
        )

        month.state = MonthState.CLOSED
        nxt.recompute()
        return nxt

    # --- structure copy ---------------------------------------------------
    def _copy_pockets(self, month: Month, nxt: Month) -> dict[str, Pocket]:
        out: dict[str, Pocket] = {}
        for p in sorted(month.pockets, key=lambda p: p.position):
            new = Pocket(name=p.name, is_default=p.is_default, position=p.position)
            nxt.pockets.append(new)
            out[new.name] = new
        return out

    def _copy_sections(
        self, month: Month, nxt: Month, pockets: dict[str, Pocket]
    ) -> dict[str, Section]:
        out: dict[str, Section] = {}
        for s in sorted(month.sections, key=lambda s: s.position):
            new = Section(
                name=s.name,
                kind=s.kind,
                alloc_kind=s.alloc_kind,
                position=s.position,
                percentage=s.percentage,  # value objects are immutable — safe to share
                amount=s.amount,
                rest_routing=s.rest_routing,
            )
            for f in sorted(s.fields, key=lambda f: f.position):
                new.fields.append(
                    Field(
                        name=f.name,
                        budget=f.budget,
                        current=f.left,  # carry the final LEFT forward
                        cap=f.cap,
                        pocket=pockets[f.pocket.name],
                        position=f.position,
                    )
                )
            nxt.sections.append(new)
            out[new.name] = new
        return out

    # --- REST routing -----------------------------------------------------
    def _route_rests(self, month: Month, sections: dict[str, Section]) -> Money:
        """Send each REST to its target; return the total that routed to income."""
        leftovers = Money.zero()
        for s in month.sections:
            target = self._target(s, sections)
            if target is None:  # to income, or fallback when the target is gone
                leftovers = leftovers + s.rest
            else:
                target.carried_rest = target.carried_rest + s.rest
        return leftovers

    @staticmethod
    def _target(section: Section, sections: dict[str, Section]) -> Section | None:
        routing = section.rest_routing
        if routing.kind is RoutingKind.INCOME:
            return None
        if routing.kind is RoutingKind.SELF:
            return sections.get(section.name)
        return sections.get(routing.target)  # SECTION; None ⇒ fallback to income
