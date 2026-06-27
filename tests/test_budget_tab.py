"""The Budget tab: section list + drill-in detail render the numbers."""

import asyncio
from datetime import date

from dependency_injector import providers
from rich.console import Console

from monay.bootstrap import build_container
from monay.domain.values import Percentage
from monay.tui.app import Monay
from monay.tui.command_bar import CommandBar
from monay.tui.widgets import section_detail, section_list
from tests.fakes import FixedClock
from tests.fixtures.sample_budget import build_sample


def render_text(renderable) -> str:
    console = Console(no_color=True, width=200)
    with console.capture() as cap:
        console.print(renderable)
    return cap.get()


def _sample():
    m = build_sample()
    m.recompute()
    return m


def test_section_list_shows_avail_rest_and_balance():
    text = render_text(section_list.build(_sample()))
    assert "Bills" in text and "Needs" in text and "Savings" in text
    assert "750.00" in text  # Needs AVAILABLE
    assert "350.00" in text  # Needs REST
    assert "Σ% = 100" in text  # post percentages balance


def test_section_list_post_pool_subtracts_tax_share():
    m = _sample()  # income 2000, Bills (pre 500), Needs/Wants/Savings (post)
    m.add_section("VAT", "tax", percentage=Percentage(10))  # 10% of 2000 fresh = 200
    text = render_text(section_list.build(m))
    assert "tax · 10%" in text  # the new kind renders its share
    assert "post pool 1,300.00" in text  # 2000 − tax 200 − Bills 500


def test_section_list_flags_negative_rest():
    m = _sample()
    m.set_field_budget("Savings", "Investments", "2000")  # blow past the slice
    text = render_text(section_list.build(m))
    assert "⚠" in text  # negative REST chip


def test_section_detail_shows_fields_columns():
    text = render_text(section_detail.build(_sample(), "Needs"))
    assert "Groceries" in text and "Dining" in text
    assert "350.00" in text  # Groceries LEFT
    assert "∞" in text  # Dining's infinite cap
    assert "Budget" in text and "Pocket" in text  # column headers


async def _drive() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())
    async with app.run_test() as pilot:
        for cmd in (
            "profile add Demo",
            "section add post Needs 100%",
            "field add Needs Groceries 300 400",
            "income add Pay 1000",
            "add Groceries 17.06 lunch",
            "open Needs",
        ):
            app.query_one(CommandBar).value = cmd
            await pilot.press("enter")
            await pilot.pause()

        assert service.drilled_section == "Needs"
        assert app.last_status == "info"

        app.query_one(CommandBar).value = "back"
        await pilot.press("enter")
        await pilot.pause()
        assert service.drilled_section is None


def test_budget_tab_drilldown_via_shell():
    asyncio.run(_drive())
