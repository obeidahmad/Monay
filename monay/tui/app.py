"""``Monay`` — the Textual app shell (docs/DEVELOPING.md).

A context bar (month · state · profile), a two-pane body, a feedback line, and the
command bar. The body splits into a **left pane** of working tabs (budget,
transactions, pockets, settings) and a **right pane** of helper tabs (docs,
history); ``ctrl+b`` toggles the right pane. The shell parses each command through
the registry, runs it against the ``MonayApp`` service, and shows the result.
Typed ``Yes``/``No`` answers a pending confirmation.
"""

from __future__ import annotations

from rich.console import RenderableType
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, Static, Tab, Tabs

from monay.app.commands import CommandRegistry, Result
from monay.app.services import MonayApp, month_label
from monay.domain.errors import MonayError
from monay.tui import theme
from monay.tui.command_bar import CommandBar
from monay.tui.screens.budget import render_budget
from monay.tui.screens.docs import render_docs
from monay.tui.screens.history import render_history
from monay.tui.screens.pockets import render_pockets
from monay.tui.screens.settings import render_settings
from monay.tui.screens.transactions import render_transactions
from monay.tui.widgets.divider import PaneDivider

_WORKING_TABS = ("budget", "transactions", "pockets", "settings")  # left pane
_HELPER_TABS = ("docs", "history")  # right pane


class Monay(App[None]):
    # Helper pane width (cells) and the minimum widths the resize keeps free.
    # HELPER_WIDTH is the single source of the starting split (used in CSS below
    # and as the initial _helper_width), so the two can't drift.
    HELPER_WIDTH = 40
    MIN_HELPER = 24
    MIN_WORKING = 30

    CSS = f"""
    Screen {{ background: {theme.BG}; }}
    #context {{
        height: 1; background: {theme.PANEL}; color: {theme.TEXT}; padding: 0 1;
    }}
    Tabs {{ background: {theme.TABS_BG}; }}
    #panes {{ height: 1fr; }}
    #left-pane {{ width: 1fr; }}
    #right-pane {{ width: {HELPER_WIDTH}; }}
    #right-pane.hidden, #divider.hidden {{ display: none; }}
    #divider {{ width: 1; height: 1fr; background: {theme.PANEL}; }}
    #divider:hover {{ background: {theme.INFO}; }}
    #content-scroll, #helper-scroll {{ height: 1fr; }}
    #content, #helper-content {{ height: auto; padding: 1 2; color: {theme.TEXT}; }}
    #helper-hint {{ height: 1; padding: 0 1; color: {theme.TEXT}; text-style: dim; }}
    #feedback {{ height: 1; padding: 0 1; color: {theme.OK}; }}
    #feedback.error {{ color: {theme.ERROR}; }}
    #feedback.confirm {{ color: {theme.WARN}; }}
    #feedback.info {{ color: {theme.INFO}; }}
    CommandBar {{ border: round {theme.PANEL}; }}
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+b", "toggle_helpers", "Helpers", priority=True),
        Binding("ctrl+left", "resize_helper(2)", "Wider helpers", priority=True),
        Binding("ctrl+right", "resize_helper(-2)", "Narrower helpers", priority=True),
    ]

    def __init__(self, service: MonayApp, registry: CommandRegistry) -> None:
        super().__init__()
        self._service = service
        self._commands = registry
        self._pending: str | None = None
        self._helper_width: int = self.HELPER_WIDTH  # right-pane width (resizable)
        # last rendered text (handy for tests / introspection)
        self.last_feedback: str = ""
        self.last_status: str = ""
        self.last_context: str = ""

    def compose(self) -> ComposeResult:
        yield Static(id="context")
        with Horizontal(id="panes"):
            with Vertical(id="left-pane"):
                yield Tabs(*(Tab(t.title(), id=t) for t in _WORKING_TABS), id="tabs")
                with VerticalScroll(id="content-scroll"):
                    yield Static(id="content")
            yield PaneDivider(id="divider")
            with Vertical(id="right-pane"):
                yield Tabs(
                    *(Tab(t.title(), id=t) for t in _HELPER_TABS), id="helper-tabs"
                )
                with VerticalScroll(id="helper-scroll"):
                    yield Static(id="helper-content")
                yield Static("Ctrl+←/→ resize · Ctrl+B hide", id="helper-hint")
        yield Static(id="feedback")
        yield CommandBar(id="command")

    def on_mount(self) -> None:
        self.query_one(CommandBar).focus()
        self._service.resume()  # re-select an existing profile + its open month
        self._refresh()

    # --- command loop -----------------------------------------------------
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        self.query_one(CommandBar).value = ""
        if not text:
            return
        if self._pending is not None:
            self._answer_confirmation(text)
            return
        self.query_one(CommandBar).remember(text)
        result = self._commands.execute(self._service, text)
        if result.status == "confirm":
            self._pending = result.pending
        self._after(result)

    def _answer_confirmation(self, text: str) -> None:
        pending, self._pending = self._pending, None
        assert pending is not None  # only entered while a confirmation is pending
        if text == "Yes":
            result = self._commands.execute(self._service, pending, confirmed=True)
        elif text == "No":
            result = Result.info("cancelled")
        else:
            self._pending = pending  # keep waiting for an exact Yes/No
            result = Result.info("please type exactly Yes or No")
        self._after(result)

    def _after(self, result: Result) -> None:
        self._show(result)
        self._refresh()
        if self._service.should_quit:
            self.exit()

    # --- rendering --------------------------------------------------------
    def action_toggle_helpers(self) -> None:
        self._service.helpers_visible = not self._service.helpers_visible
        self._refresh()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab is None or event.tab.id is None:
            return
        if event.tabs.id == "helper-tabs":
            self._service.helper_tab = event.tab.id
            self.query_one("#helper-content", Static).update(self._helper_renderable())
            self.query_one("#helper-scroll", VerticalScroll).scroll_home(animate=False)
        else:
            self._service.tab = event.tab.id
            self.query_one("#content", Static).update(self._content_renderable())
            self.query_one("#content-scroll", VerticalScroll).scroll_home(animate=False)

    def _refresh(self) -> None:
        self.last_context = self._context_text()
        self.query_one("#context", Static).update(self.last_context)
        self.query_one("#content", Static).update(self._content_renderable())
        self.query_one("#helper-content", Static).update(self._helper_renderable())
        tabs = self.query_one("#tabs", Tabs)
        if tabs.active != self._service.tab:
            tabs.active = self._service.tab
        helper_tabs = self.query_one("#helper-tabs", Tabs)
        if helper_tabs.active != self._service.helper_tab:
            helper_tabs.active = self._service.helper_tab
        hidden = not self._service.helpers_visible
        self.query_one("#right-pane").set_class(hidden, "hidden")
        self.query_one("#divider").set_class(hidden, "hidden")

    # --- resizable helper pane -------------------------------------------
    def _set_helper_width(self, width: int) -> None:
        panes = self.query_one("#panes").size.width
        if panes <= 0:
            return  # not laid out yet; a later resize will clamp correctly
        max_w = max(self.MIN_HELPER, panes - self.MIN_WORKING - 1)  # -1: the divider
        self._helper_width = max(self.MIN_HELPER, min(width, max_w))
        self.query_one("#right-pane").styles.width = self._helper_width

    def action_resize_helper(self, delta: int) -> None:
        self._set_helper_width(self._helper_width + delta)

    def on_pane_divider_dragged(self, event: PaneDivider.Dragged) -> None:
        # The divider moving right shrinks the right pane, and vice versa.
        self._set_helper_width(self._helper_width - event.delta)

    def on_resize(self, event: events.Resize) -> None:
        # Keep the split valid when the terminal itself is resized.
        self._set_helper_width(self._helper_width)

    def _show(self, result: Result) -> None:
        fb = self.query_one("#feedback", Static)
        fb.remove_class("error", "confirm", "info")
        if result.status in ("error", "confirm", "info"):
            fb.add_class(result.status)
        prefix = "✗ " if result.status == "error" else ""
        self.last_status = result.status
        self.last_feedback = prefix + result.message
        fb.update(self.last_feedback)

    def _context_text(self) -> str:
        s = self._service
        if s.profile_id is None:
            return "No profile — type:  profile add <name>"
        if s.viewing is None:
            return f"Profile: {s.profile_name}"
        state = "🔒 closed" if s.viewing_closed else "● open"
        return f"{month_label(s.viewing)}   {state}      Profile: {s.profile_name}"

    def _content_renderable(self) -> RenderableType:
        """The left (working) pane: budget · transactions · pockets · settings."""
        s = self._service
        if s.profile_id is None:
            return "No profile — type:  profile add <name>"
        try:
            if s.tab == "settings":
                return render_settings(s, s.list_profiles())
            month = s.active_month()
            if s.tab == "transactions":
                return render_transactions(month, s.tx_filter, s.currency)
            if s.tab == "pockets":
                return render_pockets(month, s.currency)
            return render_budget(month, s.drilled_section, s.currency)
        except MonayError:
            return "No month."

    def _helper_renderable(self) -> RenderableType:
        """The right (helper) pane: docs (always available) · history."""
        s = self._service
        if s.helper_tab == "docs":
            return render_docs(self._commands.specs(), s.docs_query)
        if s.profile_id is None:
            return "No profile — type:  profile add <name>"
        try:
            return render_history(s.month_summaries(), s.viewing)
        except MonayError:
            return "No month."
