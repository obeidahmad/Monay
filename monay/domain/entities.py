"""Domain entities — stateful, persistence-ignorant plain objects.

These carry both the user's inputs and the values ``Month.recompute()`` fills in
place (docs/DEVELOPING.md). Names match docs/DEVELOPING.md exactly. Mutations
are meant to go through the ``Month`` aggregate root (Phase 3); these classes are
the data it owns.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date
from enum import StrEnum

from .errors import ValidationError
from .money import Money
from .values import Cap, Day, Percentage, RestRouting

# Reserved name for the synthetic "income" pseudo-section the Budget tab shows
# above the real sections (drillable via ``open income``). It is not a real
# Section — no real section may take this name (see ``Month.add_section``).
INCOME_SECTION_NAME = "income"


class SectionKind(StrEnum):
    TAX = "tax"
    PRE = "pre"
    POST = "post"


class AllocKind(StrEnum):
    PCT = "pct"
    AMOUNT = "amount"


class IncomeKind(StrEnum):
    MANUAL = "manual"
    LEFTOVER = "leftover"


@dataclass
class Profile:
    """A fully independent budgeting world (its own months/structure/settings)."""

    name: str
    currency_symbol: str = "€"
    id: int | None = None
    created_at: date | None = None


@dataclass
class Pocket:
    """A physical place money sits (Main, Revolut, Broker…). Counter = Σ LEFT."""

    name: str
    is_default: bool = False
    position: int = 0
    id: int | None = None
    counter: Money = dc_field(default_factory=Money.zero)  # computed


@dataclass
class Income:
    """A named amount entering the month (Paycheck, Leftovers…)."""

    name: str
    amount: Money
    kind: IncomeKind = IncomeKind.MANUAL
    position: int = 0
    id: int | None = None


@dataclass
class Field:
    """A budget line inside a section. CONSUMED/LEFT/PAID are computed."""

    name: str
    budget: Money
    current: Money
    cap: Cap
    pocket: Pocket
    position: int = 0
    id: int | None = None
    # computed by Month.recompute()
    paid: Money = dc_field(default_factory=Money.zero)
    left: Money = dc_field(default_factory=Money.zero)
    consumed: Money = dc_field(default_factory=Money.zero)


@dataclass
class Section:
    """A named group of fields receiving a slice (AVAILABLE) of the month's income.

    TAX sections take a % of *fresh* income (everything but leftovers) off the
    top, before anything else; PRE sections then take a fixed amount or % of
    remaining income off the top, in order; POST sections split what remains by
    percentage (must sum to 100%). ``carried_rest`` is REST routed into this
    section when last month closed.
    """

    name: str
    kind: SectionKind
    alloc_kind: AllocKind
    position: int = 0
    percentage: Percentage | None = None
    amount: Money | None = None
    rest_routing: RestRouting = dc_field(default_factory=RestRouting.to_income)
    carried_rest: Money = dc_field(default_factory=Money.zero)
    fields: list[Field] = dc_field(default_factory=list)
    id: int | None = None
    # computed by Month.recompute()
    available: Money = dc_field(default_factory=Money.zero)
    consumed: Money = dc_field(default_factory=Money.zero)
    rest: Money = dc_field(default_factory=Money.zero)
    budget_left: Money = dc_field(default_factory=Money.zero)

    def __post_init__(self) -> None:
        if self.alloc_kind is AllocKind.PCT and self.percentage is None:
            raise ValidationError(
                f"section {self.name!r} allocates by %, needs a percentage"
            )
        if self.alloc_kind is AllocKind.AMOUNT and self.amount is None:
            raise ValidationError(
                f"section {self.name!r} allocates a fixed amount, needs one"
            )
        if (
            self.kind in (SectionKind.POST, SectionKind.TAX)
            and self.alloc_kind is not AllocKind.PCT
        ):
            raise ValidationError(
                f"{self.kind.value}-sections must allocate by percentage"
            )


@dataclass
class Transaction:
    """Money leaving a field's pot (positive amount). Feeds PAID."""

    field: Field
    day: Day
    amount: Money
    amount_expr: str = ""
    description: str = ""
    id: int | None = None


@dataclass
class Transfer:
    """A move of accumulated pot money (LEFT) between two fields, outside field math."""

    from_field: Field
    to_field: Field
    day: Day
    amount: Money
    amount_expr: str = ""
    note: str = ""
    id: int | None = None
