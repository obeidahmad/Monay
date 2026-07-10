"""The ``Month`` aggregate root: the budget engine + the mutators.

``recompute()`` refreshes every computed value in place from the raw inputs
(docs/DEVELOPING.md). The mutators are the *only*
sanctioned way to change a month — each enforces the invariants (no writes when
closed, names unique, caps never exceeded incl. transfers, field-delete only
when empty, post-% sums to 100 to operate) and leaves the month recomputed.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from .entities import (
    INCOME_SECTION_NAME,
    AllocKind,
    Field,
    Income,
    IncomeKind,
    Pocket,
    Section,
    SectionKind,
    Transaction,
    Transfer,
)
from .errors import (
    AmbiguousError,
    CapExceededError,
    DuplicateNameError,
    FieldNotEmptyError,
    MonthClosedError,
    MonthNotBalancedError,
    NotFoundError,
    PocketInUseError,
    SectionNotEmptyError,
    ValidationError,
)
from .money import Money, Numeric, money
from .values import Cap, Day, MonthKey, Percentage, PercentageInput, RestRouting


class MonthState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class Month:
    """The single consistency boundary for one month's budget."""

    def __init__(
        self,
        profile_id: int,
        key: MonthKey,
        state: MonthState = MonthState.OPEN,
        id: int | None = None,
    ) -> None:
        self.profile_id = profile_id
        self.key = key
        self.state = state
        self.id = id
        self.incomes: list[Income] = []
        self.pockets: list[Pocket] = []
        self.sections: list[Section] = []
        self.transactions: list[Transaction] = []
        self.transfers: list[Transfer] = []
        # computed
        self.total_income: Money = Money.zero()
        self.fresh_income: Money = Money.zero()
        self.warnings: list[str] = []

    @property
    def is_closed(self) -> bool:
        return self.state is MonthState.CLOSED

    # =====================================================================
    # The engine
    # =====================================================================
    def recompute(self) -> None:
        """Refresh every computed value in place from the raw inputs."""
        self.warnings = []
        self.total_income = sum((i.amount for i in self.incomes), Money.zero())
        # FRESH INCOME = income that has not been taxed before — i.e. everything
        # except LEFTOVER, which was already taxed when it first arrived. It is
        # the base TAX sections allocate against.
        self.fresh_income = sum(
            (i.amount for i in self.incomes if i.kind is not IncomeKind.LEFTOVER),
            Money.zero(),
        )

        self._recompute_paid()
        unallocated = self._allocate_sections()
        self._resolve_field_budgets()
        self._recompute_fields_and_rest()
        self._apply_transfers()
        self._recompute_pockets(unallocated)
        self._check_post_percentages()

    def _recompute_paid(self) -> None:
        for f in self._all_fields():
            f.paid = Money.zero()
        for tx in self.transactions:
            tx.field.paid = tx.field.paid + tx.amount

    def _allocate_sections(self) -> Money:
        """Give each section its AVAILABLE; return the unallocated income."""
        tax = sorted(
            (s for s in self.sections if s.kind is SectionKind.TAX),
            key=lambda s: s.position,
        )
        pre = sorted(
            (s for s in self.sections if s.kind is SectionKind.PRE),
            key=lambda s: s.position,
        )
        post = sorted(
            (s for s in self.sections if s.kind is SectionKind.POST),
            key=lambda s: s.position,
        )

        remaining = self.total_income
        for s in tax:
            # TAX sections allocate by % off FRESH income only (leftovers were
            # already taxed). Every TAX taxes the same fresh base — they don't
            # compound — and the total is taken off the top before PRE/POST.
            assert s.percentage is not None
            share = s.percentage.of(self.fresh_income)
            s.available = share + s.carried_rest
            remaining = remaining - share

        for s in pre:
            # alloc_kind and amount/percentage are kept consistent by Section's
            # invariant, so exactly one of them is set for each branch.
            if s.alloc_kind is AllocKind.AMOUNT:
                assert s.amount is not None
                share = s.amount
            else:
                assert s.percentage is not None
                share = s.percentage.of(remaining)
            s.available = share + s.carried_rest
            remaining = remaining - share

        post_shares = Money.zero()
        for s in post:
            assert s.percentage is not None  # post sections always allocate by %
            share = s.percentage.of(remaining)
            s.available = share + s.carried_rest
            post_shares = post_shares + share

        return remaining - post_shares  # income left in no section

    def _resolve_field_budgets(self) -> None:
        """Turn each %-field's percentage into a BUDGET amount.

        The base is the section's AVAILABLE minus its fixed budgets, clamped at
        zero (a section in deficit resolves every %-budget to 0 — budgets are
        never negative). Every %-field shares the same base, so resolution is
        order-independent. The result is floored to whole cents: a budget is
        directly spendable money, and flooring means %-fields can never sum
        past the base — the shaved fraction stays in the section's REST.
        """
        for s in self.sections:
            fixed = sum(
                (f.budget for f in s.fields if f.budget_pct is None), Money.zero()
            )
            base = s.available - fixed
            if base.is_negative:
                base = Money.zero()
            for f in s.fields:
                if f.budget_pct is not None:
                    f.budget = f.budget_pct.of(base).floor_cents()

    def _recompute_fields_and_rest(self) -> None:
        for s in self.sections:
            consumed_total = Money.zero()
            budget_total = Money.zero()
            for f in sorted(s.fields, key=lambda f: f.position):
                raw = f.current + f.budget - f.paid
                f.left = f.cap.clamp(raw)
                f.consumed = f.left - f.current + f.paid
                consumed_total = consumed_total + f.consumed
                budget_total = budget_total + f.budget
            s.consumed = consumed_total
            s.rest = s.available - consumed_total
            s.budget_left = s.available - budget_total
            if s.rest.is_negative:
                self.warnings.append(f"section {s.name!r} REST is negative")

    def _apply_transfers(self) -> None:
        # Transfers relocate pots only (LEFT ± amount); they never touch field
        # math (PAID/CONSUMED/REST) — docs/DEVELOPING.md.
        for t in self.transfers:
            t.from_field.left = t.from_field.left - t.amount
            t.to_field.left = t.to_field.left + t.amount

    def _recompute_pockets(self, unallocated_income: Money) -> None:
        for p in self.pockets:
            p.counter = Money.zero()
        for f in self._all_fields():
            f.pocket.counter = f.pocket.counter + f.left
        # The default pocket also holds live section RESTs and any income not
        # yet given to a section (docs/DEVELOPING.md).
        default = next((p for p in self.pockets if p.is_default), None)
        if default is not None:
            for s in self.sections:
                default.counter = default.counter + s.rest
            default.counter = default.counter + unallocated_income

    def _check_post_percentages(self) -> None:
        total = self._post_percentage_total()
        if total is not None and total != Decimal(100):
            self.warnings.append(f"post-section percentages sum to {total}, not 100")

    # =====================================================================
    # Lookups
    # =====================================================================
    def section(self, name: str) -> Section:
        for s in self.sections:
            if s.name == name:
                return s
        raise NotFoundError(f"no section named {name!r}")

    def field(self, section_name: str, field_name: str) -> Field:
        for f in self.section(section_name).fields:
            if f.name == field_name:
                return f
        raise NotFoundError(f"no field {field_name!r} in section {section_name!r}")

    def locate_field(self, name: str) -> tuple[str, Field]:
        """Resolve a bare field name to ``(section_name, field)``.

        Field names are unique within a section but can repeat across sections;
        commands address fields by bare name, so this raises ``AmbiguousError`` when
        the name matches more than one (docs/DEVELOPING.md).
        """
        matches = [
            (s.name, f) for s in self.sections for f in s.fields if f.name == name
        ]
        if not matches:
            raise NotFoundError(f"no field named {name!r}")
        if len(matches) > 1:
            where = ", ".join(sn for sn, _ in matches)
            raise AmbiguousError(
                f"field {name!r} exists in several sections ({where}); be specific"
            )
        return matches[0]

    def pocket(self, name: str) -> Pocket:
        for p in self.pockets:
            if p.name == name:
                return p
        raise NotFoundError(f"no pocket named {name!r}")

    # =====================================================================
    # Transactions
    # =====================================================================
    def add_transaction(
        self,
        section_name: str,
        field_name: str,
        day: Day | int | str,
        amount: Money | Numeric,
        description: str = "",
        amount_expr: str = "",
    ) -> Transaction:
        self._require_open()
        f = self.field(section_name, field_name)
        tx = Transaction(
            field=f,
            day=self._day(day),
            amount=self._positive(amount, "transaction amount"),
            amount_expr=amount_expr,
            description=description,
        )
        self.transactions.append(tx)
        self.recompute()
        return tx

    def edit_transaction(
        self,
        tx: Transaction,
        *,
        day: Day | int | str | None = None,
        amount: Money | Numeric | None = None,
        description: str | None = None,
    ) -> None:
        self._require_open()
        if amount is not None:
            tx.amount = self._positive(amount, "transaction amount")
        if day is not None:
            tx.day = self._day(day)
        if description is not None:
            tx.description = description
        self.recompute()

    def delete_transaction(self, tx: Transaction) -> None:
        self._require_open()
        self.transactions.remove(tx)
        self.recompute()

    # =====================================================================
    # Transfers
    # =====================================================================
    def transfer(
        self,
        from_section: str,
        from_field: str,
        to_section: str,
        to_field: str,
        day: Day | int | str,
        amount: Money | Numeric,
        note: str = "",
    ) -> Transfer:
        self._require_open()
        src = self.field(from_section, from_field)
        dst = self.field(to_section, to_field)
        if src is dst:
            raise ValidationError("cannot transfer a field to itself")
        amount = self._positive(amount, "transfer amount")
        self.recompute()  # fresh LEFTs to validate the cap against
        if not dst.cap.is_infinite:
            assert dst.cap.limit is not None  # not infinite ⟺ a finite limit
            room = dst.cap.limit - dst.left
            if amount > room:
                raise CapExceededError(
                    f"transfer would push {to_field!r} above its MAX "
                    f"of {dst.cap.limit}; the largest that fits is {room}",
                    allowed=room,
                )
        t = Transfer(
            from_field=src, to_field=dst, day=self._day(day), amount=amount, note=note
        )
        self.transfers.append(t)
        self.recompute()
        return t

    def delete_transfer(self, t: Transfer) -> None:
        self._require_open()
        self.transfers.remove(t)
        self.recompute()

    # =====================================================================
    # Fields
    # =====================================================================
    def add_field(
        self,
        section_name: str,
        name: str,
        budget: Money | Numeric | Percentage,
        cap: Cap,
        pocket_name: str,
        current: Money | Numeric | None = None,
    ) -> Field:
        self._require_open()
        s = self.section(section_name)
        if any(f.name == name for f in s.fields):
            raise DuplicateNameError(
                f"section {section_name!r} already has a field {name!r}"
            )
        if not isinstance(cap, Cap):
            raise ValidationError("cap must be a Cap")
        if isinstance(budget, Percentage):
            initial, pct = Money.zero(), budget
        else:
            initial, pct = self._nonneg(budget, "budget"), None
        f = Field(
            name=name,
            budget=initial,
            current=Money.zero() if current is None else money(current),
            cap=cap,
            pocket=self.pocket(pocket_name),
            position=len(s.fields),
            budget_pct=pct,
        )
        s.fields.append(f)
        self.recompute()
        return f

    def delete_field(self, section_name: str, name: str) -> None:
        self._require_open()
        self.recompute()
        f = self.field(section_name, name)
        if not f.left.is_zero:
            raise FieldNotEmptyError(
                f"field {name!r} still holds {f.left} — "
                "transfer its pot away (LEFT must be 0) first"
            )
        if any(tx.field is f for tx in self.transactions):
            raise FieldNotEmptyError(
                f"field {name!r} has transactions this month; delete them first"
            )
        if any(t.from_field is f or t.to_field is f for t in self.transfers):
            raise FieldNotEmptyError(
                f"field {name!r} is referenced by a transfer; remove it first"
            )
        self.section(section_name).fields.remove(f)
        self.recompute()

    def set_field_budget(
        self, section_name: str, name: str, budget: Money | Numeric | Percentage
    ) -> None:
        self._require_open()
        f = self.field(section_name, name)
        if isinstance(budget, Percentage):
            f.budget_pct = budget  # recompute resolves f.budget from it
        else:
            f.budget = self._nonneg(budget, "budget")
            f.budget_pct = None  # switching kinds clears the other
        self.recompute()

    def set_field_cap(self, section_name: str, name: str, cap: Cap) -> None:
        self._require_open()
        if not isinstance(cap, Cap):
            raise ValidationError("cap must be a Cap")
        self.field(section_name, name).cap = cap
        self.recompute()

    def set_field_pocket(self, section_name: str, name: str, pocket_name: str) -> None:
        self._require_open()
        p = self.pocket(pocket_name)
        self.field(section_name, name).pocket = p
        self.recompute()

    def set_field_current(
        self, section_name: str, name: str, current: Money | Numeric
    ) -> None:
        # CURRENT is normally carried from last month; hand-editing is meant for
        # the first (hand-built) month — the app guards that (docs/DEVELOPING.md).
        self._require_open()
        self.field(section_name, name).current = money(current)
        self.recompute()

    def rename_field(self, section_name: str, name: str, new_name: str) -> None:
        self._require_open()
        s = self.section(section_name)
        if new_name != name and any(f.name == new_name for f in s.fields):
            raise DuplicateNameError(
                f"section {section_name!r} already has a field {new_name!r}"
            )
        self.field(section_name, name).name = new_name
        self.recompute()

    # =====================================================================
    # Sections
    # =====================================================================
    def add_section(
        self,
        name: str,
        kind: SectionKind | str,
        *,
        percentage: Percentage | PercentageInput | None = None,
        amount: Money | Numeric | None = None,
        rest_routing: RestRouting | None = None,
        position: int | None = None,
    ) -> Section:
        self._require_open()
        self._reject_reserved_name(name)
        if any(s.name == name for s in self.sections):
            raise DuplicateNameError(f"a section named {name!r} already exists")
        kind = SectionKind(kind)
        s = Section(
            name=name,
            kind=kind,
            alloc_kind=AllocKind.AMOUNT if amount is not None else AllocKind.PCT,
            position=self._next_section_position() if position is None else position,
            percentage=self._as_percentage(percentage)
            if percentage is not None
            else None,
            amount=money(amount) if amount is not None else None,
            rest_routing=rest_routing or RestRouting.to_income(),
        )
        self.sections.append(s)
        self.recompute()
        return s

    def delete_section(self, name: str) -> None:
        self._require_open()
        s = self.section(name)
        if s.fields:
            raise SectionNotEmptyError(
                f"section {name!r} still has fields; delete them first"
            )
        self.sections.remove(s)
        self.recompute()

    def edit_section(
        self,
        name: str,
        *,
        new_name: str | None = None,
        percentage: Percentage | PercentageInput | None = None,
        amount: Money | Numeric | None = None,
        rest_routing: RestRouting | None = None,
        position: int | None = None,
    ) -> None:
        self._require_open()
        s = self.section(name)
        if new_name is not None and new_name != name:
            self._reject_reserved_name(new_name)
            if any(o.name == new_name for o in self.sections):
                raise DuplicateNameError(f"a section named {new_name!r} already exists")
            s.name = new_name
        if percentage is not None:
            s.percentage = self._as_percentage(percentage)
            s.alloc_kind = AllocKind.PCT
            s.amount = None
        if amount is not None:
            if s.kind in (SectionKind.POST, SectionKind.TAX):
                raise ValidationError(
                    f"{s.kind.value}-sections allocate by percentage, "
                    "not a fixed amount"
                )
            s.amount = money(amount)
            s.alloc_kind = AllocKind.AMOUNT
            s.percentage = None
        if rest_routing is not None:
            s.rest_routing = rest_routing
        if position is not None:
            s.position = position
        self.recompute()

    # =====================================================================
    # Income
    # =====================================================================
    def add_income(
        self, name: str, amount: Money | Numeric, kind: IncomeKind = IncomeKind.MANUAL
    ) -> Income:
        self._require_open()
        inc = Income(
            name=name,
            amount=money(amount),
            kind=IncomeKind(kind),
            position=len(self.incomes),
        )
        self.incomes.append(inc)
        self.recompute()
        return inc

    def edit_income(
        self,
        income: Income,
        *,
        name: str | None = None,
        amount: Money | Numeric | None = None,
    ) -> None:
        self._require_open()
        if name is not None:
            income.name = name
        if amount is not None:
            income.amount = money(amount)
        self.recompute()

    def delete_income(self, income: Income) -> None:
        self._require_open()
        self.incomes.remove(income)
        self.recompute()

    # =====================================================================
    # Pockets
    # =====================================================================
    def add_pocket(self, name: str, is_default: bool = False) -> Pocket:
        self._require_open()
        if any(p.name == name for p in self.pockets):
            raise DuplicateNameError(f"a pocket named {name!r} already exists")
        p = Pocket(name=name, is_default=False, position=len(self.pockets))
        self.pockets.append(p)
        if is_default:
            self.set_default_pocket(name)  # recomputes
        else:
            self.recompute()
        return p

    def set_default_pocket(self, name: str) -> None:
        self._require_open()
        target = self.pocket(name)
        for p in self.pockets:
            p.is_default = p is target
        self.recompute()

    def delete_pocket(self, name: str) -> None:
        self._require_open()
        p = self.pocket(name)
        if p.is_default:
            raise ValidationError("cannot delete the default pocket")
        if any(f.pocket is p for f in self._all_fields()):
            raise PocketInUseError(
                f"pocket {name!r} still holds fields; reassign them first"
            )
        self.pockets.remove(p)
        self.recompute()

    def rename_pocket(self, name: str, new_name: str) -> None:
        self._require_open()
        if new_name != name and any(p.name == new_name for p in self.pockets):
            raise DuplicateNameError(f"a pocket named {new_name!r} already exists")
        self.pocket(name).name = new_name
        self.recompute()

    # =====================================================================
    # Guards / helpers
    # =====================================================================
    def assert_operable(self) -> None:
        """Raise unless the month can be operated/closed (post-% sums to 100)."""
        total = self._post_percentage_total()
        if total is not None and total != Decimal(100):
            raise MonthNotBalancedError(
                f"post-section percentages sum to {total}, not 100"
            )

    def _require_open(self) -> None:
        if self.is_closed:
            raise MonthClosedError(
                f"month {self.key} is closed; make corrections in the open month"
            )

    @staticmethod
    def _reject_reserved_name(name: str) -> None:
        # 'income' names the synthetic pseudo-section the Budget tab shows above
        # the real sections; a real section by that name would shadow it.
        if name.lower() == INCOME_SECTION_NAME:
            raise ValidationError(
                f"{name!r} is reserved for the income summary; pick another name"
            )

    def _post_percentage_total(self) -> Decimal | None:
        post = [s for s in self.sections if s.kind is SectionKind.POST]
        if not post:
            return None
        return sum(
            (s.percentage.value for s in post if s.percentage is not None), Decimal(0)
        )

    def _next_section_position(self) -> int:
        return max((s.position for s in self.sections), default=-1) + 1

    @staticmethod
    def _as_percentage(value: Percentage | PercentageInput) -> Percentage:
        return value if isinstance(value, Percentage) else Percentage(value)

    @staticmethod
    def _day(value: Day | int | str) -> Day:
        return value if isinstance(value, Day) else Day(int(value))

    @staticmethod
    def _positive(amount: Money | Numeric, what: str) -> Money:
        m = amount if isinstance(amount, Money) else Money(amount)
        if not m.is_positive:
            raise ValidationError(f"{what} must be positive, got {m}")
        return m

    @staticmethod
    def _nonneg(amount: Money | Numeric, what: str) -> Money:
        m = amount if isinstance(amount, Money) else Money(amount)
        if m.is_negative:
            raise ValidationError(f"{what} cannot be negative, got {m}")
        return m

    def _all_fields(self) -> list[Field]:
        return [f for s in self.sections for f in s.fields]
