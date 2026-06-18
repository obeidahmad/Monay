"""Domain value objects (immutable, no identity).

These kill primitive obsession on the things that carry rules
(docs/DEVELOPING.md): ``Cap`` (rollover MAX), ``Percentage`` (a section's
share), ``MonthKey`` (``yyyy-mm``), ``Day`` (1–31), ``RestRouting`` (where a
section's REST goes at close).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from .errors import ValidationError
from .money import Money, money


# --- Cap (rollover MAX) ---------------------------------------------------
@dataclass(frozen=True)
class Cap:
    """A field's rollover ceiling: a finite ``Money`` limit, or infinite (∞).

    The pot can never grow past the limit; budget that would overflow it is not
    taken from the section (docs/DEVELOPING.md).
    """

    limit: Money | None  # None == infinite

    @classmethod
    def finite(cls, value: object) -> Cap:
        amount = money(value)
        if amount.is_negative:
            raise ValidationError(f"cap cannot be negative: {amount!r}")
        return cls(amount)

    @classmethod
    def infinite(cls) -> Cap:
        return cls(None)

    @property
    def is_infinite(self) -> bool:
        return self.limit is None

    def clamp(self, value: Money) -> Money:
        """``min(value, limit)``; returns ``value`` unchanged when infinite."""
        if self.limit is None or value <= self.limit:
            return value
        return self.limit

    def __str__(self) -> str:
        return "∞" if self.limit is None else str(self.limit)


# --- Percentage -----------------------------------------------------------
@dataclass(frozen=True)
class Percentage:
    """A section's share of income, validated to 0–100."""

    value: Decimal

    def __post_init__(self) -> None:
        raw = self.value.value if isinstance(self.value, Percentage) else self.value
        if isinstance(raw, bool):
            raise ValidationError("percentage cannot be a bool")
        if isinstance(raw, float):
            raise ValidationError("percentage rejects float; use int, str, or Decimal")
        try:
            if isinstance(raw, Decimal):
                d = raw
            elif isinstance(raw, int):
                d = Decimal(raw)
            elif isinstance(raw, str):
                d = Decimal(raw.strip())
            else:
                raise ValidationError(
                    f"cannot make a percentage from {type(raw).__name__}"
                )
        except InvalidOperation as exc:
            raise ValidationError(f"not a valid percentage: {self.value!r}") from exc
        if d < 0 or d > 100:
            raise ValidationError(f"percentage out of range 0–100: {d}")
        object.__setattr__(self, "value", d)

    @property
    def fraction(self) -> Decimal:
        return self.value / Decimal(100)

    def of(self, amount: Money) -> Money:
        """This percentage *of* an amount, re-quantized to 4dp."""
        return amount * self.fraction


# --- MonthKey -------------------------------------------------------------
_MONTHKEY_RE = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass(frozen=True, order=True)
class MonthKey:
    """A calendar month ``yyyy-mm``, chronologically ordered."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if isinstance(self.year, bool) or not isinstance(self.year, int):
            raise ValidationError("year must be an int")
        if isinstance(self.month, bool) or not isinstance(self.month, int):
            raise ValidationError("month must be an int")
        if self.year < 1 or self.year > 9999:
            raise ValidationError(f"year out of range: {self.year}")
        if self.month < 1 or self.month > 12:
            raise ValidationError(f"month out of range 1–12: {self.month}")

    @classmethod
    def from_string(cls, text: str) -> MonthKey:
        m = _MONTHKEY_RE.match(text.strip()) if isinstance(text, str) else None
        if not m:
            raise ValidationError(f"month key must look like yyyy-mm: {text!r}")
        return cls(int(m.group(1)), int(m.group(2)))

    @classmethod
    def from_date(cls, d) -> MonthKey:
        return cls(d.year, d.month)

    def next(self) -> MonthKey:
        if self.month == 12:
            return MonthKey(self.year + 1, 1)
        return MonthKey(self.year, self.month + 1)

    def previous(self) -> MonthKey:
        if self.month == 1:
            return MonthKey(self.year - 1, 12)
        return MonthKey(self.year, self.month - 1)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


# --- Day ------------------------------------------------------------------
@dataclass(frozen=True, order=True)
class Day:
    """A day-of-month, 1–31 (storage ties it to its month record)."""

    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise ValidationError("day must be an int")
        if self.value < 1 or self.value > 31:
            raise ValidationError(f"day out of range 1–31: {self.value}")

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)


# --- RestRouting ----------------------------------------------------------
class RoutingKind(StrEnum):
    INCOME = "income"
    SELF = "self"
    SECTION = "section"


@dataclass(frozen=True)
class RestRouting:
    """Where a section's REST goes at close: income, itself, or another section.

    Matches the schema's ``rest_routing`` + ``rest_target`` columns
    (docs/DEVELOPING.md). The target is a section *name* so routing survives the
    snapshot-copy into the next month (docs/DEVELOPING.md).
    """

    kind: RoutingKind
    target: str | None = None  # section name when kind is SECTION

    def __post_init__(self) -> None:
        if not isinstance(self.kind, RoutingKind):
            try:
                object.__setattr__(self, "kind", RoutingKind(self.kind))
            except ValueError as exc:
                raise ValidationError(f"unknown routing kind: {self.kind!r}") from exc
        if self.kind is RoutingKind.SECTION:
            if not self.target or not self.target.strip():
                raise ValidationError("section routing needs a target section name")
        elif self.target is not None:
            raise ValidationError(f"{self.kind.value} routing takes no target")

    @classmethod
    def to_income(cls) -> RestRouting:
        return cls(RoutingKind.INCOME)

    @classmethod
    def to_self(cls) -> RestRouting:
        return cls(RoutingKind.SELF)

    @classmethod
    def to_section(cls, name: str) -> RestRouting:
        return cls(RoutingKind.SECTION, name)

    @property
    def is_income(self) -> bool:
        return self.kind is RoutingKind.INCOME

    @property
    def is_self(self) -> bool:
        return self.kind is RoutingKind.SELF

    @property
    def is_section(self) -> bool:
        return self.kind is RoutingKind.SECTION
