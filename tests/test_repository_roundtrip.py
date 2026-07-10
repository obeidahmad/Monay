"""SQLAlchemy adapters against a real (in-memory) SQLite.

Save the sample aggregate, reload it, and assert structural equality + that
recompute still matches. Plus ports conformance, keys, profile CRUD, the
closed-month write guard, and migration idempotency.
"""

import pytest
import sqlalchemy as sa

from monay.data.db import make_engine, run_migrations
from monay.data.schema import schema_version
from monay.data.unit_of_work import SqlAlchemyUnitOfWork
from monay.domain.closing import MonthCloser
from monay.domain.entities import Profile
from monay.domain.errors import MonthClosedError
from monay.domain.money import Money
from monay.domain.ports import MonthRepository, ProfileRepository, UnitOfWork
from monay.domain.values import Cap, MonthKey, Percentage
from tests.fixtures.sample_budget import build_sample


def money(v: str) -> Money:
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
    assert loaded.total_income == money("2000")
    assert loaded.field("Needs", "Groceries").left == money("350")
    assert loaded.field("Savings", "Investments").left == money("640")
    assert loaded.section("Needs").rest == money("350")
    assert loaded.section("Savings").rest == money("60")
    assert (
        loaded.pocket("Broker").counter == loaded.field("Savings", "Investments").left
    )

    # value objects survived
    assert loaded.field("Needs", "Groceries").cap == Cap.finite("400")
    assert loaded.field("Savings", "Investments").cap == Cap.infinite()
    assert (
        loaded.section("Bills").rest_routing
        == build_sample().section("Bills").rest_routing
    )
    assert loaded.field("Needs", "Dining").current == money("0")

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
        p = uow.profiles.add(Profile(name="Alice"))
        uow.commit()
    with SqlAlchemyUnitOfWork(engine) as uow:
        assert uow.profiles.get(p.id).name == "Alice"
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
        with pytest.raises(MonthClosedError):
            uow.months.save(closed)
        assert uow.months.keys(pid) == [MonthKey(2025, 1), MonthKey(2025, 2)]


def test_migrations_idempotent(engine):
    run_migrations(engine)
    run_migrations(engine)
    pid = _seed(engine)
    with SqlAlchemyUnitOfWork(engine) as uow:
        assert uow.months.get(pid, MonthKey(2025, 1)) is not None


def test_pct_field_roundtrip(engine):
    pid = _seed(engine)
    with SqlAlchemyUnitOfWork(engine) as uow:
        month = uow.months.get(pid, MonthKey(2025, 1))
        month.add_field("Savings", "Vacation", Percentage(50), Cap.infinite(), "Main")
        uow.months.save(month)
        uow.commit()

    with SqlAlchemyUnitOfWork(engine) as uow:
        loaded = uow.months.get(pid, MonthKey(2025, 1))
    f = loaded.field("Savings", "Vacation")
    assert f.budget_pct == Percentage(50)
    # get() recomputes, so the budget comes back resolved: Savings AVAILABLE is
    # 300 (20% of 1500), its fixed budgets 100 + 140 -> 50% of 60 = 30.
    assert f.budget == money("30")
    assert loaded.field("Savings", "Emergency").budget_pct is None  # fixed untouched


def test_migration_from_v1_adds_budget_pct(engine):
    pid = _seed(engine)
    # Rewind to a v1 database: drop the column m0002 adds and reset the version.
    with engine.begin() as conn:
        conn.exec_driver_sql("ALTER TABLE fields DROP COLUMN budget_pct")
        conn.execute(sa.delete(schema_version))
        conn.execute(schema_version.insert().values(version=1))

    run_migrations(engine)

    with engine.begin() as conn:
        columns = {c["name"] for c in sa.inspect(conn).get_columns("fields")}
    assert "budget_pct" in columns
    with SqlAlchemyUnitOfWork(engine) as uow:
        loaded = uow.months.get(pid, MonthKey(2025, 1))  # legacy rows load as fixed
    assert all(f.budget_pct is None for s in loaded.sections for f in s.fields)
