"""The engine's keystone test: recompute the sample budget and check every value.

Numbers are hand-verifiable from the field/section formulas in
docs/DEVELOPING.md. If recompute regresses, these break.
"""

import pytest

from monay.domain.money import Money
from tests.fixtures.sample_budget import build_sample, field, pocket, section


def M(v: str) -> Money:
    return Money(v)


@pytest.fixture
def sample():
    m = build_sample()
    m.recompute()
    return m


# --- field LEFT = min(CURRENT + BUDGET - PAID, MAX) ----------------------
EXPECTED_LEFT = {
    ("Bills", "Utilities"): "50",      # 0 + 500 - 450
    ("Needs", "Groceries"): "350",     # 100 + 300 - 50
    ("Needs", "Transport"): "50",      # min(50 + 50 - 0, 50) -> clamped
    ("Needs", "Dining"): "-150",       # 0 + 100 - 250 -> negative carry
    ("Wants", "Clothes"): "150",
    ("Wants", "Gadgets"): "200",
    ("Savings", "Emergency"): "1100",  # 1000 + 100
    ("Savings", "Investments"): "640", # 500 + 140
}

# --- field CONSUMED = LEFT - CURRENT + PAID ------------------------------
EXPECTED_CONSUMED = {
    ("Bills", "Utilities"): "500",
    ("Needs", "Groceries"): "300",
    ("Needs", "Transport"): "0",       # pot was already full; budget not taken
    ("Needs", "Dining"): "100",        # only BUDGET, never the overspend
    ("Wants", "Clothes"): "150",
    ("Wants", "Gadgets"): "0",
    ("Savings", "Emergency"): "100",
    ("Savings", "Investments"): "140",
}

EXPECTED_PAID = {
    ("Bills", "Utilities"): "450",
    ("Needs", "Groceries"): "50",      # 30 + (10+10)
    ("Needs", "Dining"): "250",
}


@pytest.mark.parametrize("ref,expected", EXPECTED_LEFT.items())
def test_field_left(sample, ref, expected):
    assert field(sample, *ref).left == M(expected)


@pytest.mark.parametrize("ref,expected", EXPECTED_CONSUMED.items())
def test_field_consumed(sample, ref, expected):
    assert field(sample, *ref).consumed == M(expected)


def test_field_paid(sample):
    for s in sample.sections:
        for f in s.fields:
            assert f.paid == M(EXPECTED_PAID.get((s.name, f.name), "0")), f"{s.name}/{f.name}"


def test_total_income(sample):
    assert sample.total_income == M("2000")


def test_section_available(sample):
    assert section(sample, "Bills").available == M("500")    # fixed pre amount
    assert section(sample, "Needs").available == M("750")    # 50% of 1500
    assert section(sample, "Wants").available == M("450")    # 30% of 1500
    assert section(sample, "Savings").available == M("300")  # 20% of 1500


def test_section_rest(sample):
    assert section(sample, "Bills").rest == M("0")
    assert section(sample, "Needs").rest == M("350")
    assert section(sample, "Wants").rest == M("300")
    assert section(sample, "Savings").rest == M("60")


def test_needs_budget_left(sample):
    # AVAILABLE 750 - Σ budgets (300 + 50 + 100)
    assert section(sample, "Needs").budget_left == M("300")


def test_pocket_counters(sample):
    assert pocket(sample, "Bank").counter == field(sample, "Savings", "Emergency").left
    assert pocket(sample, "Broker").counter == field(sample, "Savings", "Investments").left

    main_left = sum(
        (f.left for s in sample.sections for f in s.fields if f.pocket.name == "Main"),
        Money.zero(),
    )
    rests = sum((s.rest for s in sample.sections), Money.zero())
    assert pocket(sample, "Main").counter == main_left + rests  # 650 + 710 = 1360


def test_no_warnings(sample):
    # Post percentages sum to 100 and no section REST is negative.
    assert sample.warnings == []
