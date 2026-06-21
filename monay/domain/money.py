"""The ``Money`` value object.

Money is a ``Decimal`` quantized to **4 decimal places** with **banker's
rounding** (``ROUND_HALF_EVEN``) — the stored truth (docs/DEVELOPING.md).
The UI shows a cosmetic 2dp view via :meth:`Money.display`. All money arithmetic
goes through this class so a value with more than 4dp can never be stored, and
no float ever touches a value (floats are rejected outright).
"""

from __future__ import annotations

import functools
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Final

from .errors import ValidationError

FOUR_PLACES: Final = Decimal("0.0001")
TWO_PLACES: Final = Decimal("0.01")
ROUNDING: Final = ROUND_HALF_EVEN

# Raw inputs accepted by Money(...) — plus Money itself (passed through).
Numeric = int | str | Decimal


def _coerce(value: object) -> Decimal:
    """Turn an accepted input into an un-quantized Decimal, or raise."""
    if isinstance(value, Money):
        return value._amount
    if isinstance(value, bool):
        raise TypeError("Money does not accept bool")
    if isinstance(value, float):
        raise TypeError(
            "Money rejects float to preserve precision; pass int, str, or Decimal"
        )
    if isinstance(value, (int, Decimal)):
        candidate: int | str | Decimal = value
    elif isinstance(value, str):
        candidate = value.strip()
    else:
        raise TypeError(f"cannot make Money from {type(value).__name__}")
    try:
        return Decimal(candidate)
    except InvalidOperation as exc:
        raise ValidationError(f"not a valid amount: {value!r}") from exc


@functools.total_ordering
class Money:
    """An immutable amount of money, stored at 4dp / banker's rounding."""

    __slots__ = ("_amount",)
    _amount: Decimal

    def __init__(self, value: Numeric | Money = 0) -> None:
        object.__setattr__(
            self, "_amount", _coerce(value).quantize(FOUR_PLACES, rounding=ROUNDING)
        )

    # --- immutability -----------------------------------------------------
    def __setattr__(self, *_: object) -> None:
        raise AttributeError("Money is immutable")

    def __delattr__(self, *_: object) -> None:
        raise AttributeError("Money is immutable")

    # --- constructors -----------------------------------------------------
    @classmethod
    def zero(cls) -> Money:
        return cls(0)

    # --- views ------------------------------------------------------------
    @property
    def amount(self) -> Decimal:
        """The stored 4dp Decimal — the source of truth."""
        return self._amount

    def display(self) -> Decimal:
        """Cosmetic 2dp value for the UI (banker's rounding)."""
        return self._amount.quantize(TWO_PLACES, rounding=ROUNDING)

    @property
    def is_zero(self) -> bool:
        return self._amount == 0

    @property
    def is_negative(self) -> bool:
        return self._amount < 0

    @property
    def is_positive(self) -> bool:
        return self._amount > 0

    # --- arithmetic -------------------------------------------------------
    def __add__(self, other: object) -> Money:
        if isinstance(other, Money):
            return Money(self._amount + other._amount)
        return NotImplemented

    def __radd__(self, other: object) -> Money:
        if other == 0:  # enables sum() with its default int start of 0
            return self
        return NotImplemented

    def __sub__(self, other: object) -> Money:
        if isinstance(other, Money):
            return Money(self._amount - other._amount)
        return NotImplemented

    def __neg__(self) -> Money:
        return Money(-self._amount)

    def __abs__(self) -> Money:
        return Money(abs(self._amount))

    def __mul__(self, factor: object) -> Money:
        # Scale by a unit-less scalar (e.g. a Percentage fraction).
        if isinstance(factor, bool):
            return NotImplemented
        if isinstance(factor, (int, Decimal)):
            return Money(self._amount * factor)
        return NotImplemented

    __rmul__ = __mul__

    def __truediv__(self, divisor: object) -> Money:
        if isinstance(divisor, bool):
            return NotImplemented
        if isinstance(divisor, (int, Decimal)):
            return Money(self._amount / divisor)
        return NotImplemented

    # --- comparison -------------------------------------------------------
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self._amount == other._amount
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self._amount < other._amount
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._amount)

    # --- copy / pickle (immutable, so a "copy" is just self) --------------
    def __copy__(self) -> Money:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Money:
        return self

    def __reduce__(self) -> tuple[type[Money], tuple[str]]:
        return (Money, (str(self._amount),))

    # --- repr -------------------------------------------------------------
    def __repr__(self) -> str:
        return f"Money('{self._amount}')"

    def __str__(self) -> str:
        return str(self.display())


def money(value: Numeric | Money = 0) -> Money:
    """Ergonomic constructor; an existing Money passes through unchanged."""
    return value if isinstance(value, Money) else Money(value)
