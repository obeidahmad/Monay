"""SQLAlchemy adapters against a real (in-memory) SQLite.

Save the sample aggregate, reload it, and assert structural equality + that
recompute still matches. Plus ports conformance, keys, profile CRUD, the
closed-month write guard, and migration idempotency.
"""

import pytest

from monay.data.db import make_engine, run_migrations
from monay.data.unit_of_work import SqlAlchemyUnitOfWork
from monay.domain.closing import MonthCloser
from monay.domain.entities import Profile
from monay.domain.errors import MonthClosed
from monay.domain.money import Money
from monay.domain.ports import MonthRepository, ProfileRepository, UnitOfWork
from monay.domain.values import Cap, MonthKey
from tests.fixtures.sample_budget import build_sample


def M(v: str) -> Money:
    return Money(v)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    run_migrations(eng)
    return eng


def _seed(engine) -> int:
    """Insert a profile + the recomputed sample month; return the profile id."""
    month = build_sample()
    month.recompute()
    uow = SqlAlchemyUnitOfWork(engine)
    with uow:
        prof = uow.profiles.add(Profile(name="Me"))
        month.profile_id = prof.id
        uow.months.add(month)
        uow.commit()
    return prof.id


def test_conforms_to_ports(engine):
    uow = SqlAlchemyUnitOfWork(engine)
    with uow:
        assert isinstance(uow, UnitOfWork)
        assert isinstance(uow.months, MonthRepository)
        assert isinstance(uow.profiles, ProfileRepository)


def test_roundtrip_recompute_matches(engine):
    pid = _seed(engine)
    with SqlAlchemyUnitOfWork(engine) as uow:
        loaded = uow.months.get(pid, MonthKey(2025, 1))

    assert loaded is not None
    assert [s.name for s in loaded.sections] == ["Bills", "Needs", "Wants", "Savings"]
    assert len(loaded.section("Needs").fields) == 3
    assert len(loaded.transactions) == 4

    # recompute reproduces the values from stored inputs
    assert loaded.total_income == M("2000")
    assert loaded.field("Needs", "Groceries").left == M("350")
    assert loaded.field("Savings", "Investments").left == M("640")
    assert loaded.section("Needs").rest == M("350")
    assert loaded.section("Savings").rest == M("60")
    assert loaded.pocket("Broker").counter == loaded.field("Savings", "Investments").left

    # value objects survived
    assert loaded.field("Needs", "Groceries").cap == Cap.finite("400")
    assert loaded.field("Savings", "Investments").cap == Cap.infinite()
    assert loaded.section("Bills").rest_routing == build_sample().section("Bills").rest_routing
    assert loaded.field("Needs", "Dining").current == M("0")

    # transactions rewired to their field objects (first tx is Bills/Utilities)
    assert loaded.transactions[0].field is loaded.field("Bills", "Utilities")


def test_keys(engine):
    pid = _seed(engine)
    with SqlAlchemyUnitOfWork(engine) as uow:
        assert uow.months.keys(pid) == [MonthKey(2025, 1)]
        assert uow.months.get(pid, MonthKey(2025, 2)) is None
        assert uow.months.keys(999) == []


def test_profile_crud(engine):
    uow = SqlAlchemyUnitOfWork(engine)
    with uow:
        p = uow.profiles.add(Profile(name="Alice", currency_symbol="$"))
        uow.commit()
    with SqlAlchemyUnitOfWork(engine) as uow:
        assert uow.profiles.get(p.id).name == "Alice"
        assert uow.profiles.by_name("Alice").currency_symbol == "$"
        assert uow.profiles.by_name("nobody") is None
        assert [x.name for x in uow.profiles.all()] == ["Alice"]


def test_rollback_discards_changes(engine):
    uow = SqlAlchemyUnitOfWork(engine)
    with uow:
        uow.profiles.add(Profile(name="Ghost"))
        # no commit -> rolled back on exit
    with SqlAlchemyUnitOfWork(engine) as uow:
        assert uow.profiles.by_name("Ghost") is None


def test_closed_month_save_rejected(engine):
    pid = _seed(engine)
    with SqlAlchemyUnitOfWork(engine) as uow:
        month = uow.months.get(pid, MonthKey(2025, 1))
        nxt = MonthCloser().close(month)
        uow.months.save(month)  # open -> closed: allowed
        uow.months.add(nxt)
        uow.commit()

    with SqlAlchemyUnitOfWork(engine) as uow:
        closed = uow.months.get(pid, MonthKey(2025, 1))
        assert closed.is_closed
        with pytest.raises(MonthClosed):
            uow.months.save(closed)
        assert uow.months.keys(pid) == [MonthKey(2025, 1), MonthKey(2025, 2)]


def test_migrations_idempotent(engine):
    run_migrations(engine)
    run_migrations(engine)
    pid = _seed(engine)
    with SqlAlchemyUnitOfWork(engine) as uow:
        assert uow.months.get(pid, MonthKey(2025, 1)) is not None
