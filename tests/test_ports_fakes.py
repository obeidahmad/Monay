"""Phase 5 — the DI seam: the fakes conform to the ports and round-trip a Month."""

from datetime import date

import pytest

from monay.domain.entities import Profile
from monay.domain.money import Money
from monay.domain.ports import (
    Clock,
    MonthRepository,
    ProfileRepository,
    UnitOfWork,
)
from monay.domain.values import MonthKey
from tests.fakes import (
    FakeMonthRepository,
    FakeProfileRepository,
    FakeUnitOfWork,
    FixedClock,
)
from tests.fixtures.sample_budget import build_sample


def test_fakes_satisfy_the_ports():
    assert isinstance(FixedClock(date(2026, 6, 13)), Clock)
    assert isinstance(FakeMonthRepository(), MonthRepository)
    assert isinstance(FakeProfileRepository(), ProfileRepository)
    assert isinstance(FakeUnitOfWork(), UnitOfWork)


def test_fixed_clock():
    assert FixedClock(date(2026, 6, 13)).today() == date(2026, 6, 13)


def test_fake_uow_roundtrips_a_month():
    month = build_sample()
    month.recompute()

    uow = FakeUnitOfWork()
    with uow:
        uow.months.add(month)
        uow.commit()
    assert uow.committed

    with uow:
        loaded = uow.months.get(month.profile_id, month.key)

    assert loaded is not None
    assert loaded is not month  # came back as a fresh object graph
    loaded.recompute()
    assert loaded.total_income == month.total_income
    assert (
        loaded.field("Needs", "Groceries").left
        == month.field("Needs", "Groceries").left
    )
    assert loaded.section("Needs").rest == month.section("Needs").rest
    # the reconstructed graph keeps its internal wiring (tx -> field)
    assert loaded.transactions[0].field is loaded.field("Bills", "Utilities")


def test_fake_month_repo_keys():
    repo = FakeMonthRepository()
    month = build_sample()
    repo.add(month)
    assert repo.keys(month.profile_id) == [MonthKey(2025, 1)]
    assert repo.get(month.profile_id, MonthKey(2025, 2)) is None
    assert repo.keys(999) == []


def test_fake_profile_repo():
    repo = FakeProfileRepository()
    p = repo.add(Profile(name="Me"))
    assert p.id is not None
    assert repo.get(p.id).name == "Me"
    assert repo.by_name("Me").id == p.id
    assert repo.by_name("nobody") is None
    assert [x.name for x in repo.all()] == ["Me"]


def test_uow_rolls_back_on_exception():
    uow = FakeUnitOfWork()
    with pytest.raises(RuntimeError), uow:
        uow.profiles.add(Profile(name="X"))
        raise RuntimeError("boom")
    assert uow.rolled_back
    assert not uow.committed


def test_money_survives_deepcopy_identity():
    # The slotted, immutable Money copies as itself (keeps the graph copyable).
    import copy

    m = Money("12.3456")
    assert copy.deepcopy(m) is m
    assert copy.copy(m) is m
