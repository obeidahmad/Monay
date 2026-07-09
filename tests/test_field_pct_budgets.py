"""Percentage-based field budgets: resolution math + the budget mutators.

A %-field's BUDGET = pct × max(AVAILABLE − Σ fixed budgets in the section, 0),
resolved on every recompute (docs/DEVELOPING.md). Small hand-built months, no
database.
"""

import pytest

from monay.domain.entities import (
    AllocKind,
    Field,
    Income,
    IncomeKind,
    Pocket,
    Section,
    SectionKind,
)
from monay.domain.errors import ValidationError
from monay.domain.money import Money
from monay.domain.month import Month
from monay.domain.values import Cap, MonthKey, Percentage, RestRouting

INF = Cap.infinite()


def money(v: str) -> Money:
    return Money(v)


def make_month(income: str = "500") -> Month:
    """A month with one default pocket and a single 100% post section 'Save'."""
    m = Month(profile_id=1, key=MonthKey(2025, 1))
    m.pockets = [Pocket("Main", is_default=True, position=0)]
    if income != "0":
        m.incomes = [Income("Pay", money(income), IncomeKind.MANUAL, 0)]
    m.sections = [
        Section(
            name="Save",
            kind=SectionKind.POST,
            alloc_kind=AllocKind.PCT,
            percentage=Percentage(100),
            rest_routing=RestRouting.to_self(),
        )
    ]
    return m


def add(m: Month, name: str, *, budget="0", pct=None, current="0", cap=INF) -> Field:
    s = m.section("Save")
    f = Field(
        name,
        money(budget),
        money(current),
        cap,
        m.pockets[0],
        position=len(s.fields),
        budget_pct=None if pct is None else Percentage(pct),
    )
    s.fields.append(f)
    return f


# --- resolution math -------------------------------------------------------
def test_mixed_fixed_and_pct():
    m = make_month("500")
    add(m, "Fixed", budget="300")
    emergency = add(m, "Emergency", pct=50)
    m.recompute()
    assert emergency.budget == money("100")  # 50% of (500 - 300)
    assert m.section("Save").budget_left == money("100")


def test_pure_pct_section():
    m = make_month("500")
    a = add(m, "A", pct=60)
    b = add(m, "B", pct=40)
    m.recompute()
    assert (a.budget, b.budget) == (money("300"), money("200"))
    assert m.section("Save").budget_left == money("0")


def test_order_independent():
    m = make_month("500")
    emergency = add(m, "Emergency", pct=50)  # %-field placed *before* the fixed one
    add(m, "Fixed", budget="300")
    m.recompute()
    assert emergency.budget == money("100")


def test_over_100_percent_allowed():
    m = make_month("500")
    a = add(m, "A", pct=80)
    b = add(m, "B", pct=40)
    m.recompute()
    assert (a.budget, b.budget) == (money("400"), money("200"))
    assert m.section("Save").budget_left == money("-100")  # visible, not an error


def test_negative_remainder_clamps_to_zero():
    m = make_month("500")
    add(m, "Fixed", budget="600")
    emergency = add(m, "Emergency", pct=50)
    m.recompute()
    assert emergency.budget == money("0")
    assert m.section("Save").budget_left == money("-100")


def test_negative_available_resolves_pct_to_zero():
    # A PRE amount larger than income drives the POST section's share negative.
    m = make_month("1000")
    m.sections.insert(
        0,
        Section(
            name="Bills",
            kind=SectionKind.PRE,
            alloc_kind=AllocKind.AMOUNT,
            amount=money("1500"),
            rest_routing=RestRouting.to_income(),
        ),
    )
    fixed = add(m, "Fixed", budget="100")
    emergency = add(m, "Emergency", pct=50)
    m.recompute()
    assert m.section("Save").available == money("-500")
    assert emergency.budget == money("0")
    assert fixed.budget == money("100")  # fixed budgets are never touched
    assert any("REST is negative" in w for w in m.warnings)


def test_negative_carried_rest_resolves_pct_to_zero():
    m = make_month("0")
    m.section("Save").carried_rest = money("-200")
    emergency = add(m, "Emergency", pct=50)
    m.recompute()
    assert m.section("Save").available == money("-200")
    assert emergency.budget == money("0")


def test_rounding_residue_lands_in_budget_left():
    m = make_month("100")
    fields = [add(m, n, pct="33.33") for n in ("A", "B", "C")]
    m.recompute()
    assert all(f.budget == money("33.33") for f in fields)
    assert m.section("Save").budget_left == money("0.01")


def test_recompute_idempotent():
    m = make_month("500")
    add(m, "Fixed", budget="300")
    emergency = add(m, "Emergency", pct=50)
    m.recompute()
    m.recompute()
    assert emergency.budget == money("100")


def test_cap_clamps_resolved_budget():
    m = make_month("500")
    emergency = add(m, "Emergency", pct=50, cap=Cap.finite("100"))
    m.recompute()
    assert emergency.budget == money("250")
    assert emergency.left == money("100")  # min(0 + 250 - 0, 100)


# --- mutators ---------------------------------------------------------------
def test_add_field_with_percentage():
    m = make_month("500")
    f = m.add_field("Save", "Emergency", Percentage(50), INF, "Main")
    assert f.budget_pct == Percentage(50)
    assert f.budget == money("250")  # resolved by the mutator's recompute


def test_set_field_budget_switches_kinds_both_ways():
    m = make_month("500")
    m.add_field("Save", "Emergency", money("200"), INF, "Main")

    m.set_field_budget("Save", "Emergency", Percentage(50))
    f = m.field("Save", "Emergency")
    assert f.budget_pct == Percentage(50)
    assert f.budget == money("250")

    m.set_field_budget("Save", "Emergency", money("200"))
    assert f.budget_pct is None
    assert f.budget == money("200")


def test_percentage_over_100_rejected():
    with pytest.raises(ValidationError):
        Percentage("150")
