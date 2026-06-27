"""The income pseudo-section: it renders on the Budget tab and drills in (#32).

Income shows as a distinct row above the real sections (carrying total income),
is reachable via ``open income``, and appears even before any section exists. The
name ``income`` is reserved so no real section can shadow it.
"""

import asyncio
from datetime import date

import pytest
from dependency_injector import providers
from rich.console import Console

from monay.bootstrap import build_container
from monay.domain.entities import INCOME_SECTION_NAME, Income, IncomeKind
from monay.domain.errors import ValidationError
from monay.domain.money import Money
from monay.domain.month import Month
from monay.domain.values import MonthKey, Percentage
from monay.tui.app import Monay
from monay.tui.command_bar import CommandBar
from monay.tui.screens.budget import render_budget
from monay.tui.widgets import section_list
from tests.fakes import FixedClock
from tests.fixtures.sample_budget import build_sample


def render_text(renderable) -> str:
    console = Console(no_color=True, width=200)
    with console.capture() as cap:
        console.print(renderable)
    return cap.get()


def _income_only() -> Month:
    """A fresh month with income but no sections yet (the #32 repro)."""
    m = Month(profile_id=1, key=MonthKey(2025, 1))
    m.incomes = [Income("Salary", Money("1000"), IncomeKind.MANUAL, 0)]
    m.recompute()
    return m


# --- rendering ----------------------------------------------------------
def test_income_row_precedes_sections_in_the_list():
    m = build_sample()
    m.recompute()
    text = render_text(section_list.build(m))
    assert "$ income" in text  # the distinct income row
    assert "2,000.00" in text  # total income in its AVAILABLE column
    # the income row comes before the first real section
    assert text.index("$ income") < text.index("Bills")


def test_open_income_lists_each_entry():
    m = build_sample()
    m.recompute()
    text = render_text(render_budget(m, "income"))
    assert "INCOME" in text and "total 2,000.00" in text
    assert "Salary" in text  # the per-entry source name
    assert "manual" in text  # its kind


def test_income_shows_before_any_section_exists():
    text = render_text(render_budget(_income_only(), None))
    assert "$ income" in text and "1,000.00" in text  # income is visible
    assert "No sections yet" in text  # …alongside the nudge to add one


def test_no_sections_no_income_is_just_the_hint():
    m = Month(profile_id=1, key=MonthKey(2025, 1))
    m.recompute()
    text = render_text(render_budget(m, None))
    assert "No sections yet" in text
    assert "$ income" not in text


# --- reserved name ------------------------------------------------------
def test_add_section_rejects_the_reserved_income_name():
    m = build_sample()
    with pytest.raises(ValidationError):
        m.add_section("income", "post", percentage=Percentage(50))
    with pytest.raises(ValidationError):  # case-insensitive
        m.add_section("Income", "post", percentage=Percentage(50))


def test_rename_section_to_income_is_rejected():
    m = build_sample()
    with pytest.raises(ValidationError):
        m.edit_section("Needs", new_name="income")


def test_open_section_stores_canonical_income_name():
    # Any casing drills into the pseudo-section and is stored canonically. The
    # income branch returns before touching the UoW, so no profile is needed.
    service = build_container("sqlite://").app_service()
    for variant in ("INCOME", "Income", "income"):
        service.open_section(variant)
        assert service.drilled_section == INCOME_SECTION_NAME


# --- shell flow ---------------------------------------------------------
async def _drive() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())

    def budget(drill: str | None) -> str:
        month = service.active_month()
        return render_text(render_budget(month, drill, service.currency))

    async with app.run_test() as pilot:
        for cmd in ("profile add Demo", "income add Salary 1000"):
            app.query_one(CommandBar).value = cmd
            await pilot.press("enter")
            await pilot.pause()

        # income is on the Budget tab before any section exists
        text = budget(None)
        assert "$ income" in text and "1,000.00" in text

        # open income drills into the entries
        app.query_one(CommandBar).value = "open income"
        await pilot.press("enter")
        await pilot.pause()
        assert service.drilled_section == "income"
        assert "Salary" in budget(service.drilled_section)

        # adding a section keeps the income row
        for cmd in ("back", "section add post Needs 100%"):
            app.query_one(CommandBar).value = cmd
            await pilot.press("enter")
            await pilot.pause()
        text = budget(None)
        assert "$ income" in text and "Needs" in text


def test_income_section_via_shell():
    asyncio.run(_drive())
