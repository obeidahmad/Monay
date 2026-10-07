"""The API's wire format.

These models are also where the web app's TypeScript types come from: they are
generated from the OpenAPI document this module produces, so the two sides
cannot drift apart.

Conventions worth knowing before reading on:

* **Money is a string**, the stored 4dp decimal (``"332.9400"``) — never a JSON
  number, which a client would read as a float and quietly lose the precision
  the engine exists to protect. The client formats it for display.
* **Amounts typed by a person are expressions** (``"15.71+1.35"``); the server
  evaluates them. Percentages are plain numbers in a string (``"50"``).
* **``index`` / ``number`` are positions in one revision of the month.** Send
  that month's ``revision`` back in ``If-Match`` with every change; a ``412``
  means the positions you hold are out of date.
* On an update, a property that is **absent** is left unchanged.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints
from pydantic import Field as Constraint

from monay.domain.entities import IncomeKind, SectionKind
from monay.domain.month import MonthState
from monay.domain.values import RoutingKind

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
]
Expression = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
MonthKeyText = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
Index = Annotated[int, Constraint(ge=0)]
DayOfMonth = Annotated[int, Constraint(ge=1, le=31)]
MoneyText = Annotated[
    str, Constraint(description="A decimal at 4 places.", examples=["332.9400"])
]


class _Input(BaseModel):
    """Request bodies reject unknown properties: a typo is an error, not a no-op."""

    model_config = ConfigDict(extra="forbid")


# =========================================================================
# Shared shapes
# =========================================================================
class ErrorOut(BaseModel):
    """Every error response. ``field`` names the input at fault, when one is."""

    code: str
    message: str
    field: str | None = None


class RestRoutingModel(_Input):
    """Where a section's REST goes at close; ``target`` only for ``section``."""

    kind: RoutingKind
    target: str | None = None


class AmountOrPercent(_Input):
    """A section's allocation or a field's budget: an amount, or a percentage."""

    type: Literal["amount", "percent"]
    value: Expression


class FieldRef(_Input):
    """A field, by its section's position and its own position within it."""

    section: Index
    field: Index


# =========================================================================
# Profiles
# =========================================================================
class ProfileOut(BaseModel):
    id: int
    name: str
    created_at: date | None
    open_month: MonthKeyText | None


class ProfileCreate(_Input):
    name: Name
    first_month: MonthKeyText | None = None


class ProfileUpdate(_Input):
    name: Name


# =========================================================================
# A month, as read
# =========================================================================
class IncomeOut(BaseModel):
    index: int
    name: str
    amount: MoneyText
    kind: IncomeKind


class AllocationOut(BaseModel):
    """``value`` is a 4dp amount, or a bare percentage such as ``"50"``."""

    type: Literal["amount", "percent"]
    value: str


class FieldOut(BaseModel):
    index: int
    name: str
    budget: MoneyText
    budget_pct: str | None  # set when the budget is a % of the section
    current: MoneyText
    paid: MoneyText
    left: MoneyText
    consumed: MoneyText
    max: MoneyText | None  # null = no limit (∞)
    pocket: str
    pocket_index: int


class SectionOut(BaseModel):
    index: int
    name: str
    kind: SectionKind
    allocation: AllocationOut
    rest_routing: RestRoutingModel
    carried_rest: MoneyText
    available: MoneyText
    consumed: MoneyText
    rest: MoneyText
    budget_left: MoneyText
    fields: list[FieldOut]


class PocketHoldingOut(BaseModel):
    section: str
    field: str
    left: MoneyText


class PocketOut(BaseModel):
    """``counter`` = Σ holdings (+ ``rests`` and ``unallocated`` on the default)."""

    index: int
    name: str
    is_default: bool
    counter: MoneyText
    holdings: list[PocketHoldingOut]
    rests: MoneyText
    unallocated: MoneyText


class FieldRefOut(BaseModel):
    section_index: int
    field_index: int
    section: str
    field: str


class TransactionOut(BaseModel):
    number: int  # the stable "#" a transaction is known by within its month
    day: int
    field: FieldRefOut
    amount: MoneyText
    expression: str  # what was typed ("15.71+1.35"), when it was recorded
    description: str


class TransferOut(BaseModel):
    number: int
    day: int
    from_field: FieldRefOut
    to_field: FieldRefOut
    amount: MoneyText
    note: str


class MonthOut(BaseModel):
    key: MonthKeyText
    label: str
    state: MonthState
    is_first: bool  # the profile's first month: CURRENT may be set by hand
    revision: str  # send back in If-Match with every change
    total_income: MoneyText
    fresh_income: MoneyText
    post_pool: MoneyText
    post_pct_total: str | None  # Σ% of post-sections; null when there are none
    unallocated: MoneyText
    spent: MoneyText
    incomes: list[IncomeOut]
    sections: list[SectionOut]
    pockets: list[PocketOut]
    transactions: list[TransactionOut]
    transfers: list[TransferOut]


class ChangeOut(BaseModel):
    """The month after a change. ``undo_token`` is set when it can be undone."""

    month: MonthOut
    undo_token: str | None = None


class MonthSummaryOut(BaseModel):
    key: MonthKeyText
    label: str
    state: MonthState
    income: MoneyText
    spent: MoneyText
    leftovers: MoneyText


class RestCarryOut(BaseModel):
    section: str
    amount: MoneyText


class ClosePreviewOut(BaseModel):
    key: MonthKeyText
    label: str
    next_key: MonthKeyText
    next_label: str
    income: MoneyText
    spent: MoneyText
    leftovers: MoneyText
    carries: list[RestCarryOut]


class HealthOut(BaseModel):
    status: Literal["ok"]
    version: str


# =========================================================================
# Changes to a month
# =========================================================================
class IncomeCreate(_Input):
    name: Name
    amount: Expression


class IncomeUpdate(_Input):
    name: Name | None = None
    amount: Expression | None = None


class SectionCreate(_Input):
    name: Name
    kind: SectionKind
    allocation: AmountOrPercent
    rest_routing: RestRoutingModel | None = None


class SectionUpdate(_Input):
    name: Name | None = None
    allocation: AmountOrPercent | None = None
    rest_routing: RestRoutingModel | None = None
    position: Index | None = None  # where to move it to, in display order


class FieldCreate(_Input):
    name: Name
    budget: AmountOrPercent | None = None  # defaults to 0
    max: Expression | None = None  # null = no limit (∞)
    pocket: Index | None = None  # defaults to the default pocket
    current: Expression | None = None  # first month only


class FieldUpdate(_Input):
    name: Name | None = None
    budget: AmountOrPercent | None = None
    max: Expression | None = None  # absent = unchanged; null = no limit (∞)
    pocket: Index | None = None
    current: Expression | None = None  # first month only


class TransactionCreate(_Input):
    field: FieldRef
    amount: Expression
    day: DayOfMonth
    description: Note = ""


class TransactionUpdate(_Input):
    field: FieldRef | None = None
    amount: Expression | None = None
    day: DayOfMonth | None = None
    description: Note | None = None


class TransferCreate(_Input):
    from_field: FieldRef
    to_field: FieldRef
    amount: Expression
    day: DayOfMonth
    note: Note = ""


class PocketCreate(_Input):
    name: Name


class PocketUpdate(_Input):
    name: Name | None = None
    is_default: Literal[True] | None = None


class UndoRequest(_Input):
    token: str
