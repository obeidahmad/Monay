"""Request values → domain values, with each failure pinned to its form field.

The engine's own errors say what rule was broken; a form needs to know *which
input* to mark and what to type instead. Reading every value here, one at a
time, is what lets the API answer with both.
"""

from __future__ import annotations

from monay.domain.errors import ValidationError
from monay.domain.expressions import evaluate
from monay.domain.money import Money
from monay.domain.values import Cap, MonthKey, Percentage, RestRouting, RoutingKind

from .schemas import AmountOrPercent, FieldRef, RestRoutingModel


class InputError(Exception):
    """A request value that reads wrong; ``field`` is the input it came from."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def amount(text: str, field: str = "amount") -> Money:
    try:
        return evaluate(text)
    # ArithmeticError: a syntactically fine number too large to hold at 4dp.
    except (ValidationError, ArithmeticError) as exc:
        raise InputError(
            field,
            f"Can't read {text!r} as an amount. Use numbers with + - * / and "
            "parentheses, like 15.71+1.35.",
        ) from exc


def positive_amount(text: str, field: str = "amount") -> Money:
    value = amount(text, field)
    if not value.is_positive:
        raise InputError(field, "Enter an amount greater than zero.")
    return value


def non_negative_amount(text: str, field: str) -> Money:
    value = amount(text, field)
    if value.is_negative:
        raise InputError(field, "This can't be negative.")
    return value


def percentage(text: str, field: str) -> Percentage:
    try:
        return Percentage(text.strip().removesuffix("%").strip())
    except ValidationError as exc:
        raise InputError(field, "Enter a percentage between 0 and 100.") from exc


def allocation(value: AmountOrPercent, field: str = "allocation") -> Money | Percentage:
    """A section's share of income: a fixed amount or a percentage."""
    if value.type == "percent":
        return percentage(value.value, field)
    return non_negative_amount(value.value, field)


def budget(value: AmountOrPercent | None, field: str = "budget") -> Money | Percentage:
    """A field's budget; nothing given means a budget of zero."""
    if value is None:
        return Money.zero()
    return allocation(value, field)


def cap(text: str | None, field: str = "max") -> Cap:
    """A field's MAX: ``None`` is no limit (∞)."""
    if text is None:
        return Cap.infinite()
    return Cap.finite(non_negative_amount(text, field))


def routing(value: RestRoutingModel, field: str = "rest_routing") -> RestRouting:
    if value.kind is RoutingKind.INCOME:
        return RestRouting.to_income()
    if value.kind is RoutingKind.SELF:
        return RestRouting.to_self()
    try:
        return RestRouting.to_section(value.target or "")
    except ValidationError as exc:
        raise InputError(field, "Choose the section the rest should go to.") from exc


def month_key(text: str) -> MonthKey:
    return MonthKey.from_string(text)


def field_ref(ref: FieldRef) -> tuple[int, int]:
    return ref.section, ref.field
