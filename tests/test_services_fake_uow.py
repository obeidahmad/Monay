"""Drive the ``MonayApp`` use cases against a fake UoW, assert state.

No web layer, no database: a shared ``FakeUnitOfWork`` persists across use
cases, the ``MonayApp`` runs them, and ``app.inputs`` turns typed text into
values exactly as the web API does.
"""

from datetime import date

import pytest

from monay.app import inputs
from monay.app.errors import BadUsageError, NoProfileError
from monay.app.services import MonayApp
from monay.domain.errors import (
    AmbiguousError,
    CapExceededError,
    FieldNotEmptyError,
    MonthClosedError,
    MonthNotBalancedError,
    ValidationError,
)
from monay.domain.money import Money
from monay.domain.values import Cap, Day, MonthKey, Percentage
from tests.fakes import FakeUnitOfWork, FixedClock


def make_app(today=date(2026, 6, 13)):
    fake = FakeUnitOfWork()
    return MonayApp(uow_factory=lambda: fake, clock=FixedClock(today))


def make_budget():
    """An app with a profile, the three post sections (sum 100%), and income."""
    app = make_app()
    app.create_profile("Demo")
    app.add_section("post", "Need", percentage=Percentage(50))
    app.add_section("post", "Want", percentage=Percentage(30))
    app.add_section("post", "Save", percentage=Percentage(20))
    app.add_income("Pay", Money("1000"))
    return app


# --- profile + first month -----------------------------------------------
def test_create_profile_seeds_open_month_with_main_pocket():
    app = make_app()
    app.create_profile("Demo")
    assert app.profile_name == "Demo"
    m = app.active_month()
    assert m.key == MonthKey(2026, 6)
    assert any(p.is_default and p.name == "Main" for p in m.pockets)
    assert app.is_first_month()


# --- section add + field add + add transaction ---------------------------
def test_section_field_and_transaction():
    app = make_budget()
    app.add_field("Need", "Food", inputs.budget("300"), inputs.cap("400"))
    app.add_transaction("Food", inputs.amount("15.71+1.35"), None, "sds lunch")
    m = app.active_month()
    f = m.field("Need", "Food")
    assert f.paid == Money("17.06")  # 15.71+1.35
    assert f.left == Money("282.94")  # 0 + 300 - 17.06
    tx = m.transactions[0]
    assert tx.description == "sds lunch"
    assert tx.day == Day(13)  # defaulted to the clock day (real calendar month)


def test_explicit_day():
    app = make_budget()
    app.add_field("Need", "Food", Money("300"), Cap.infinite())
    app.add_transaction("Food", Money("10"), 5, "groceries", section="Need")
    assert app.active_month().transactions[0].day == Day(5)


def test_same_field_name_in_two_sections_needs_the_section():
    app = make_budget()
    app.add_field("Need", "Misc", Money("10"), Cap.infinite())
    app.add_field("Want", "Misc", Money("20"), Cap.infinite())
    with pytest.raises(AmbiguousError):
        app.add_transaction("Misc", Money("1"), 1)
    app.add_transaction("Misc", Money("1"), 1, section="Want")
    assert app.active_month().field("Want", "Misc").paid == Money("1")


def test_edit_and_delete_transaction():
    app = make_budget()
    app.add_field("Need", "Food", Money("300"), Cap.infinite())
    app.add_transaction("Food", Money("10"), 1)
    app.edit_transaction(1, amount=Money("12"), day=3, description="x")
    tx = app.active_month().transactions[0]
    assert (tx.amount, tx.day, tx.description) == (Money("12"), Day(3), "x")
    app.delete_transaction(1)
    assert app.active_month().transactions == []
    with pytest.raises(BadUsageError):
        app.delete_transaction(1)


# --- field edits ------------------------------------------------------------
def test_edit_field_applies_every_change_at_once():
    app = make_budget()
    app.add_pocket("Bank")
    app.add_field("Need", "Transport", Money("0"), Cap.infinite())
    app.edit_field(
        "Need",
        "Transport",
        budget=inputs.budget("50"),
        cap=inputs.cap("50"),
        pocket="Bank",
        new_name="Transit",
    )
    f = app.active_month().field("Need", "Transit")
    assert (f.budget, f.cap, f.pocket.name) == (Money("50"), Cap.finite("50"), "Bank")
    app.edit_field("Need", "Transit", cap=inputs.cap("inf"))
    assert app.active_month().field("Need", "Transit").cap == Cap.infinite()


def test_edit_field_is_all_or_nothing():
    app = make_budget()
    app.add_field("Need", "A", Money("0"), Cap.infinite())
    app.add_field("Need", "B", Money("0"), Cap.infinite())
    with pytest.raises(Exception):  # noqa: B017 — the rename collides
        app.edit_field("Need", "A", budget=Money("99"), new_name="B")
    assert app.active_month().field("Need", "A").budget == Money("0")


def test_current_only_editable_in_first_month():
    app = make_budget()
    app.add_field("Need", "Pot", Money("0"), Cap.infinite())
    app.edit_field("Need", "Pot", current=Money("40"))
    assert app.active_month().field("Need", "Pot").current == Money("40")
    app.close_active()
    assert not app.is_first_month()
    with pytest.raises(BadUsageError):
        app.edit_field("Need", "Pot", current=Money("1"))


# --- % field budgets -------------------------------------------------------
def test_field_add_with_percentage_budget():
    app = make_budget()  # income 1000, Need is 50% post -> AVAILABLE 500
    app.add_field("Need", "Rent", inputs.budget("300"), Cap.infinite())
    app.add_field("Need", "Emergency", inputs.budget("50%"), inputs.cap("400"))
    f = app.active_month().field("Need", "Emergency")
    assert f.budget_pct == Percentage(50)
    assert f.budget == Money("100")  # 50% of (500 - 300 fixed)
    assert f.cap == Cap.finite("400")


def test_field_budget_percentage_round_trip():
    app = make_budget()
    app.add_field("Need", "Emergency", Money("0"), Cap.infinite())
    app.edit_field("Need", "Emergency", budget=inputs.budget("50%"))
    f = app.active_month().field("Need", "Emergency")
    assert (f.budget_pct, f.budget) == (Percentage(50), Money("250"))
    app.edit_field("Need", "Emergency", budget=inputs.budget("200"))
    f = app.active_month().field("Need", "Emergency")
    assert (f.budget_pct, f.budget) == (None, Money("200"))


def test_field_budget_percentage_out_of_range():
    with pytest.raises(ValidationError, match="0–100"):
        inputs.budget("150%")


# --- transfer (incl. over-MAX refusal) -----------------------------------
def test_transfer_and_cap_refusal():
    app = make_budget()
    app.add_field("Save", "A", Money("0"), Cap.infinite())
    app.edit_field("Save", "A", current=Money("100"))
    app.add_field("Save", "B", Money("0"), Cap.finite("50"))
    app.edit_field("Save", "B", current=Money("40"))

    with pytest.raises(CapExceededError) as exc:
        app.transfer(Money("20"), "A", "B", 1)  # 40+20 > 50
    assert exc.value.allowed == Money("10")
    app.transfer(Money("10"), "A", "B", 1, from_section="Save", to_section="Save")
    m = app.active_month()
    assert m.field("Save", "B").left == Money("50")
    assert m.field("Save", "A").left == Money("90")


# --- sections ---------------------------------------------------------------
def test_section_add_post_requires_percentage():
    app = make_app()
    app.create_profile("Me")
    with pytest.raises(ValidationError):
        app.add_section("post", "Bad", amount=Money("300"))


def test_edit_section_alloc_routing_order_and_name():
    app = make_budget()
    app.add_section("pre", "Bills", amount=Money("100"))
    app.edit_section(
        "Bills",
        allocation=inputs.allocation("10%"),
        routing=inputs.routing("self"),
        position=0,
        new_name="Fixed",
    )
    s = app.active_month().section("Fixed")
    assert s.percentage == Percentage(10)
    assert s.rest_routing.is_self
    assert s.position == 0
    app.edit_section("Fixed", allocation=inputs.allocation("200"))
    assert app.active_month().section("Fixed").amount == Money("200")


# --- close (preview) + closed-month rejection -----------------------------
def test_close_preview_and_history_lock():
    app = make_budget()
    preview = app.close_preview()
    assert preview.next_key == MonthKey(2026, 7)
    assert preview.leftovers == Money("1000")  # nothing budgeted, all to income

    app.close_active()
    assert app.viewing == MonthKey(2026, 7)
    leftovers = [i for i in app.active_month().incomes if i.kind.value == "leftover"]
    assert len(leftovers) == 1

    # June is closed → editing it is rejected
    app.view_month("2026-06")
    assert app.viewing_closed
    with pytest.raises(MonthClosedError):
        app.add_income("Bonus", Money("50"))
    assert app.view_open_month() == MonthKey(2026, 7)


def test_close_refused_when_unbalanced():
    app = make_app()
    app.create_profile("Me")
    app.add_section("post", "Need", percentage=Percentage(50))  # only 50%
    with pytest.raises(MonthNotBalancedError, match="100"):
        app.close_preview()


# --- field del guard ----------------------------------------------------------
def test_field_del_guard():
    app = make_budget()
    app.add_field("Need", "Pot", Money("50"), Cap.infinite())  # LEFT 50
    with pytest.raises(FieldNotEmptyError):
        app.delete_field("Pot")
    app.edit_field("Need", "Pot", budget=Money("0"))
    app.delete_field("Pot", section="Need")
    assert app.active_month().section("Need").fields == []


# --- pockets ------------------------------------------------------------------
def test_edit_pocket_rename_and_main():
    app = make_budget()
    app.add_pocket("Bank")
    app.edit_pocket("Bank", new_name="Revolut", main=True)
    m = app.active_month()
    assert [p.name for p in m.pockets if p.is_default] == ["Revolut"]


# --- profiles -------------------------------------------------------------
def test_profile_switch_and_isolation():
    app = make_app()
    app.create_profile("Alice")
    app.create_profile("Bob")
    assert app.profile_name == "Bob"
    app.add_section("post", "Need", percentage=Percentage(100))
    app.switch_profile("Alice")
    assert app.profile_name == "Alice"
    assert app.active_month().sections == []  # Alice's June is its own world


def test_no_profile_guard():
    app = make_app()
    with pytest.raises(NoProfileError):
        app.add_transaction("Food", Money("5"), 1)


def test_resume_reselects_existing_profile_on_restart():
    fake = FakeUnitOfWork()
    first = MonayApp(uow_factory=lambda: fake, clock=FixedClock(date(2026, 6, 13)))
    first.create_profile("Demo")
    first.add_income("Pay", Money("1000"))

    restarted = MonayApp(uow_factory=lambda: fake, clock=FixedClock(date(2026, 6, 13)))
    assert restarted.profile_id is None
    assert restarted.resume() is True
    assert restarted.profile_name == "Demo"
    assert restarted.viewing == MonthKey(2026, 6)
    assert restarted.active_month().total_income == Money("1000")


def test_resume_with_no_profiles_stays_empty():
    app = make_app()
    assert app.resume() is False
    assert app.profile_id is None
