"""Phase 9 — the TUI shell drives a real command and shows the result.

Uses Textual's ``run_test()`` harness against an in-memory DB (no real terminal).
"""

import asyncio
from datetime import date

from dependency_injector import providers

from monay.bootstrap import build_container
from monay.domain.money import Money
from monay.domain.values import MonthKey
from monay.tui.app import Monay
from monay.tui.command_bar import CommandBar
from tests.fakes import FixedClock


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
