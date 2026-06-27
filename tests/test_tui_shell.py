"""Phase 9 — the TUI shell drives a real command and shows the result.

Uses Textual's ``run_test()`` harness against an in-memory DB (no real terminal).
"""

import asyncio
from datetime import date

from dependency_injector import providers
from rich.console import Console
from textual.containers import VerticalScroll

from monay.bootstrap import build_container
from monay.domain.money import Money
from monay.domain.values import MonthKey
from monay.tui.app import Monay
from monay.tui.command_bar import CommandBar
from monay.tui.widgets.divider import PaneDivider
from tests.fakes import FixedClock


def render_text(renderable) -> str:
    console = Console(no_color=True, width=200)
    with console.capture() as cap:
        console.print(renderable)
    return cap.get()


async def _type(pilot, app, text: str) -> None:
    app.query_one(CommandBar).value = text
    await pilot.press("enter")
    await pilot.pause()


async def _scenario() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())

    async with app.run_test() as pilot:
        # a command mutates state and the feedback line reports it
        await _type(pilot, app, "profile add Demo")
        assert service.profile_name == "Demo"
        assert "Demo" in app.last_feedback
        assert "Demo" in app.last_context

        # an unknown command shows a red error
        await _type(pilot, app, "frobnicate")
        assert app.last_status == "error"
        assert "unknown" in app.last_feedback.lower()

        # building structure works through the shell
        await _type(pilot, app, "section add post Need 100%")
        await _type(pilot, app, "field add Need Food 300 400")
        await _type(pilot, app, "income add Pay 1000")
        await _type(pilot, app, "add Food 17.06 lunch")
        assert service.active_month().field("Need", "Food").paid == Money("17.06")

        # navigation command switches the active tab
        await _type(pilot, app, "goto pockets")
        assert service.tab == "pockets"

        # a confirmation: first a prompt, then Yes runs it
        await _type(pilot, app, "close")
        assert app.last_status == "confirm"
        assert "Yes or No" in app.last_feedback
        await _type(pilot, app, "Yes")
        assert service.viewing == MonthKey(2025, 2)  # advanced to the next month

        # quit
        await _type(pilot, app, "quit")
        assert service.should_quit is True


def test_shell_command_loop():
    asyncio.run(_scenario())


async def _overflow_scenario() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())

    async with app.run_test() as pilot:  # default 80x24 virtual terminal
        for cmd in (
            "profile add Demo",
            "section add post Need 100%",
            "field add Need Food 300 400",
            "income add Pay 1000",
        ):
            await _type(pilot, app, cmd)
        # add many more transactions than fit in 24 rows
        for n in range(40):
            await _type(pilot, app, f"add Food 1 item{n}")
        await _type(pilot, app, "goto transactions")

        scroll = app.query_one("#content-scroll", VerticalScroll)
        # content is taller than the viewport, so the area can scroll to reach it
        assert scroll.max_scroll_y > 0

        # scroll to the bottom, then switching tabs and back resets to the top
        scroll.scroll_end(animate=False)
        await pilot.pause()
        assert scroll.scroll_y > 0
        await _type(pilot, app, "goto budget")
        await _type(pilot, app, "goto transactions")
        assert scroll.scroll_y == 0


def test_overflowing_content_is_scrollable():
    asyncio.run(_overflow_scenario())


async def _help_scenario() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())

    async with app.run_test() as pilot:
        right = app.query_one("#right-pane")

        # `help` selects the Docs tab and keeps the feedback line to one line
        # (the original bug dumped the multi-line reference into #feedback).
        await _type(pilot, app, "help")
        assert service.helper_tab == "docs"
        assert service.helpers_visible is True
        assert app.last_status == "info"
        assert "\n" not in app.last_feedback
        # the full reference renders in the right pane, unclipped
        shown = render_text(app._helper_renderable())
        for cmd in ("add", "transfer", "section add", "quit"):
            assert cmd in shown

        # `help <query>` filters the Docs view
        await _type(pilot, app, "help pocket")
        assert service.docs_query == "pocket"
        assert "transfer" not in render_text(app._helper_renderable())

        # navigating to Docs clears the filter and shows the full reference again
        await _type(pilot, app, "goto docs")
        assert service.docs_query is None
        assert "transfer" in render_text(app._helper_renderable())

        # an unknown query is a one-line error, not a tab switch
        await _type(pilot, app, "help nope")
        assert app.last_status == "error"

        # ctrl+b toggles the right (helper) pane
        assert not right.has_class("hidden")
        app.action_toggle_helpers()
        await pilot.pause()
        assert right.has_class("hidden")
        app.action_toggle_helpers()
        await pilot.pause()
        assert not right.has_class("hidden")


def test_help_opens_docs_tab():
    asyncio.run(_help_scenario())


async def _resize_scenario() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())

    async with app.run_test() as pilot:
        right = app.query_one("#right-pane")
        divider = app.query_one("#divider")

        # keyboard resize grows then shrinks the helper pane
        start = app._helper_width
        app.action_resize_helper(4)
        assert app._helper_width == start + 4
        app.action_resize_helper(-2)
        assert app._helper_width == start + 2

        # dragging the divider right shrinks the pane (opposite of the delta)
        before = app._helper_width
        app.on_pane_divider_dragged(PaneDivider.Dragged(3))
        assert app._helper_width == before - 3

        # clamps: a huge grow caps below the panes width; a huge shrink floors out
        panes = app.query_one("#panes").size.width
        app.action_resize_helper(10_000)
        assert app._helper_width == max(app.MIN_HELPER, panes - app.MIN_WORKING - 1)
        app.action_resize_helper(-10_000)
        assert app._helper_width == app.MIN_HELPER

        # ctrl+b hides both the pane and the divider
        app.action_toggle_helpers()
        await pilot.pause()
        assert right.has_class("hidden") and divider.has_class("hidden")


def test_helper_pane_is_resizable():
    asyncio.run(_resize_scenario())
