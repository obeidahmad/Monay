"""Income on the Budget tab, and the reserved ``income`` name (#32).

The web UI shows income as a distinct row above the real sections (carrying total
income, expandable to its entries), even before any section exists. The name
``income`` is reserved so no real section can shadow it.
"""

import pytest

from monay.domain.entities import Income, IncomeKind
from monay.domain.errors import ValidationError
from monay.domain.money import Money
from monay.domain.month import Month
from monay.domain.values import MonthKey, Percentage
from monay.web.presenter import month_view
from tests.fixtures.sample_budget import build_sample


def test_month_view_lists_income_entries():
    m = build_sample()
    m.recompute()
    view = month_view(m)
    assert view["total_income"] == "2000.00"
    assert view["incomes"] == [
        {"name": "Salary", "amount": "2000.00", "kind": "manual"}
    ]


def test_income_shows_before_any_section_exists():
    m = Month(profile_id=1, key=MonthKey(2025, 1))
    m.incomes = [Income("Salary", Money("1000"), IncomeKind.MANUAL, 0)]
    m.recompute()
    view = month_view(m)
    assert view["sections"] == []
    assert view["total_income"] == "1000.00"


def test_add_section_rejects_the_reserved_income_name():
    m = build_sample()
    with pytest.raises(ValidationError):
        m.add_section("income", "post", percentage=Percentage(50))
    with pytest.raises(ValidationError):  # case-insensitive
        m.add_section("Income", "post", percentage=Percentage(50))


def test_rename_section_to_income_is_rejected():
    m = build_sample()
    with pytest.raises(ValidationError):
        m.edit_section("Needs", new_name="income")
