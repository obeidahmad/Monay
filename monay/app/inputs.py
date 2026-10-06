"""Interpreters for user-typed values — text from a form field → domain types.

The web UI sends amounts, budgets, caps and routings exactly as the user typed
them; these turn that text into value objects (``inf`` caps, ``50%`` budgets,
``income``/``self``/``<section>`` routing, arithmetic amounts like
``15.71+1.35``). Bad input raises a domain ``ValidationError`` with a message
meant for the user.
"""

from __future__ import annotations

from monay.domain.expressions import evaluate
from monay.domain.money import Money
from monay.domain.values import Cap, Percentage, RestRouting

_INFINITE = ("inf", "infinite", "∞", "")


def amount(text: str) -> Money:
    """An amount, which may be an arithmetic expression (``15.71+1.35``)."""
    return evaluate(text)


def cap(text: str | None) -> Cap:
    """A rollover MAX: a number/expression, or ``inf``/``∞``/blank for none."""
    if text is None or text.strip().lower() in _INFINITE:
        return Cap.infinite()
    return Cap.finite(evaluate(text))


def percentage(text: str) -> Percentage:
    """A percentage, with or without a trailing ``%``."""
    text = text.strip()
    return Percentage(text[:-1] if text.endswith("%") else text)


def budget(text: str | None) -> Money | Percentage:
    """A field budget: an amount, or ``NN%`` of the section's free AVAILABLE."""
    if text is None or not text.strip():
        return Money.zero()
    text = text.strip()
    return percentage(text) if text.endswith("%") else evaluate(text)


def allocation(text: str) -> Money | Percentage:
    """A section's allocation: ``NN%`` or a fixed amount (pre-sections only)."""
    text = text.strip()
    return percentage(text) if text.endswith("%") else evaluate(text)


def routing(text: str) -> RestRouting:
    """Where REST goes at close: ``income``, ``self``, or a section name."""
    low = text.strip().lower()
    if low == "income":
        return RestRouting.to_income()
    if low == "self":
        return RestRouting.to_self()
    return RestRouting.to_section(text.strip())
