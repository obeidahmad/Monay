"""Phase 8 — drive parsed command strings against a fake UoW, assert state.

No TUI, no database: a shared ``FakeUnitOfWork`` persists across use cases, the
``MonayApp`` runs them, and the ``CommandRegistry`` parses real command lines.
"""

from datetime import date

import pytest

from monay.app.commands import build_registry
from monay.app.services import MonayApp
from monay.domain.money import Money
from monay.domain.values import Cap, Day, MonthKey, Percentage
from tests.fakes import FakeUnitOfWork, FixedClock


def make_app(today=date(2026, 6, 13)):
    fake = FakeUnitOfWork()
    app = MonayApp(uow_factory=lambda: fake, clock=FixedClock(today))
    registry = build_registry()

    def run(text, confirmed=False):
        return registry.execute(app, text, confirmed=confirmed)

    return app, run


def make_budget():
    """An app with a profile, the three post sections (sum 100%), and income."""
    app, run = make_app()
    run("profile add Demo")
    run("section add post Need 50%")
    run("section add post Want 30%")
    run("section add post Save 20%")
    run("income add Pay 1000")
    return app, run


# --- profile + first month -----------------------------------------------
def test_create_profile_seeds_open_month_with_main_pocket():
    app, run = make_app()
    r = run("profile add Demo")
    assert r.status == "info"
    assert app.profile_name == "Demo"
    m = app.active_month()
    assert m.key == MonthKey(2026, 6)
    assert any(p.is_default and p.name == "Main" for p in m.pockets)


# --- section add + field add + add transaction ---------------------------
def test_section_field_and_transaction():
    app, run = make_budget()
    assert run("field add Need Food 300 400").status == "ok"
    r = run("add Food 15.71+1.35 sds lunch")
    assert r.status == "ok"
    m = app.active_month()
    f = m.field("Need", "Food")
    assert f.paid == Money("17.06")  # 15.71+1.35
    assert f.left == Money("282.94")  # 0 + 300 - 17.06
    tx = m.transactions[0]
    assert tx.description == "sds lunch"
    assert tx.day == Day(13)  # defaulted to the clock day (real calendar month)


def test_day_override_token():
    app, run = make_budget()
    run("field add Need Food 300 400")
    run("add Food 10 d5 groceries")
    assert app.active_month().transactions[0].day == Day(5)


# --- field set (budget / max / current) ----------------------------------
def test_field_set_variants():
    app, run = make_budget()
    run("field add Need Transport")
    run("field set Transport budget 50")
    run("field set Transport max 50")
    f = app.active_month().field("Need", "Transport")
    assert f.budget == Money("50")
    assert f.cap == Cap.finite("50")
    run("field set Transport max inf")
    assert app.active_month().field("Need", "Transport").cap == Cap.infinite()
    run("field set Transport name Transit")
    assert app.active_month().field("Need", "Transit").budget == Money("50")


# --- transfer (incl. over-MAX refusal) -----------------------------------
def test_transfer_and_cap_refusal():
    app, run = make_budget()
    run("field add Save A 0 inf")
    run("field set A current 100")
    run("field add Save B 0 50")
    run("field set B current 40")

    assert run("transfer 20 A B").status == "error"  # 40+20 > 50
    assert run("transfer 10 A B").status == "ok"
    m = app.active_month()
    assert m.field("Save", "B").left == Money("50")
    assert m.field("Save", "A").left == Money("90")


# --- section add error surfaced (post needs %) ---------------------------
def test_section_add_post_requires_percentage():
    app, run = make_app()
    run("profile add Me")
    assert run("section add post Need 50%").status == "ok"
    assert run("section add post Bad 300").status == "error"  # post must be %


# --- close (confirm flow) + closed-month rejection -----------------------
def test_close_confirm_flow_and_history_lock():
    app, run = make_budget()
    pending = run("close")
    assert pending.status == "confirm"
    assert "Leftovers" in pending.message

    done = run(pending.pending, confirmed=True)
    assert done.status == "ok"
    assert app.viewing == MonthKey(2026, 7)
    assert app.active_month().key == MonthKey(2026, 7)

    # the carried Leftovers entry exists in July
    leftovers = [i for i in app.active_month().incomes if i.kind.value == "leftover"]
    assert len(leftovers) == 1

    # June is closed → editing it is rejected
    run("month 2026-06")
    assert app.viewing_closed
    r = run("income add Bonus 50")
    assert r.status == "error"
    assert "closed" in r.message.lower()


def test_close_refused_when_unbalanced():
    app, run = make_app()
    run("profile add Me")
    run("section add post Need 50%")  # only 50%
    run("income add Pay 1000")
    r = run("close")  # summary calls assert_operable
    assert r.status == "error"
    assert "100" in r.message


# --- field del guard + confirm -------------------------------------------
def test_field_del_guard_and_confirm():
    app, run = make_budget()
    run("field add Need Pot 50")  # LEFT 50
    assert run("field del Pot").status == "confirm"
    assert run("field del Pot", confirmed=True).status == "error"  # holds money
    run("field set Pot budget 0")
    assert run("field del Pot", confirmed=True).status == "ok"


# --- profiles -------------------------------------------------------------
def test_profile_switch_and_isolation():
    app, run = make_app()
    run("profile add Alice")
    run("profile add Bob")
    assert app.profile_name == "Bob"
    run("section add post Need 100%")
    run("profile switch Alice")
    assert app.profile_name == "Alice"
    # Alice's June has no sections (isolated world)
    assert app.active_month().sections == []


# --- meta -----------------------------------------------------------------
def test_help_and_unknown_command():
    app, run = make_app()
    assert run("help").status == "info"
    assert run("help field").status == "info"
    assert run("frobnicate").status == "error"


def test_no_profile_guard():
    app, run = make_app()
    r = run("add Food 5")
    assert r.status == "error"


def test_resume_reselects_existing_profile_on_restart():
    # one "session" creates a profile + structure...
    fake = FakeUnitOfWork()
    first = MonayApp(uow_factory=lambda: fake, clock=FixedClock(date(2026, 6, 13)))
    first.create_profile("Demo")
    first.add_income("Pay", Money("1000"))

    # ...a fresh app (same store = a restart) auto-selects it
    restarted = MonayApp(uow_factory=lambda: fake, clock=FixedClock(date(2026, 6, 13)))
    assert restarted.profile_id is None
    assert restarted.resume() is True
    assert restarted.profile_name == "Demo"
    assert restarted.viewing == MonthKey(2026, 6)
    assert restarted.active_month().total_income == Money("1000")


def test_resume_with_no_profiles_stays_empty():
    app, _ = make_app()
    assert app.resume() is False
    assert app.profile_id is None