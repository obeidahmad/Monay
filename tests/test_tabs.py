"""The remaining tabs + the full "usable v0" loop, end to end."""

import asyncio
from datetime import date

from dependency_injector import providers
from rich.console import Console

from monay.app.services import MonthSummary
from monay.bootstrap import build_container
from monay.domain.money import Money
from monay.domain.month import MonthState
from monay.domain.values import MonthKey
from monay.tui.app import Monay
from monay.tui.command_bar import CommandBar
from monay.tui.screens.history import render_history
from monay.tui.screens.pockets import render_pockets
from monay.tui.screens.transactions import render_transactions
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


def test_transactions_tab():
    text = render_text(render_transactions(_sample(), None))
    assert "Groceries" in text and "Dining" in text
    assert "250.00" in text  # the Dining transaction
    assert "Needs" in text  # section column
    assert "Description" in text


def test_transactions_filter():
    text = render_text(render_transactions(_sample(), "dining"))
    assert "Dining" in text and "250.00" in text
    assert "Groceries" not in text  # filtered out


def test_pockets_tab():
    text = render_text(render_pockets(_sample()))
    assert "Main" in text and "Bank" in text and "Broker" in text
    assert "Investments" in text  # Broker's breakdown
    assert "RESTs" in text  # default pocket carries live RESTs


def test_history_tab():
    summaries = [
        MonthSummary(MonthKey(2025, 2), MonthState.OPEN, Money("2000"), Money("0"), Money("0")),
        MonthSummary(MonthKey(2025, 1), MonthState.CLOSED, Money("2000"), Money("750"), Money("650")),
    ]
    text = render_text(render_history(summaries, MonthKey(2025, 2)))
    assert "2025-02" in text and "2025-01" in text
    assert "open" in text and "closed" in text
    assert "650.00" in text


async def _full_loop() -> None:
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    service = container.app_service()
    app = Monay(service, container.registry())

    setup = [
        "profile add Demo",
        "section add post Needs 50%",
        "section add post Wants 30%",
        "section add post Savings 20%",
        "field add Needs Groceries 300 400",
        "field add Savings Stock 70 inf",
        "field add Savings Cash 0 inf",
        "income add Salary 1000",
        "field set Stock current 100",  # first-month hand entry
        "field set Cash current 50",
        "add Groceries 17.06 lunch",
        "transfer 10 Cash Stock",
        "goto transactions",
        "goto pockets",
        "goto history",
        "goto settings",
        "goto budget",
        "open Needs",
        "back",
    ]

    async def run(cmd):
        app.query_one(CommandBar).value = cmd
        await pilot.press("enter")
        await pilot.pause()

    async with app.run_test() as pilot:
        for cmd in setup:
            await run(cmd)
            assert app.last_status != "error", f"{cmd!r}: {app.last_feedback}"

        m = service.active_month()
        assert m.field("Needs", "Groceries").paid == Money("17.06")
        assert m.field("Savings", "Cash").left == Money("40")  # 50 - 10 transferred
        assert m.field("Savings", "Stock").left == Money("180")  # 100 + 70 + 10

        await run("close")
        assert app.last_status == "confirm"
        await run("Yes")
        assert service.viewing == MonthKey(2025, 2)

        assert len(service.month_summaries()) == 2
        await run("month 2025-01")
        assert service.viewing_closed
        await run("add Groceries 5")  # editing a closed month is rejected
        assert app.last_status == "error"


def test_usable_v0_full_loop():
    asyncio.run(_full_loop())