"""Phase 1 — the safe expression evaluator."""

from decimal import Decimal

import pytest

from monay.domain.errors import ExpressionError
from monay.domain.expressions import evaluate
from monay.domain.money import Money


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("15.71+1.35", "17.06"),
        ("(7.81)/2+6.5", "10.405"),
        ("10", "10"),
        ("2 - 3", "-1"),
        ("3*-2", "-6"),
        ("0.1+0.2", "0.3"),
        ("  42  ", "42"),
        ("-5", "-5"),
        ("+5", "5"),
        ("2*3+4", "10"),
        (".5", "0.5"),
    ],
)
def test_evaluates(expr, expected):
    assert evaluate(expr) == Money(expected)


def test_repeating_division_quantizes_to_4dp():
    assert evaluate("1/3").amount == Decimal("0.3333")


@pytest.mark.parametrize(
    "expr",
    [
        "",
        "   ",
        "1+",
        "a+1",
        "x.y",
        "2**3",
        "1<2",
        "__import__('os')",
        "len('a')",
        "1/0",
        "1%2",
        "1//2",
        "[1,2]",
        "1;2",
    ],
)
def test_rejects(expr):
    with pytest.raises(ExpressionError):
        evaluate(expr)


def test_rejects_overlong():
    with pytest.raises(ExpressionError):
        evaluate("1+" * 200 + "1")