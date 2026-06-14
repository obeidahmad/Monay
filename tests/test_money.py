"""Phase 1 — the Money value object: 4dp storage, banker's rounding, arithmetic."""

from decimal import Decimal

import pytest

from monay.domain.errors import ValidationError
from monay.domain.money import Money, money


def test_stores_at_four_places():
    assert Money("1").amount == Decimal("1.0000")
    assert Money(7).amount == Decimal("7.0000")
    assert Money("1.23456").amount == Decimal("1.2346")  # 6 rounds 5 up


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0.00005", "0.0000"),  # half -> even (0)
        ("0.00015", "0.0002"),  # half -> even (up from 1)
        ("0.00025", "0.0002"),  # half -> even (stays 2)
        ("0.00035", "0.0004"),  # half -> even (up from 3)
    ],
)
def test_storage_banker_rounding(value, expected):
    assert Money(value).amount == Decimal(expected)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1.005", "1.00"),  # half -> even (0)
        ("1.015", "1.02"),  # half -> even (up from 1)
        ("1.025", "1.02"),  # half -> even (stays 2)
        ("1.2349", "1.23"),
    ],
)
def test_display_banker_rounding(value, expected):
    assert Money(value).display() == Decimal(expected)


def test_addition_is_exact_no_float_error():
    assert Money("0.1") + Money("0.2") == Money("0.3")
    assert sum([Money("1"), Money("2"), Money("3")]) == Money("6")


def test_subtraction_negation_abs():
    assert Money("10") - Money("3.5") == Money("6.5")
    assert -Money("5") == Money("-5")
    assert abs(Money("-5")) == Money("5")


def test_scalar_multiplication_and_division():
    assert Money("100") * Decimal("0.015") == Money("1.5")  # zakat 1.5%
    assert Decimal("0.015") * Money("100") == Money("1.5")  # rmul
    assert Money("2") * 3 == Money("6")
    assert Money("10") / 4 == Money("2.5")
    assert (Money("1") / 3).amount == Decimal("0.3333")


def test_min_max_and_ordering():
    assert min(Money("5"), Money("3")) == Money("3")
    assert max(Money("5"), Money("3")) == Money("5")
    assert Money("1") < Money("2")
    assert Money("2") >= Money("2")


def test_equality_and_hashing():
    assert Money("1.0") == Money("1.0000")
    assert hash(Money("1.0")) == hash(Money("1.0000"))
    assert Money("1") != Money("2")
    assert len({Money("1.0"), Money("1.0000"), Money("2")}) == 2


def test_zero_and_sign_helpers():
    assert Money.zero() == Money("0")
    assert Money.zero().is_zero
    assert Money("-1").is_negative
    assert Money("1").is_positive
    assert not Money("0").is_positive


def test_money_factory_passes_through():
    m = Money("5")
    assert money(m) is m
    assert money("5") == m


def test_immutable():
    m = Money("1")
    with pytest.raises(AttributeError):
        m._amount = Decimal("2")
    with pytest.raises(AttributeError):
        m.other = 1


def test_rejects_float_and_bool():
    with pytest.raises(TypeError):
        Money(1.5)
    with pytest.raises(TypeError):
        Money(True)


def test_rejects_garbage_string():
    with pytest.raises(ValidationError):
        Money("abc")


def test_no_silent_compare_with_int():
    assert Money("1") != 1
    with pytest.raises(TypeError):
        _ = Money("1") < 1