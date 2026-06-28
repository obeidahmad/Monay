"""The Budget tab: the accordion renders summary rows and inline field tables."""

import asyncio
from datetime import date

from dependency_injector import providers
from rich.console import Console

from monay.bootstrap import build_container
from monay.domain.values import Percentage
from monay.tui.app import Monay
from monay.tui.command_bar import CommandBar
from monay.tui.widgets import accordion
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


def test_accordion_shows_avail_rest_and_balance():
    text = render_text(accordion.build(_sample(), set()))
    assert "Bills" in text and "Needs" in text and "Savings" in text
    assert "750.00" in text  # Needs AVAILABLE
    assert "350.00" in text  # Needs REST
    assert "Σ% = 100" in text  # post percentages balance


def test_accordion_post_pool_subtracts_tax_share():
    m = _sample()  # income 2000, Bills (pre 500), Needs/Wants/Savings (post)
    m.add_section("VAT", "tax", percentage=Percentage(10))  # 10% of 2000 fresh = 200
    m.recompute()
    text = render_text(accordion.build(m, set()))
    assert "tax · 10%" in text  # the new kind renders its share
    assert "post pool 1,300.00" in text  # 2000 − tax 200 − Bills 500


def test_accordion_flags_negative_rest():
    m = _sample()
    m.set_field_budget("Savings", "Investments", "2000")  # blow past the slice
    text = render_text(accordion.build(m, set()))
    assert "⚠" in text  # negative REST chip


def test_collapsed_section_hides_its_fields():
    text = render_text(accordion.build(_sample(), set()))
    assert "Needs" in text  # the summary row is always visible
    assert "Groceries" not in text  # …but its fields are not, while collapsed


def test_expanded_section_shows_fields_columns_inline():
    text = render_text(accordion.build(_sample(), {"Needs"}))
    assert "Groceries" in text and "Dining" in text
    assert "350.00" in text  # Groceries LEFT
    assert "∞" in text  # Dining's infinite cap
    assert "Budget" in text and "Pocket" in text  # column headers


def test_multiple_sections_expand_at_once():
    # Two sections open together: every other summary row stays visible, and the
    # fields of both expanded sections render — the whole point of the accordion.
    text = render_text(accordion.build(_sample(), {"Needs", "Bills"}))
    assert "Groceries" in text  # a Needs field
    assert "Utilities" in text  # a Bills field
    assert "Savings" in text  # the still-collapsed section's summary row


def test_stale_expansion_is_pruned():
    # A section expanded, then renamed, must not keep rendering expanded under its
    # old name — build() prunes names that no longer match a real section.
    m = _sample()
    m.edit_section("Needs", new_name="Essentials")
    m.recompute()
    text = render_text(accordion.build(m, {"Needs"}))  # stale: "Needs" is gone
    assert "Essentials" in text  # the section renders under its new name…
    assert "▼ ▍Essentials" not in text  # …collapsed, not expanded
    assert "Groceries" not in text  # and its fields are not shown


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
            "expand Needs",
        ):
            app.query_one(CommandBar).value = cmd
            await pilot.press("enter")
            await pilot.pause()

        assert service.expanded_sections == {"Needs"}
        assert app.last_status == "info"

        app.query_one(CommandBar).value = "collapse"
        await pilot.press("enter")
        await pilot.pause()
        assert service.expanded_sections == set()


def test_budget_tab_expand_collapse_via_shell():
    asyncio.run(_drive())


async def _click_cell(pilot, app, action_fragment: str) -> bool:
    """Click the content cell whose meta carries a key named ``action_fragment``.

    Locating the cell by its meta (rather than hard-coded coordinates) keeps the
    test robust to layout, while still exercising the real mouse → meta → on_click
    path that a user's click goes through.
    """
    from textual.widgets import Static

    content = app.query_one("#content", Static)
    reg = content.region
    for sy in range(reg.y, reg.y + reg.height):
        for sx in range(reg.x, reg.x + reg.width):
            if action_fragment in app.screen.get_style_at(sx, sy).meta:
                await pilot.click(content, offset=(sx - reg.x, sy - reg.y))
                await pilot.pause()
                return True
    return False


async def _click_toggles() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())
    async with app.run_test() as pilot:
        for cmd in (
            "profile add Demo",
            "section add post Needs 100%",
            "field add Needs Groceries 300 400",
        ):
            app.query_one(CommandBar).value = cmd
            await pilot.press("enter")
            await pilot.pause()

        # clicking the section row expands it, and clicking again collapses it
        assert await _click_cell(pilot, app, "toggle_section")
        assert service.expanded_sections == {"Needs"}
        assert await _click_cell(pilot, app, "toggle_section")
        assert service.expanded_sections == set()


def test_clicking_a_row_toggles_it():
    asyncio.run(_click_toggles())


async def _click_income() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())
    async with app.run_test() as pilot:
        for cmd in ("profile add Demo", "income add Pay 1000"):
            app.query_one(CommandBar).value = cmd
            await pilot.press("enter")
            await pilot.pause()

        # the income row uses its own action/handler (toggle_income), so cover it too
        assert await _click_cell(pilot, app, "toggle_income")
        assert service.expanded_sections == {"income"}
        assert await _click_cell(pilot, app, "toggle_income")
        assert service.expanded_sections == set()


def test_clicking_the_income_row_toggles_it():
    asyncio.run(_click_income())


async def _collapse_one_vs_all() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())
    async with app.run_test() as pilot:
        for cmd in (
            "profile add Demo",
            "section add post Needs 50%",
            "section add post Wants 50%",
            "expand Needs",
            "expand Wants",
        ):
            app.query_one(CommandBar).value = cmd
            await pilot.press("enter")
            await pilot.pause()
        assert service.expanded_sections == {"Needs", "Wants"}

        # collapse <section> closes only that one
        app.query_one(CommandBar).value = "collapse Needs"
        await pilot.press("enter")
        await pilot.pause()
        assert service.expanded_sections == {"Wants"}

        # bare collapse closes everything
        app.query_one(CommandBar).value = "collapse"
        await pilot.press("enter")
        await pilot.pause()
        assert service.expanded_sections == set()


def test_collapse_one_then_all():
    asyncio.run(_collapse_one_vs_all())


async def _expand_all() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())
    async with app.run_test() as pilot:
        for cmd in (
            "profile add Demo",
            "income add Pay 1000",
            "section add post Needs 50%",
            "section add post Wants 50%",
            "expand",  # no name: open every row, like bare collapse closes every row
        ):
            app.query_one(CommandBar).value = cmd
            await pilot.press("enter")
            await pilot.pause()
        assert service.expanded_sections == {"income", "Needs", "Wants"}
        assert app.last_status == "info"


def test_expand_all():
    asyncio.run(_expand_all())
