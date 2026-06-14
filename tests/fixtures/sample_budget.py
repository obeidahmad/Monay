"""A small, neutral sample budget used across the test suite.

Round, invented numbers (no real data), chosen so every value is easy to verify
by hand against the field/section formulas in docs/DEVELOPING.md, while still
exercising the interesting behaviors:

  * a PRE section (fixed amount, taken off the top) with a fully-spent field;
  * POST sections that split the remainder 50/30/20 (sum = 100%);
  * a cap clamp (Transport: full pot, budget overflows, stays at the cap);
  * a negative carry (Dining: overspent, LEFT goes red, CONSUMED stays = BUDGET);
  * fields in non-default pockets (Bank, Broker);
  * a non-zero self-routed REST (Savings) that carries on close.

Income 2000 · Bills (pre) 500 → remainder 1500 → Needs 750 / Wants 450 / Savings 300.
"""

from __future__ import annotations

from monay.domain.entities import (
    AllocKind,
    Field,
    Income,
    IncomeKind,
    Pocket,
    Section,
    SectionKind,
    Transaction,
)
from monay.domain.month import Month
from monay.domain.money import Money
from monay.domain.values import Cap, Day, MonthKey, Percentage, RestRouting

INF = Cap.infinite()


def _m(value: str) -> Money:
    return Money(value)


def build_sample() -> Month:
    month = Month(profile_id=1, key=MonthKey(2025, 1))

    main = Pocket("Main", is_default=True, position=0)
    bank = Pocket("Bank", position=1)
    broker = Pocket("Broker", position=2)
    month.pockets = [main, bank, broker]

    month.incomes = [Income("Salary", _m("2000"), IncomeKind.MANUAL, 0)]

    bills = _section("Bills", SectionKind.PRE, 0, RestRouting.to_self(), amount=_m("500"))
    _fields(bills, main, [
        ("Utilities", "500", "0", INF),
    ])

    needs = _section("Needs", SectionKind.POST, 1, RestRouting.to_income(), percentage=Percentage(50))
    _fields(needs, main, [
        ("Groceries", "300", "100", Cap.finite("400")),
        ("Transport", "50", "50", Cap.finite("50")),
        ("Dining", "100", "0", INF),
    ])

    wants = _section("Wants", SectionKind.POST, 2, RestRouting.to_income(), percentage=Percentage(30))
    _fields(wants, main, [
        ("Clothes", "150", "0", INF),
        ("Gadgets", "0", "200", INF),
    ])

    savings = _section("Savings", SectionKind.POST, 3, RestRouting.to_self(), percentage=Percentage(20))
    _fields(savings, bank, [
        ("Emergency", "100", "1000", Cap.finite("5000")),
    ])
    _fields(savings, broker, [
        ("Investments", "140", "500", INF),
    ])

    month.sections = [bills, needs, wants, savings]
    month.transactions = _transactions(month)
    return month


def _section(name, kind, position, routing, *, percentage=None, amount=None) -> Section:
    return Section(
        name=name,
        kind=kind,
        alloc_kind=AllocKind.AMOUNT if amount is not None else AllocKind.PCT,
        position=position,
        percentage=percentage,
        amount=amount,
        rest_routing=routing,
    )


def _fields(section: Section, pocket: Pocket, rows) -> None:
    start = len(section.fields)
    for i, (name, budget, current, cap) in enumerate(rows):
        section.fields.append(
            Field(name, _m(budget), _m(current), cap, pocket, position=start + i)
        )


# (day, section, field, amount) — kept tiny; Groceries uses two entries (one an
# expression) to exercise PAID summation.
_TX = [
    (3, "Bills", "Utilities", "450"),
    (5, "Needs", "Groceries", "30"),
    (6, "Needs", "Groceries", "10+10"),
    (8, "Needs", "Dining", "250"),
]


def _transactions(month: Month) -> list[Transaction]:
    return [
        Transaction(field(month, section, name), Day(day), _m(_eval(amount)))
        for day, section, name, amount in _TX
    ]


def _eval(text: str) -> str:
    from monay.domain.expressions import evaluate

    return str(evaluate(text).amount)


def section(month: Month, name: str) -> Section:
    return next(s for s in month.sections if s.name == name)


def field(month: Month, section_name: str, field_name: str) -> Field:
    return next(f for f in section(month, section_name).fields if f.name == field_name)


def pocket(month: Month, name: str) -> Pocket:
    return next(p for p in month.pockets if p.name == name)