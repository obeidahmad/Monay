"""Phase 4 — REST routing in isolation: income / self / section + fallback.

Two POST sections A and B (50/50) over income 100, each with one inert field, so
each section's REST is a clean 50. We vary A's routing and assert where its REST
lands in the next month. B always routes to itself (a stable reference).
"""

import pytest

from monay.domain.closing import MonthCloser
from monay.domain.entities import (
    AllocKind,
    Field,
    Income,
    IncomeKind,
    Pocket,
    Section,
    SectionKind,
)
from monay.domain.errors import MonthClosedError, MonthNotBalancedError
from monay.domain.money import Money
from monay.domain.month import Month
from monay.domain.values import Cap, MonthKey, Percentage, RestRouting

INF = Cap.infinite()


def money(v: str) -> Money:
    return Money(v)


def month_with(a_routing: RestRouting, a_budget: str = "0") -> Month:
    m = Month(profile_id=1, key=MonthKey(2026, 7))
    main = Pocket("Main", is_default=True)
    m.pockets = [main]
    m.incomes = [Income("Pay", money("100"))]
    a = Section(
        "A",
        SectionKind.POST,
        AllocKind.PCT,
        0,
        percentage=Percentage(50),
        rest_routing=a_routing,
    )
    a.fields = [Field("fa", money(a_budget), money("0"), INF, main, 0)]
    b = Section(
        "B",
        SectionKind.POST,
        AllocKind.PCT,
        1,
        percentage=Percentage(50),
        rest_routing=RestRouting.to_self(),
    )
    b.fields = [Field("fb", money("0"), money("0"), INF, main, 0)]
    m.sections = [a, b]
    m.recompute()
    return m


def leftovers_of(month: Month) -> Money:
    return next(i.amount for i in month.incomes if i.kind is IncomeKind.LEFTOVER)


def test_route_to_income():
    july = MonthCloser().close(month_with(RestRouting.to_income()))
    assert leftovers_of(july) == money("50")  # A's REST went to income
    assert july.section("A").carried_rest == money("0")
    assert july.section("B").carried_rest == money("50")  # B's own to_self


def test_route_to_self():
    july = MonthCloser().close(month_with(RestRouting.to_self()))
    assert july.section("A").carried_rest == money("50")
    assert july.section("B").carried_rest == money("50")
    assert leftovers_of(july) == money("0")


def test_route_to_other_section():
    july = MonthCloser().close(month_with(RestRouting.to_section("B")))
    assert july.section("B").carried_rest == money("100")  # A's 50 + B's own 50
    assert july.section("A").carried_rest == money("0")
    assert leftovers_of(july) == money("0")


def test_route_to_missing_section_falls_back_to_income():
    july = MonthCloser().close(month_with(RestRouting.to_section("Ghost")))
    assert leftovers_of(july) == money("50")  # Ghost doesn't exist next month
    assert july.section("B").carried_rest == money("50")


def test_negative_rest_routes_the_same_way():
    # A field budget 100 over AVAILABLE 50 → A REST = -50, routed to self.
    july = MonthCloser().close(month_with(RestRouting.to_self(), a_budget="100"))
    assert july.section("A").carried_rest == money("-50")


def test_cannot_close_unbalanced():
    m = Month(profile_id=1, key=MonthKey(2026, 7))
    m.pockets = [Pocket("Main", is_default=True)]
    m.incomes = [Income("Pay", money("100"))]
    m.sections = [
        Section(
            "Only",
            SectionKind.POST,
            AllocKind.PCT,
            0,
            percentage=Percentage(90),
            rest_routing=RestRouting.to_income(),
        )
    ]
    m.recompute()
    with pytest.raises(MonthNotBalancedError):
        MonthCloser().close(m)


def test_cannot_close_twice():
    closer = MonthCloser()
    june = month_with(RestRouting.to_self())
    closer.close(june)
    with pytest.raises(MonthClosedError):
        closer.close(june)
