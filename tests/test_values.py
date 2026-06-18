"""Phase 1 — value objects: Cap, Percentage, MonthKey, Day, RestRouting."""

from decimal import Decimal

import pytest

from monay.domain.errors import ValidationError
from monay.domain.money import Money
from monay.domain.values import Cap, Day, MonthKey, Percentage, RestRouting


# --- Cap ------------------------------------------------------------------
def test_cap_finite_clamps():
    cap = Cap.finite(18)
    assert not cap.is_infinite
    assert cap.clamp(Money("20")) == Money("18")  # overflow trimmed to the cap
    assert cap.clamp(Money("10")) == Money("10")  # below cap untouched


def test_cap_infinite_passes_through():
    cap = Cap.infinite()
    assert cap.is_infinite
    assert cap.clamp(Money("99999")) == Money("99999")


def test_cap_negative_rejected():
    with pytest.raises(ValidationError):
        Cap.finite(-1)


def test_cap_equality():
    assert Cap.finite(18) == Cap.finite("18")
    assert Cap.infinite() == Cap.infinite()
    assert Cap.finite(18) != Cap.infinite()


# --- Percentage -----------------------------------------------------------
def test_percentage_of():
    assert Percentage(50).of(Money("1000")) == Money("500")
    assert Percentage("1.5").of(Money("1000")) == Money("15")
    assert Percentage(100).of(Money("987.65")) == Money("987.65")
    assert Percentage(0).of(Money("1000")) == Money("0")


def test_percentage_fraction():
    assert Percentage(20).fraction == Decimal("0.2")


@pytest.mark.parametrize("bad", ["-1", "101", "100.0001"])
def test_percentage_out_of_range(bad):
    with pytest.raises(ValidationError):
        Percentage(bad)


def test_percentage_rejects_float():
    with pytest.raises(ValidationError):
        Percentage(1.5)


# --- MonthKey -------------------------------------------------------------
def test_monthkey_roundtrip_and_str():
    assert str(MonthKey.from_string("2026-07")) == "2026-07"
    assert str(MonthKey(2026, 7)) == "2026-07"


def test_monthkey_next_prev_wrap():
    assert MonthKey.from_string("2026-12").next() == MonthKey(2027, 1)
    assert MonthKey.from_string("2026-01").previous() == MonthKey(2025, 12)
    assert MonthKey(2026, 6).next() == MonthKey(2026, 7)


def test_monthkey_ordering():
    assert MonthKey.from_string("2026-06") < MonthKey.from_string("2026-07")
    assert MonthKey(2027, 1) > MonthKey(2026, 12)


@pytest.mark.parametrize(
    "bad", ["2026-13", "2026-00", "2026-7", "26-06", "bad", "2026/07"]
)
def test_monthkey_invalid(bad):
    with pytest.raises(ValidationError):
        MonthKey.from_string(bad)


# --- Day ------------------------------------------------------------------
def test_day_valid():
    assert int(Day(1)) == 1
    assert int(Day(31)) == 31
    assert str(Day(5)) == "5"


@pytest.mark.parametrize("bad", [0, 32, -1])
def test_day_invalid(bad):
    with pytest.raises(ValidationError):
        Day(bad)


def test_day_ordering():
    assert Day(1) < Day(2)


# --- RestRouting ----------------------------------------------------------
def test_routing_income():
    r = RestRouting.to_income()
    assert r.is_income and r.target is None


def test_routing_self():
    r = RestRouting.to_self()
    assert r.is_self and r.target is None


def test_routing_section():
    r = RestRouting.to_section("Save")
    assert r.is_section and r.target == "Save"


def test_routing_section_requires_target():
    with pytest.raises(ValidationError):
        RestRouting.to_section("")
    with pytest.raises(ValidationError):
        RestRouting.to_section("   ")


def test_routing_coerces_string_kind():
    assert RestRouting("income").is_income
    with pytest.raises(ValidationError):
        RestRouting("bogus")
