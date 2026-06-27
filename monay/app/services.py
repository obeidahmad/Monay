"""``MonayApp`` — the application facade / use-case layer.

Holds the session (current profile + the month being viewed) and depends only on
the ports (``UnitOfWork`` factory + ``Clock``). Each use case opens a UoW, loads
the active month, calls an aggregate mutator (which recomputes + enforces
invariants), saves, and commits. The command layer (``app/commands``) and the
TUI (``tui/``) both drive this object.
"""

from __future__ import annotations

import calendar
from collections.abc import Callable
from dataclasses import dataclass

from monay.app.errors import BadUsageError, NoProfileError
from monay.domain.closing import MonthCloser
from monay.domain.entities import Income, Profile, Transaction
from monay.domain.errors import DuplicateNameError, NotFoundError
from monay.domain.money import Money, Numeric
from monay.domain.month import Month, MonthState
from monay.domain.ports import Clock, UnitOfWork
from monay.domain.values import Cap, MonthKey, Percentage, PercentageInput, RestRouting


def month_label(key: MonthKey) -> str:
    return f"{calendar.month_name[key.month]} {key.year}"


@dataclass(frozen=True)
class MonthSummary:
    key: MonthKey
    state: MonthState
    income: Money
    spent: Money
    leftovers: Money


class MonayApp:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        # session
        self.profile_id: int | None = None
        self.profile_name: str | None = None
        self.currency: str = "€"
        self.viewing: MonthKey | None = None
        self.viewing_closed: bool = False
        # ephemeral UI state (the TUI reads these)
        self.tab: str = "budget"  # active working tab (left pane)
        self.helper_tab: str = "docs"  # active helper tab (right pane)
        self.helpers_visible: bool = True  # is the right (helper) pane shown?
        self.docs_query: str | None = None  # filter for the Docs tab, if any
        self.drilled_section: str | None = None
        self.tx_filter: str | None = None
        self.should_quit: bool = False

    # =====================================================================
    # Profiles
    # =====================================================================
    def create_profile(self, name: str, first_month: MonthKey | None = None) -> Profile:
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
        self._select(profile)
        self.viewing, self.viewing_closed = first, False
        return profile

    def switch_profile(self, name: str) -> Profile:
        with self._uow_factory() as uow:
            p = uow.profiles.by_name(name)
            if p is None:
                raise NotFoundError(f"no profile named {name!r}")
            assert p.id is not None  # a stored profile always has an id
            keys = uow.months.keys(p.id)
        self._select(p)
        self.viewing, self.viewing_closed = (max(keys) if keys else None), False
        return p

    def rename_profile(self, new_name: str) -> None:
        pid = self._require_profile()
        with self._uow_factory() as uow:
            if uow.profiles.by_name(new_name) is not None:
                raise DuplicateNameError(f"a profile named {new_name!r} already exists")
            p = uow.profiles.get(pid)
            assert p is not None  # the active profile exists in storage
            p.name = new_name
            uow.profiles.update(p)
            uow.commit()
        self.profile_name = new_name

    def set_currency(self, symbol: str) -> None:
        pid = self._require_profile()
        with self._uow_factory() as uow:
            p = uow.profiles.get(pid)
            assert p is not None  # the active profile exists in storage
            p.currency_symbol = symbol
            uow.profiles.update(p)
            uow.commit()
        self.currency = symbol

    def delete_profile(self, name: str) -> Profile:
        with self._uow_factory() as uow:
            p = uow.profiles.by_name(name)
            if p is None:
                raise NotFoundError(f"no profile named {name!r}")
            assert p.id is not None  # a stored profile always has an id
            uow.profiles.delete(p.id)
            uow.commit()
            remaining = uow.profiles.all()
        if self.profile_id == p.id:
            self.profile_id = self.profile_name = self.viewing = None
            if remaining:
                self.switch_profile(remaining[0].name)
        return p

    def list_profiles(self) -> list[Profile]:
        with self._uow_factory() as uow:
            return uow.profiles.all()

    def resume(self) -> bool:
        """On launch, auto-select an existing profile + its open month.

        Returns True if a profile was selected; with none, the app stays on the
        "create a profile" prompt. (A full multi-profile startup picker is the
        Phase 13 onboarding work; for now we select the first profile.)
        """
        if self.profile_id is not None:
            return True
        with self._uow_factory() as uow:
            profiles = uow.profiles.all()
        if not profiles:
            return False
        self.switch_profile(profiles[0].name)
        return True

    def _select(self, profile: Profile) -> None:
        self.profile_id = profile.id
        self.profile_name = profile.name
        self.currency = profile.currency_symbol

    # =====================================================================
    # Month context
    # =====================================================================
    def active_month(self) -> Month:
        with self._uow_factory() as uow:
            return self._load_active(uow)

    def view_month(self, key_text: str) -> tuple[MonthKey, bool]:
        key = MonthKey.from_string(key_text)
        with self._uow_factory() as uow:
            m = uow.months.get(self._require_profile(), key)
            if m is None:
                raise NotFoundError(f"no month {key} for this profile")
            closed = m.is_closed
        self.viewing, self.viewing_closed = key, closed
        return key, closed

    def view_open_month(self) -> MonthKey:
        with self._uow_factory() as uow:
            key = self._open_key(uow)
        self.viewing, self.viewing_closed = key, False
        return key

    def history(self) -> list[MonthKey]:
        with self._uow_factory() as uow:
            return sorted(uow.months.keys(self._require_profile()), reverse=True)

    def month_summaries(self) -> list[MonthSummary]:
        """One summary per month, newest first (for the History tab)."""
        out: list[MonthSummary] = []
        pid = self._require_profile()
        with self._uow_factory() as uow:
            for key in sorted(uow.months.keys(pid), reverse=True):
                m = uow.months.get(pid, key)
                assert m is not None  # key came from this profile's month list
                spent = sum(
                    (f.paid for s in m.sections for f in s.fields), Money.zero()
                )
                leftovers = sum(
                    (s.rest for s in m.sections if s.rest_routing.is_income),
                    Money.zero(),
                )
                out.append(MonthSummary(key, m.state, m.total_income, spent, leftovers))
        return out

    # =====================================================================
    # Transactions / transfers
    # =====================================================================
    def add_transaction(
        self, field_name: str, amount: Money, day: int | None, description: str = ""
    ) -> Month:
        def fn(m: Month) -> None:
            section, _ = m.locate_field(field_name)
            m.add_transaction(
                section,
                field_name,
                self._resolve_day(m, day),
                amount,
                description=description,
            )

        return self._mutate(fn)

    def transfer(
        self,
        amount: Money,
        from_field: str,
        to_field: str,
        day: int | None,
        note: str = "",
    ) -> Month:
        def fn(m: Month) -> None:
            fs, _ = m.locate_field(from_field)
            ts, _ = m.locate_field(to_field)
            m.transfer(
                fs,
                from_field,
                ts,
                to_field,
                self._resolve_day(m, day),
                amount,
                note=note,
            )

        return self._mutate(fn)

    def edit_transaction(
        self,
        index: int,
        *,
        amount: Money | None = None,
        day: int | None = None,
        description: str | None = None,
    ) -> Month:
        return self._mutate(
            lambda m: m.edit_transaction(
                self._tx_at(m, index), amount=amount, day=day, description=description
            )
        )

    def delete_transaction(self, index: int) -> Month:
        return self._mutate(lambda m: m.delete_transaction(self._tx_at(m, index)))

    # =====================================================================
    # Fields
    # =====================================================================
    def add_field(self, section: str, name: str, budget: Money, cap: Cap) -> Month:
        return self._mutate(
            lambda m: m.add_field(section, name, budget, cap, self._default_pocket(m))
        )

    def set_field_budget(self, name: str, budget: Money) -> Month:
        return self._mutate(
            lambda m: m.set_field_budget(self._sec(m, name), name, budget)
        )

    def set_field_cap(self, name: str, cap: Cap) -> Month:
        return self._mutate(lambda m: m.set_field_cap(self._sec(m, name), name, cap))

    def set_field_pocket(self, name: str, pocket: str) -> Month:
        return self._mutate(
            lambda m: m.set_field_pocket(self._sec(m, name), name, pocket)
        )

    def rename_field(self, name: str, new_name: str) -> Month:
        return self._mutate(
            lambda m: m.rename_field(self._sec(m, name), name, new_name)
        )

    def delete_field(self, name: str) -> Month:
        return self._mutate(lambda m: m.delete_field(self._sec(m, name), name))

    def set_field_current(self, name: str, current: Money) -> Month:
        pid = self._require_profile()
        with self._uow_factory() as uow:
            m = self._load_active(uow)
            if m.key != min(uow.months.keys(pid)):
                raise BadUsageError(
                    "CURRENT can only be set in the first month; "
                    "afterwards it carries automatically"
                )
            section, _ = m.locate_field(name)
            m.set_field_current(section, name, current)
            uow.months.save(m)
            uow.commit()
            return m

    # =====================================================================
    # Sections / income / pockets
    # =====================================================================
    def add_section(
        self,
        kind: str,
        name: str,
        *,
        percentage: Percentage | PercentageInput | None = None,
        amount: Money | Numeric | None = None,
    ) -> Month:
        return self._mutate(
            lambda m: m.add_section(name, kind, percentage=percentage, amount=amount)
        )

    def set_section_pct(
        self, name: str, percentage: Percentage | PercentageInput
    ) -> Month:
        return self._mutate(lambda m: m.edit_section(name, percentage=percentage))

    def set_section_amount(self, name: str, amount: Money | Numeric) -> Month:
        return self._mutate(lambda m: m.edit_section(name, amount=amount))

    def rename_section(self, name: str, new_name: str) -> Month:
        return self._mutate(lambda m: m.edit_section(name, new_name=new_name))

    def set_section_routing(self, name: str, routing: RestRouting) -> Month:
        return self._mutate(lambda m: m.edit_section(name, rest_routing=routing))

    def order_section(self, name: str, position: int) -> Month:
        return self._mutate(lambda m: m.edit_section(name, position=position))

    def delete_section(self, name: str) -> Month:
        return self._mutate(lambda m: m.delete_section(name))

    def add_income(self, name: str, amount: Money) -> Month:
        return self._mutate(lambda m: m.add_income(name, amount))

    def set_income(
        self,
        name: str,
        *,
        new_name: str | None = None,
        amount: Money | Numeric | None = None,
    ) -> Month:
        return self._mutate(
            lambda m: m.edit_income(self._income(m, name), name=new_name, amount=amount)
        )

    def delete_income(self, name: str) -> Month:
        return self._mutate(lambda m: m.delete_income(self._income(m, name)))

    def add_pocket(self, name: str) -> Month:
        return self._mutate(lambda m: m.add_pocket(name))

    def rename_pocket(self, old: str, new: str) -> Month:
        return self._mutate(lambda m: m.rename_pocket(old, new))

    def delete_pocket(self, name: str) -> Month:
        return self._mutate(lambda m: m.delete_pocket(name))

    def set_main_pocket(self, name: str) -> Month:
        return self._mutate(lambda m: m.set_default_pocket(name))

    # =====================================================================
    # Closing
    # =====================================================================
    def close_summary(self) -> str:
        m = self.active_month()
        m.assert_operable()
        leftovers = sum(
            (s.rest for s in m.sections if s.rest_routing.is_income), Money.zero()
        )
        carries = [
            f"{s.name} REST {s.rest.display()} carries"
            for s in m.sections
            if not s.rest_routing.is_income and not s.rest.is_zero
        ]
        tail = ("; " + "; ".join(carries)) if carries else ""
        return (
            f"⚠ Close {month_label(m.key)} forever? Leftovers {leftovers.display()} "
            f"→ {month_label(m.key.next())}{tail}."
        )

    def close_active(self) -> Month:
        self._require_profile()
        with self._uow_factory() as uow:
            m = self._load_active(uow)
            nxt = MonthCloser().close(m)
            uow.months.save(m)
            uow.months.add(nxt)
            uow.commit()
        self.viewing, self.viewing_closed = nxt.key, False
        return nxt

    # =====================================================================
    # Navigation (UI state)
    # =====================================================================
    def goto(self, tab: str) -> None:
        # Route by which pane owns the tab: helper tabs live in the right pane.
        if tab in ("docs", "history"):
            self.helper_tab = tab
            self.helpers_visible = True
            if tab == "docs":
                self.docs_query = None  # navigating to Docs shows the full reference
        else:
            self.tab = tab

    def show_docs(self, query: str | None = None) -> None:
        self.helper_tab = "docs"
        self.helpers_visible = True
        self.docs_query = query

    def set_tx_filter(self, text: str | None) -> None:
        self.tx_filter = text or None
        self.tab = "transactions"

    def open_section(self, name: str) -> None:
        with self._uow_factory() as uow:
            self._load_active(uow).section(name)  # raises NotFoundError if missing
        self.drilled_section = name

    def back(self) -> None:
        self.drilled_section = None

    def quit(self) -> None:
        self.should_quit = True

    # =====================================================================
    # Internals
    # =====================================================================
    def _mutate(self, fn: Callable[[Month], object]) -> Month:
        self._require_profile()
        with self._uow_factory() as uow:
            m = self._load_active(uow)
            fn(m)
            uow.months.save(m)
            uow.commit()
            return m

    def _load_active(self, uow: UnitOfWork) -> Month:
        key = self.viewing or self._open_key(uow)
        m = uow.months.get(self._require_profile(), key)
        if m is None:
            raise NotFoundError(f"no month {key}")
        return m

    def _open_key(self, uow: UnitOfWork) -> MonthKey:
        keys = uow.months.keys(self._require_profile())
        if not keys:
            raise NotFoundError("this profile has no months")
        return max(keys)

    def _resolve_day(self, month: Month, day: int | None) -> int:
        if day is not None:
            return day
        today = self._clock.today()
        if month.key == MonthKey.from_date(today):
            return today.day
        raise BadUsageError(
            "this isn't the current calendar month — give a day like d5"
        )

    def _require_profile(self) -> int:
        if self.profile_id is None:
            raise NoProfileError("no profile yet — create one with: profile add <name>")
        return self.profile_id

    @staticmethod
    def _sec(month: Month, field_name: str) -> str:
        section_name, _ = month.locate_field(field_name)
        return section_name

    @staticmethod
    def _default_pocket(month: Month) -> str:
        p = next((p for p in month.pockets if p.is_default), None)
        if p is None:
            raise BadUsageError("no default pocket — add one with: pocket add Main")
        return p.name

    @staticmethod
    def _tx_at(month: Month, index: int) -> Transaction:
        if index < 1 or index > len(month.transactions):
            raise BadUsageError(f"no transaction #{index}")
        return month.transactions[index - 1]

    @staticmethod
    def _income(month: Month, name: str) -> Income:
        for inc in month.incomes:
            if inc.name == name:
                return inc
        raise NotFoundError(f"no income named {name!r}")
