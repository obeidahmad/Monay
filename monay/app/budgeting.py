"""``BudgetingService`` — the stateless use cases behind the HTTP API.

``MonayApp`` (``services.py``) is the TUI's facade and carries a *session*: one
long-lived process, one person looking at one month, so "which profile, which
month" lives in memory. HTTP has no session to lean on — two browser tabs are
two independent callers — so every use case here names the profile and month it
acts on, and nothing is remembered between calls.

Three things follow from being driven over a network instead of a keyboard:

* **Addressing.** Sections, fields, pockets and income entries are addressed by
  their position in the month as the caller last read it (transactions and
  transfers by their ``#``). Names stay out of URLs, and a month's children have
  no stable database identity anyway — ``data/mappers.py`` rewrites them on
  every save.
* **Optimistic concurrency.** A position only means something for the version
  of the month the caller was looking at, so every change carries that
  version's :func:`month_revision` and is refused with
  :class:`~monay.app.errors.StaleRevisionError` if the month has moved on.
* **Undo.** A deletion happens immediately and hands back a short-lived token;
  :class:`UndoJournal` keeps the month as it was so it can be put back exactly,
  rather than re-created approximately.

Like ``MonayApp`` it depends only on the ports (``UnitOfWork`` factory +
``Clock``); the rules themselves stay in the ``Month`` aggregate.
"""

from __future__ import annotations

import copy
import hashlib
import secrets
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from monay.app.errors import BadUsageError, StaleRevisionError, UndoUnavailableError
from monay.app.services import MonthSummary, summarize_month
from monay.domain.closing import MonthCloser
from monay.domain.entities import (
    Field,
    Income,
    IncomeKind,
    Pocket,
    Profile,
    Section,
    SectionKind,
    Transaction,
    Transfer,
)
from monay.domain.errors import DuplicateNameError, NotFoundError
from monay.domain.money import Money
from monay.domain.month import Month, MonthState
from monay.domain.ports import Clock, UnitOfWork
from monay.domain.values import Cap, MonthKey, Percentage, RestRouting


# =========================================================================
# Reading a month: one ordering, shared by addressing and presentation
# =========================================================================
def ordered_sections(month: Month) -> list[Section]:
    return sorted(month.sections, key=lambda s: s.position)


def ordered_fields(section: Section) -> list[Field]:
    return sorted(section.fields, key=lambda f: f.position)


def ordered_pockets(month: Month) -> list[Pocket]:
    return sorted(month.pockets, key=lambda p: p.position)


def ordered_incomes(month: Month) -> list[Income]:
    return sorted(month.incomes, key=lambda i: i.position)


def income_share(section: Section) -> Money:
    """What the section took from *this* month's income.

    AVAILABLE also includes REST routed in at the last close; that carried money
    is not a cut of this month's income, so it is left out.
    """
    return section.available - section.carried_rest


def post_pool(month: Month) -> Money:
    """The income POST sections split: everything after TAX and PRE."""
    off_the_top = sum(
        (income_share(s) for s in month.sections if s.kind is not SectionKind.POST),
        Money.zero(),
    )
    return month.total_income - off_the_top


def post_percentage_total(month: Month) -> Decimal | None:
    """Σ% of the POST sections (must be 100 to close), or None with no POST."""
    post = [s for s in month.sections if s.kind is SectionKind.POST]
    if not post:
        return None
    return sum(
        (s.percentage.value for s in post if s.percentage is not None), Decimal(0)
    )


def unallocated_income(month: Month) -> Money:
    """Income no section has claimed (it sits in the default pocket)."""
    claimed = sum((income_share(s) for s in month.sections), Money.zero())
    return month.total_income - claimed


def month_revision(month: Month) -> str:
    """A short content hash of everything a month stores.

    Two reads return the same revision exactly when nothing the user can change
    differs between them, which makes it an entity tag: a caller sends back the
    revision it based a change on, and a mismatch means it was looking at a
    month that no longer exists in that form. Computed values are left out —
    they follow from the inputs.
    """
    digest = hashlib.sha256()

    def put(*parts: object) -> None:
        digest.update(repr(parts).encode())

    section_of = {id(f): s.name for s in month.sections for f in s.fields}
    put("month", str(month.key), month.state.value)
    for inc in ordered_incomes(month):
        put("income", inc.name, str(inc.amount.amount), inc.kind.value)
    for p in ordered_pockets(month):
        put("pocket", p.name, p.is_default)
    for s in ordered_sections(month):
        put(
            "section",
            s.name,
            s.kind.value,
            None if s.percentage is None else str(s.percentage.value),
            None if s.amount is None else str(s.amount.amount),
            s.rest_routing.kind.value,
            s.rest_routing.target,
            str(s.carried_rest.amount),
        )
        for f in ordered_fields(s):
            put(
                "field",
                f.name,
                # a %-field's budget is computed, so only its percentage counts
                str(f.budget.amount) if f.budget_pct is None else None,
                None if f.budget_pct is None else str(f.budget_pct.value),
                str(f.current.amount),
                None if f.cap.limit is None else str(f.cap.limit.amount),
                f.pocket.name,
            )
    for tx in month.transactions:
        put(
            "transaction",
            section_of[id(tx.field)],
            tx.field.name,
            int(tx.day),
            str(tx.amount.amount),
            tx.amount_expr,
            tx.description,
        )
    for t in month.transfers:
        put(
            "transfer",
            section_of[id(t.from_field)],
            t.from_field.name,
            section_of[id(t.to_field)],
            t.to_field.name,
            int(t.day),
            str(t.amount.amount),
            t.note,
        )
    return digest.hexdigest()[:16]


# =========================================================================
# What the use cases take and return
# =========================================================================
@dataclass(frozen=True)
class ProfileInfo:
    id: int
    name: str
    created_at: date | None
    open_month: MonthKey | None


@dataclass(frozen=True)
class MonthView:
    """A month as read: the recomputed aggregate plus what only storage knows."""

    month: Month
    revision: str
    is_first: bool  # the profile's first month — CURRENT is hand-set here


@dataclass(frozen=True)
class MonthRef:
    """The month a change targets, pinned to the revision the caller last saw."""

    profile_id: int
    key: MonthKey
    revision: str


@dataclass(frozen=True)
class Changed:
    """The month after a change, plus a token when the change can be undone."""

    view: MonthView
    undo_token: str | None = None


@dataclass(frozen=True)
class RestCarry:
    """REST that will land in a section of the next month (not in its income)."""

    section: str
    amount: Money


@dataclass(frozen=True)
class ClosePreview:
    key: MonthKey
    next_key: MonthKey
    income: Money
    spent: Money
    leftovers: Money
    carries: list[RestCarry]


# =========================================================================
# Undo
# =========================================================================
@dataclass(frozen=True)
class _UndoEntry:
    before: Month
    revision: str  # the month's revision right after the change
    expires_at: float


class UndoJournal:
    """Months as they were just before a deletion, kept for a moment.

    In memory on purpose: an undo that outlives the minute (or the process) has
    stopped being an undo. Bounded by age and by count. One journal serves one
    API process — with several workers a token could reach a worker that never
    saw it, which is one more reason the API runs single-process on SQLite.
    """

    def __init__(
        self,
        ttl_seconds: float = 120.0,
        capacity: int = 32,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._capacity = capacity
        self._now = now
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, _UndoEntry] = OrderedDict()

    def remember(self, before: Month, revision: str) -> str:
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._evict_expired()
            self._entries[token] = _UndoEntry(before, revision, self._now() + self._ttl)
            while len(self._entries) > self._capacity:
                self._entries.popitem(last=False)  # oldest first
        return token

    def claim(self, token: str) -> _UndoEntry | None:
        """Take an entry out; a token is good for one undo."""
        with self._lock:
            self._evict_expired()
            return self._entries.pop(token, None)

    def _evict_expired(self) -> None:
        now = self._now()
        for token in [t for t, e in self._entries.items() if e.expires_at <= now]:
            del self._entries[token]


# =========================================================================
# A month open for one change
# =========================================================================
class _Draft:
    """A loaded month plus the position → object lookups a change needs."""

    def __init__(self, month: Month, is_first: bool) -> None:
        self.month = month
        self.is_first = is_first

    def section(self, index: int) -> Section:
        return _at(ordered_sections(self.month), index, f"no section at {index}")

    def field(self, section_index: int, field_index: int) -> tuple[Section, Field]:
        section = self.section(section_index)
        field = _at(
            ordered_fields(section),
            field_index,
            f"no field at {field_index} in section {section.name!r}",
        )
        return section, field

    def pocket(self, index: int) -> Pocket:
        return _at(ordered_pockets(self.month), index, f"no pocket at {index}")

    def income(self, index: int) -> Income:
        return _at(ordered_incomes(self.month), index, f"no income entry at {index}")

    def transaction(self, number: int) -> Transaction:
        return _at(self.month.transactions, number - 1, f"no transaction #{number}")

    def transfer(self, number: int) -> Transfer:
        return _at(self.month.transfers, number - 1, f"no transfer #{number}")

    def default_pocket(self) -> Pocket:
        pocket = next((p for p in self.month.pockets if p.is_default), None)
        if pocket is None:
            raise BadUsageError("this month has no default pocket — add one first")
        return pocket

    def require_first_month(self) -> None:
        if not self.is_first:
            raise BadUsageError(
                "CURRENT can only be set in a profile's first month; "
                "afterwards it carries over automatically"
            )


def _at[T](items: list[T], index: int, missing: str) -> T:
    if 0 <= index < len(items):
        return items[index]
    raise NotFoundError(missing)


def _move_section(month: Month, section: Section, to_index: int) -> None:
    """Put ``section`` at ``to_index`` in display order, renumbering the rest."""
    order = [s for s in ordered_sections(month) if s is not section]
    order.insert(max(0, min(to_index, len(order))), section)
    for position, s in enumerate(order):
        if s.position != position:
            month.edit_section(s.name, position=position)


def _require_current(month: Month, ref: MonthRef) -> None:
    if month_revision(month) != ref.revision:
        raise StaleRevisionError(
            f"month {month.key} has changed since it was loaded; refresh and try again"
        )


# =========================================================================
# The service
# =========================================================================
class BudgetingService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        clock: Clock,
        undo: UndoJournal | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._undo = undo if undo is not None else UndoJournal()

    # ---------------------------------------------------------------------
    # Profiles
    # ---------------------------------------------------------------------
    def list_profiles(self) -> list[ProfileInfo]:
        with self._uow_factory() as uow:
            return [self._info(uow, p) for p in uow.profiles.all()]

    def create_profile(
        self, name: str, first_month: MonthKey | None = None
    ) -> ProfileInfo:
        first = first_month or MonthKey.from_date(self._clock.today())
        with self._uow_factory() as uow:
            if uow.profiles.by_name(name) is not None:
                raise DuplicateNameError(f"a profile named {name!r} already exists")
            profile = uow.profiles.add(
                Profile(name=name, created_at=self._clock.today())
            )
            assert profile.id is not None  # just inserted; the repo set its id
            month = Month(profile_id=profile.id, key=first, state=MonthState.OPEN)
            month.add_pocket("Main", is_default=True)
            uow.months.add(month)
            uow.commit()
            return ProfileInfo(profile.id, profile.name, profile.created_at, first)

    def rename_profile(self, profile_id: int, name: str) -> ProfileInfo:
        with self._uow_factory() as uow:
            profile = self._profile(uow, profile_id)
            holder = uow.profiles.by_name(name)
            if holder is not None and holder.id != profile_id:
                raise DuplicateNameError(f"a profile named {name!r} already exists")
            profile.name = name
            uow.profiles.update(profile)
            info = self._info(uow, profile)
            uow.commit()
            return info

    def delete_profile(self, profile_id: int) -> None:
        with self._uow_factory() as uow:
            self._profile(uow, profile_id)  # a miss is a 404, not a silent no-op
            uow.profiles.delete(profile_id)
            uow.commit()

    # ---------------------------------------------------------------------
    # Reading
    # ---------------------------------------------------------------------
    def summaries(self, profile_id: int) -> list[MonthSummary]:
        """One summary per month, newest first (the History list)."""
        with self._uow_factory() as uow:
            self._profile(uow, profile_id)
            out: list[MonthSummary] = []
            for key in sorted(uow.months.keys(profile_id), reverse=True):
                month = uow.months.get(profile_id, key)
                assert month is not None  # key came from this profile's months
                out.append(summarize_month(month))
            return out

    def month(self, profile_id: int, key: MonthKey) -> MonthView:
        with self._uow_factory() as uow:
            month, is_first = self._load(uow, profile_id, key)
            return MonthView(month, month_revision(month), is_first)

    def close_preview(self, profile_id: int, key: MonthKey) -> ClosePreview:
        """What closing would do — by actually closing a throwaway copy.

        Running the real ``MonthCloser`` on a month that is never saved means
        the preview cannot drift from the close it describes.
        """
        scratch = self.month(profile_id, key).month  # loaded for this call only
        summary = summarize_month(scratch)
        nxt = MonthCloser().close(scratch)
        leftovers = sum(
            (i.amount for i in nxt.incomes if i.kind is IncomeKind.LEFTOVER),
            Money.zero(),
        )
        carries = [
            RestCarry(s.name, s.carried_rest)
            for s in ordered_sections(nxt)
            if not s.carried_rest.is_zero
        ]
        return ClosePreview(
            key, nxt.key, summary.income, summary.spent, leftovers, carries
        )

    # ---------------------------------------------------------------------
    # Income
    # ---------------------------------------------------------------------
    def add_income(self, ref: MonthRef, name: str, amount: Money) -> Changed:
        return self._change(ref, lambda d: d.month.add_income(name, amount))

    def edit_income(
        self,
        ref: MonthRef,
        index: int,
        *,
        name: str | None = None,
        amount: Money | None = None,
    ) -> Changed:
        return self._change(
            ref,
            lambda d: d.month.edit_income(d.income(index), name=name, amount=amount),
        )

    def delete_income(self, ref: MonthRef, index: int) -> Changed:
        return self._change(
            ref, lambda d: d.month.delete_income(d.income(index)), undoable=True
        )

    # ---------------------------------------------------------------------
    # Sections
    # ---------------------------------------------------------------------
    def add_section(
        self,
        ref: MonthRef,
        name: str,
        kind: SectionKind,
        allocation: Money | Percentage,
        routing: RestRouting | None = None,
    ) -> Changed:
        def change(d: _Draft) -> None:
            if isinstance(allocation, Percentage):
                d.month.add_section(
                    name, kind, percentage=allocation, rest_routing=routing
                )
            else:
                d.month.add_section(name, kind, amount=allocation, rest_routing=routing)

        return self._change(ref, change)

    def edit_section(
        self,
        ref: MonthRef,
        index: int,
        *,
        name: str | None = None,
        allocation: Money | Percentage | None = None,
        routing: RestRouting | None = None,
        position: int | None = None,
    ) -> Changed:
        def change(d: _Draft) -> None:
            section = d.section(index)
            d.month.edit_section(
                section.name,
                new_name=name,
                percentage=allocation if isinstance(allocation, Percentage) else None,
                amount=allocation if isinstance(allocation, Money) else None,
                rest_routing=routing,
            )
            if position is not None:
                _move_section(d.month, section, position)

        return self._change(ref, change)

    def delete_section(self, ref: MonthRef, index: int) -> Changed:
        return self._change(
            ref,
            lambda d: d.month.delete_section(d.section(index).name),
            undoable=True,
        )

    # ---------------------------------------------------------------------
    # Fields
    # ---------------------------------------------------------------------
    def add_field(
        self,
        ref: MonthRef,
        section_index: int,
        name: str,
        budget: Money | Percentage,
        cap: Cap,
        *,
        pocket_index: int | None = None,
        current: Money | None = None,
    ) -> Changed:
        def change(d: _Draft) -> None:
            section = d.section(section_index)
            pocket = (
                d.default_pocket() if pocket_index is None else d.pocket(pocket_index)
            )
            if current is not None:
                d.require_first_month()
            d.month.add_field(
                section.name, name, budget, cap, pocket.name, current=current
            )

        return self._change(ref, change)

    def edit_field(
        self,
        ref: MonthRef,
        section_index: int,
        field_index: int,
        *,
        name: str | None = None,
        budget: Money | Percentage | None = None,
        cap: Cap | None = None,
        pocket_index: int | None = None,
        current: Money | None = None,
    ) -> Changed:
        def change(d: _Draft) -> None:
            section, field = d.field(section_index, field_index)
            month, owner, old_name = d.month, section.name, field.name
            if budget is not None:
                month.set_field_budget(owner, old_name, budget)
            if cap is not None:
                month.set_field_cap(owner, old_name, cap)
            if pocket_index is not None:
                month.set_field_pocket(owner, old_name, d.pocket(pocket_index).name)
            if current is not None:
                d.require_first_month()
                month.set_field_current(owner, old_name, current)
            if name is not None:  # last: everything above addresses the old name
                month.rename_field(owner, old_name, name)

        return self._change(ref, change)

    def delete_field(
        self, ref: MonthRef, section_index: int, field_index: int
    ) -> Changed:
        def change(d: _Draft) -> None:
            section, field = d.field(section_index, field_index)
            d.month.delete_field(section.name, field.name)

        return self._change(ref, change, undoable=True)

    # ---------------------------------------------------------------------
    # Transactions / transfers
    # ---------------------------------------------------------------------
    def add_transaction(
        self,
        ref: MonthRef,
        section_index: int,
        field_index: int,
        amount: Money,
        day: int,
        *,
        description: str = "",
        expression: str = "",
    ) -> Changed:
        def change(d: _Draft) -> None:
            section, field = d.field(section_index, field_index)
            d.month.add_transaction(
                section.name,
                field.name,
                day,
                amount,
                description=description,
                amount_expr=expression,
            )

        return self._change(ref, change)

    def edit_transaction(
        self,
        ref: MonthRef,
        number: int,
        *,
        field: tuple[int, int] | None = None,
        amount: Money | None = None,
        expression: str | None = None,
        day: int | None = None,
        description: str | None = None,
    ) -> Changed:
        def change(d: _Draft) -> None:
            target: tuple[str, str] | None = None
            if field is not None:
                section, to_field = d.field(*field)
                target = (section.name, to_field.name)
            d.month.edit_transaction(
                d.transaction(number),
                day=day,
                amount=amount,
                description=description,
                amount_expr=expression,
                field=target,
            )

        return self._change(ref, change)

    def delete_transaction(self, ref: MonthRef, number: int) -> Changed:
        return self._change(
            ref,
            lambda d: d.month.delete_transaction(d.transaction(number)),
            undoable=True,
        )

    def add_transfer(
        self,
        ref: MonthRef,
        source: tuple[int, int],
        target: tuple[int, int],
        amount: Money,
        day: int,
        *,
        note: str = "",
    ) -> Changed:
        def change(d: _Draft) -> None:
            from_section, from_field = d.field(*source)
            to_section, to_field = d.field(*target)
            d.month.transfer(
                from_section.name,
                from_field.name,
                to_section.name,
                to_field.name,
                day,
                amount,
                note=note,
            )

        return self._change(ref, change)

    def delete_transfer(self, ref: MonthRef, number: int) -> Changed:
        return self._change(
            ref,
            lambda d: d.month.delete_transfer(d.transfer(number)),
            undoable=True,
        )

    # ---------------------------------------------------------------------
    # Pockets
    # ---------------------------------------------------------------------
    def add_pocket(self, ref: MonthRef, name: str) -> Changed:
        return self._change(ref, lambda d: d.month.add_pocket(name))

    def edit_pocket(
        self,
        ref: MonthRef,
        index: int,
        *,
        name: str | None = None,
        make_default: bool = False,
    ) -> Changed:
        def change(d: _Draft) -> None:
            pocket = d.pocket(index)
            if make_default:
                d.month.set_default_pocket(pocket.name)
            if name is not None:
                d.month.rename_pocket(pocket.name, name)

        return self._change(ref, change)

    def delete_pocket(self, ref: MonthRef, index: int) -> Changed:
        return self._change(
            ref, lambda d: d.month.delete_pocket(d.pocket(index).name), undoable=True
        )

    # ---------------------------------------------------------------------
    # Closing / undo
    # ---------------------------------------------------------------------
    def close(self, ref: MonthRef) -> MonthView:
        """Close the month and return the new open one."""
        with self._uow_factory() as uow:
            month, _ = self._load(uow, ref.profile_id, ref.key)
            _require_current(month, ref)
            nxt = MonthCloser().close(month)
            uow.months.save(month)
            uow.months.add(nxt)
            uow.commit()
        return self.month(ref.profile_id, nxt.key)

    def undo(self, profile_id: int, key: MonthKey, token: str) -> MonthView:
        """Put the month back as it was before the change ``token`` came from."""
        entry = self._undo.claim(token)
        if entry is None or (entry.before.profile_id, entry.before.key) != (
            profile_id,
            key,
        ):
            raise UndoUnavailableError("that change can no longer be undone")
        with self._uow_factory() as uow:
            month, _ = self._load(uow, profile_id, key)
            # Only the change itself may be reverted: if anything happened
            # after it, restoring the old month would throw that away too.
            if month_revision(month) != entry.revision:
                raise UndoUnavailableError(
                    "the month has changed since, so that can no longer be undone"
                )
            uow.months.save(entry.before)
            uow.commit()
        return self.month(profile_id, key)

    # ---------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------
    def _change(
        self,
        ref: MonthRef,
        change: Callable[[_Draft], object],
        *,
        undoable: bool = False,
    ) -> Changed:
        with self._uow_factory() as uow:
            month, is_first = self._load(uow, ref.profile_id, ref.key)
            _require_current(month, ref)
            before = copy.deepcopy(month) if undoable else None
            change(_Draft(month, is_first))
            uow.months.save(month)
            uow.commit()
        # Re-read rather than trust the in-memory graph: what comes back is what
        # storage holds, in storage order — the same shape every reader sees.
        view = self.month(ref.profile_id, ref.key)
        token = None if before is None else self._undo.remember(before, view.revision)
        return Changed(view, token)

    @staticmethod
    def _load(uow: UnitOfWork, profile_id: int, key: MonthKey) -> tuple[Month, bool]:
        month = uow.months.get(profile_id, key)
        if month is None:
            raise NotFoundError(f"no month {key} for this profile")
        return month, key == min(uow.months.keys(profile_id))

    @staticmethod
    def _profile(uow: UnitOfWork, profile_id: int) -> Profile:
        profile = uow.profiles.get(profile_id)
        if profile is None:
            raise NotFoundError("that profile no longer exists")
        return profile

    @staticmethod
    def _info(uow: UnitOfWork, profile: Profile) -> ProfileInfo:
        assert profile.id is not None  # a stored profile always has an id
        keys = uow.months.keys(profile.id)
        return ProfileInfo(
            profile.id, profile.name, profile.created_at, max(keys) if keys else None
        )
