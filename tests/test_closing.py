"""Closing the sample month into the next: rollover, routing, and the lock."""

import pytest

from monay.domain.closing import MonthCloser
from monay.domain.entities import IncomeKind
from monay.domain.errors import MonthClosed
from monay.domain.money import Money
from monay.domain.month import MonthState
from monay.domain.values import MonthKey
from tests.fixtures.sample_budget import build_sample


def M(v: str) -> Money:
    return Money(v)


@pytest.fixture
def closed():
    month = build_sample()
    nxt = MonthCloser().close(month)
    return month, nxt


def test_month_is_locked(closed):
    month, _ = closed
    assert month.is_closed
    with pytest.raises(MonthClosed):
        month.add_income("X", M("1"))


def test_next_month_identity(closed):
    month, nxt = closed
    assert nxt.key == MonthKey(2025, 2)
    assert nxt.state is MonthState.OPEN
    assert nxt.profile_id == month.profile_id


def test_structure_copied(closed):
    month, nxt = closed
    order = lambda sections: [s.name for s in sorted(sections, key=lambda s: s.position)]
    assert order(nxt.sections) == order(month.sections)
    for s in month.sections:
        ns = nxt.section(s.name)
        assert ns.kind == s.kind
        assert ns.percentage == s.percentage
        assert ns.rest_routing == s.rest_routing


def test_currents_carry_final_left(closed):
    """The keystone rollover assertion: next month's CURRENT == this month's LEFT."""
    month, nxt = closed
    for s in month.sections:
        for f in s.fields:
            assert nxt.field(s.name, f.name).current == f.left, f"{s.name}/{f.name}"


def test_budgets_caps_pockets_copied(closed):
    month, nxt = closed
    for s in month.sections:
        for f in s.fields:
            nf = nxt.field(s.name, f.name)
            assert nf.budget == f.budget
            assert nf.cap == f.cap
            assert nf.pocket.name == f.pocket.name


def test_leftovers_entry(closed):
    # Needs REST 350 + Wants REST 300 (both route to income); Bills/Savings route to self.
    _, nxt = closed
    leftovers = [i for i in nxt.incomes if i.kind is IncomeKind.LEFTOVER]
    assert len(leftovers) == 1
    assert leftovers[0].amount == M("650")
    assert "Leftovers" in leftovers[0].name


def test_only_leftovers_income_carried(closed):
    _, nxt = closed
    assert len(nxt.incomes) == 1
    assert nxt.total_income == M("650")


def test_rest_routing_carried(closed):
    _, nxt = closed
    assert nxt.section("Savings").carried_rest == M("60")  # to_self, REST 60
    assert nxt.section("Bills").carried_rest == M("0")      # to_self, REST 0
    assert nxt.section("Needs").carried_rest == M("0")      # routed to income
    assert nxt.section("Wants").carried_rest == M("0")      # routed to income


def test_pockets_copied(closed):
    _, nxt = closed
    assert {p.name for p in nxt.pockets} == {"Main", "Bank", "Broker"}
    assert nxt.pocket("Main").is_default