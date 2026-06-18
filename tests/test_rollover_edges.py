"""Phase 3 — aggregate mutators & invariants (docs/PLAN.md §4).

Cap clamping, negative carry, the advance pattern, transfer-over-MAX refusal,
delete guards, closed-month write rejection, and the post-% balance guard.
"""

import pytest

from monay.domain.entities import (
    AllocKind,
    Income,
    Pocket,
    Section,
    SectionKind,
)
from monay.domain.errors import (
    CapExceededError,
    DuplicateNameError,
    FieldNotEmptyError,
    MonthClosedError,
    MonthNotBalancedError,
    NotFoundError,
    PocketInUseError,
    ValidationError,
)
from monay.domain.money import Money
from monay.domain.month import Month, MonthState
from monay.domain.values import Cap, MonthKey, Percentage, RestRouting


def money(v: str) -> Money:
    return Money(v)


def make_month(income: str = "1000") -> Month:
    """One POST section 'Save' at 100%, default pocket 'Main', given income."""
    m = Month(profile_id=1, key=MonthKey(2026, 7))
    m.pockets = [Pocket("Main", is_default=True)]
    m.incomes = [Income("Pay", money(income))]
    m.sections = [
        Section(
            "Save",
            SectionKind.POST,
            AllocKind.PCT,
            position=0,
            percentage=Percentage(100),
            rest_routing=RestRouting.to_self(),
        )
    ]
    m.recompute()
    return m


# --- cap clamping (Hair Cut: full pot, budget overflows, REST keeps it) ----
def test_cap_clamps_overflow_into_rest():
    m = make_month()
    m.add_field(
        "Save", "Hair Cut", money("6"), Cap.finite("18"), "Main", current=money("18")
    )
    f = m.field("Save", "Hair Cut")
    assert f.left == money("18")  # capped — the 6 budget isn't taken
    assert f.consumed == money("0")  # nothing consumed; pot was already full


# --- negative carry (field borrows from its own future budgets) -----------
def test_negative_carry_keeps_consumed_at_budget():
    m = make_month()
    m.add_field("Save", "Food", money("50"), Cap.infinite(), "Main", current=money("0"))
    m.add_transaction("Save", "Food", 1, money("120"))
    f = m.field("Save", "Food")
    assert f.left == money("-70")  # 0 + 50 - 120
    assert f.consumed == money("50")  # only BUDGET, never the overspend
    assert m.section("Save").rest == money("950")  # section only lost the budget


# --- the advance pattern (Stock 840: section red, field never) ------------
def test_advance_pattern():
    m = make_month("197")  # Save AVAILABLE = 197
    m.add_field(
        "Save", "Stock", money("840"), Cap.infinite(), "Main", current=money("0")
    )
    stock = m.field("Save", "Stock")
    save = m.section("Save")
    assert stock.left == money("840")  # the pot grew by the full advance
    assert stock.consumed == money("840")
    assert not stock.left.is_negative  # the FIELD is never in the red
    assert save.rest == money("-643")  # the SECTION carries the debt (197 - 840)
    assert any("Save" in w and "negative" in w for w in m.warnings)


# --- transfer over MAX is refused, with the largest that fits -------------
def test_transfer_over_max_refused():
    m = make_month()
    m.add_field("Save", "Src", money("0"), Cap.infinite(), "Main", current=money("100"))
    m.add_field(
        "Save", "Dst", money("0"), Cap.finite("50"), "Main", current=money("40")
    )

    with pytest.raises(CapExceededError) as exc:
        m.transfer("Save", "Src", "Save", "Dst", day=1, amount=money("20"))
    assert exc.value.allowed == money("10")  # 50 - 40

    m.transfer("Save", "Src", "Save", "Dst", day=1, amount=money("10"))  # fits exactly
    assert m.field("Save", "Dst").left == money("50")
    assert m.field("Save", "Src").left == money("90")


def test_transfer_amount_must_be_positive():
    m = make_month()
    m.add_field("Save", "A", money("0"), Cap.infinite(), "Main", current=money("10"))
    m.add_field("Save", "B", money("0"), Cap.infinite(), "Main", current=money("0"))
    with pytest.raises(ValidationError):
        m.transfer("Save", "A", "Save", "B", day=1, amount=money("0"))


# --- delete-field guards --------------------------------------------------
def test_delete_field_refused_while_holding_money():
    m = make_month()
    m.add_field("Save", "Pot", money("50"), Cap.infinite(), "Main", current=money("0"))
    with pytest.raises(FieldNotEmptyError):
        m.delete_field("Save", "Pot")  # LEFT = 50

    m.set_field_budget("Save", "Pot", money("0"))  # empty it
    assert m.field("Save", "Pot").left == money("0")
    m.delete_field("Save", "Pot")  # now allowed
    with pytest.raises(NotFoundError):
        m.field("Save", "Pot")


def test_delete_field_refused_with_transactions_even_when_left_zero():
    m = make_month()
    m.add_field("Save", "Z", money("0"), Cap.infinite(), "Main", current=money("5"))
    m.add_transaction("Save", "Z", 1, money("5"))  # LEFT 5+0-5 = 0, but has activity
    assert m.field("Save", "Z").left == money("0")
    with pytest.raises(FieldNotEmptyError):
        m.delete_field("Save", "Z")


# --- closed months reject writes ------------------------------------------
def test_closed_month_rejects_writes():
    m = make_month()
    m.add_field("Save", "X", money("0"), Cap.infinite(), "Main", current=money("0"))
    m.state = MonthState.CLOSED
    with pytest.raises(MonthClosedError):
        m.add_transaction("Save", "X", 1, money("5"))
    with pytest.raises(MonthClosedError):
        m.set_field_budget("Save", "X", money("10"))


# --- balance guard --------------------------------------------------------
def test_post_percentage_balance_guard():
    m = make_month()  # Save 100% -> operable
    m.assert_operable()
    m.add_section("Extra", SectionKind.POST, percentage=Percentage(10))  # now 110%
    with pytest.raises(MonthNotBalancedError):
        m.assert_operable()
    assert any("110" in w for w in m.warnings)


# --- name / structure guards ----------------------------------------------
def test_duplicate_field_name_refused():
    m = make_month()
    m.add_field("Save", "Dup", money("0"), Cap.infinite(), "Main")
    with pytest.raises(DuplicateNameError):
        m.add_field("Save", "Dup", money("0"), Cap.infinite(), "Main")


def test_pocket_delete_guards():
    m = make_month()
    m.add_pocket("Broker")
    m.add_field(
        "Save", "Stock", money("70"), Cap.infinite(), "Broker", current=money("0")
    )
    with pytest.raises(PocketInUseError):
        m.delete_pocket("Broker")
    with pytest.raises(ValidationError):
        m.delete_pocket("Main")  # the default


def test_transaction_must_be_positive():
    m = make_month()
    m.add_field("Save", "F", money("0"), Cap.infinite(), "Main", current=money("0"))
    for bad in ("0", "-5"):
        with pytest.raises(ValidationError):
            m.add_transaction("Save", "F", 1, money(bad))
