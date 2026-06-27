"""TAX sections: a % off FRESH income only, taken before PRE/POST.

Leftovers were already taxed when they first arrived, so a TAX section must
allocate against non-leftover income only (docs/DEVELOPING.md, issue #28). Every
value here is hand-verifiable.
"""

import pytest

from monay.data.db import make_engine, run_migrations
from monay.data.unit_of_work import SqlAlchemyUnitOfWork
from monay.domain.entities import (
    AllocKind,
    Income,
    IncomeKind,
    Pocket,
    Profile,
    Section,
    SectionKind,
)
from monay.domain.errors import ValidationError
from monay.domain.money import Money
from monay.domain.month import Month
from monay.domain.values import MonthKey, Percentage, RestRouting


def money(v: str) -> Money:
    return Money(v)


def _section(name, kind, position, *, percentage=None, amount=None) -> Section:
    return Section(
        name=name,
        kind=kind,
        alloc_kind=AllocKind.AMOUNT if amount is not None else AllocKind.PCT,
        position=position,
        percentage=percentage,
        amount=amount,
        rest_routing=RestRouting.to_income(),
    )


def _month(*sections: Section, leftover: str = "200", fresh: str = "1000") -> Month:
    """A month with one fresh income + one leftover, plus the given sections."""
    m = Month(profile_id=1, key=MonthKey(2025, 1))
    m.pockets = [Pocket("Main", is_default=True)]
    m.incomes = [
        Income("Salary", money(fresh), IncomeKind.MANUAL, 0),
        Income("Leftovers", money(leftover), IncomeKind.LEFTOVER, 1),
    ]
    m.sections = list(sections)
    m.recompute()
    return m


# --- the fresh-income base ------------------------------------------------
def test_fresh_income_excludes_leftovers():
    m = _month(_section("Spend", SectionKind.POST, 0, percentage=Percentage(100)))
    assert m.total_income == money("1200")
    assert m.fresh_income == money("1000")
    assert m.fresh_income < m.total_income


def test_tax_share_is_pct_of_fresh_not_total():
    # 10% of fresh 1000 = 100 (NOT 120, which would be 10% of total 1200).
    tax = _section("Tax", SectionKind.TAX, 0, percentage=Percentage(10))
    m = _month(tax)
    assert m.section("Tax").available == money("100")


def test_tax_taken_off_the_top_leftovers_still_flow():
    # Tax 10% of fresh -> 100 off the top; the POST pool is the remaining 1100,
    # which still includes the 200 leftover. Zero-based: it lands in the pocket.
    tax = _section("Tax", SectionKind.TAX, 0, percentage=Percentage(10))
    spend = _section("Spend", SectionKind.POST, 1, percentage=Percentage(100))
    m = _month(tax, spend)
    # 1100 = 900 (fresh net of tax) + 200 leftover: the leftover stays spendable.
    assert m.section("Spend").available == money("1100")
    # Nothing is consumed, so every dollar (tax + spend RESTs) is conserved in
    # the default pocket — zero-based, leftover included.
    assert m.pocket("Main").counter == m.total_income


def test_multiple_taxes_share_the_same_fresh_base():
    # 10% and 5% each of fresh 1000 -> 100 and 50; they don't compound
    # (5% of 900 would be 45). Total 150 off the top.
    t1 = _section("Income tax", SectionKind.TAX, 0, percentage=Percentage(10))
    t2 = _section("Social", SectionKind.TAX, 1, percentage=Percentage(5))
    spend = _section("Spend", SectionKind.POST, 2, percentage=Percentage(100))
    m = _month(t1, t2, spend)
    assert m.section("Income tax").available == money("100")
    assert m.section("Social").available == money("50")
    assert m.section("Spend").available == money("1050")


def test_tax_runs_before_pre():
    # Tax 10% of fresh 1000 = 100; PRE 50% of the remaining 1100 = 550.
    tax = _section("Tax", SectionKind.TAX, 0, percentage=Percentage(10))
    pre = _section("Bills", SectionKind.PRE, 1, percentage=Percentage(50))
    m = _month(tax, pre)
    assert m.section("Tax").available == money("100")
    assert m.section("Bills").available == money("550")


# --- %-only invariant -----------------------------------------------------
def test_tax_section_rejects_fixed_amount_on_construction():
    with pytest.raises(ValidationError):
        _section("Tax", SectionKind.TAX, 0, amount=money("100"))


def test_edit_section_rejects_amount_on_tax():
    m = _month(_section("Tax", SectionKind.TAX, 0, percentage=Percentage(10)))
    with pytest.raises(ValidationError):
        m.edit_section("Tax", amount=money("100"))


# --- persistence round-trip -----------------------------------------------
def test_tax_section_survives_save_and_load():
    engine = make_engine("sqlite://")
    run_migrations(engine)

    month = _month(_section("Tax", SectionKind.TAX, 0, percentage=Percentage(10)))
    with SqlAlchemyUnitOfWork(engine) as uow:
        prof = uow.profiles.add(Profile(name="Me"))
        month.profile_id = prof.id
        uow.months.add(month)
        uow.commit()
        pid = prof.id

    with SqlAlchemyUnitOfWork(engine) as uow:
        loaded = uow.months.get(pid, MonthKey(2025, 1))

    assert loaded is not None
    tax = loaded.section("Tax")
    assert tax.kind is SectionKind.TAX
    assert tax.available == money("100")
