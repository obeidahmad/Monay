"""``Monay`` — the Textual app shell (docs/DEVELOPING.md).

Tab strip, a context bar (month · state · profile), the active-tab content area,
a feedback line, and the command bar. The shell parses each command through the
registry, runs it against the ``MonayApp`` service, and shows the result. Typed
``Yes``/``No`` answers a pending confirmation. Tab *contents* arrive in Phases
10–11; here every tab is a placeholder.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Tab, Tabs

from monay.app.commands import CommandRegistry, Result
from monay.app.services import MonayApp, month_label
from monay.domain.errors import MonayError
from monay.tui import theme
from monay.tui.command_bar import CommandBar
from monay.tui.screens.budget import render_budget
from monay.tui.screens.history import render_history
from monay.tui.screens.pockets import render_pockets
from monay.tui.screens.settings import render_settings
from monay.tui.screens.transactions import render_transactions

_TABS = ("budget", "transactions", "pockets", "history", "settings")


class Monay(App):
    CSS = f"""
    Screen {{ background: {theme.BG}; }}
    #context {{
        height: 1; background: {theme.PANEL}; color: {theme.TEXT}; padding: 0 1;
    }}
    Tabs {{ background: {theme.TABS_BG}; }}
    #content {{ height: 1fr; padding: 1 2; color: {theme.TEXT}; }}
    #feedback {{ height: 1; padding: 0 1; color: {theme.OK}; }}
    #feedback.error {{ color: {theme.ERROR}; }}
    #feedback.confirm {{ color: {theme.WARN}; }}
    #feedback.info {{ color: {theme.INFO}; }}
    CommandBar {{ border: round {theme.PANEL}; }}
    """

    BINDINGS = [Binding("ctrl+c", "quit", "Quit", priority=True)]

    def __init__(self, service: MonayApp, registry: CommandRegistry) -> None:
        super().__init__()
        self._service = service
        self._commands = registry
        self._pending: str | None = None
        # last rendered text (handy for tests / introspection)
        self.last_feedback: str = ""
        self.last_status: str = ""
        self.last_context: str = ""

    def compose(self) -> ComposeResult:
        yield Static(id="context")
        yield Tabs(*(Tab(t.title(), id=t) for t in _TABS), id="tabs")
        yield Static(id="content")
        yield Static(id="feedback")
        yield CommandBar(id="command")

    def on_mount(self) -> None:
        self.query_one(CommandBar).focus()
        self._service.resume()  # re-select an existing profile + its open month
        self._refresh()

    # --- command loop -----------------------------------------------------
    def on_input_submitted(self, event) -> None:
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
    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab is not None:
            self._service.tab = event.tab.id
            self.query_one("#content", Static).update(self._content_renderable())

    def _refresh(self) -> None:
        self.last_context = self._context_text()
        self.query_one("#context", Static).update(self.last_context)
        self.query_one("#content", Static).update(self._content_renderable())
        tabs = self.query_one(Tabs)
        if tabs.active != self._service.tab:
            tabs.active = self._service.tab

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

    def _content_renderable(self):
        s = self._service
        if s.profile_id is None:
            return "No profile — type:  profile add <name>"
        try:
            if s.tab == "history":
                return render_history(s.month_summaries(), s.viewing)
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
