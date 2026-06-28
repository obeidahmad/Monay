"""The command bar — an always-focused input with completion, history, Esc-clear.

Ghost text comes from Textual's built-in suggester (a dimmed completion of the
trailing token), fed by the registry-driven :func:`complete`. ``Tab`` accepts the
ghost completion; pressing it again cycles through the other matching candidates
in place, until you type (which resets the cycle). ``→`` also accepts (built in),
``↑/↓`` recall history, and ``Esc`` clears the line.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from textual import events
from textual.suggester import Suggester
from textual.widgets import Input

from monay.app.commands import CommandRegistry
from monay.app.commands.completion import CompletionNames, complete


class _RegistrySuggester(Suggester):
    """Feed the command bar's ghost text from the registry-driven completer.

    Caching is off (the candidate names change as the user edits the month) and
    casing is left to :func:`complete`, whose suggestions extend the typed text.
    """

    def __init__(
        self, registry: CommandRegistry, names: Callable[[], CompletionNames]
    ) -> None:
        super().__init__(use_cache=False, case_sensitive=True)
        self._registry = registry
        self._names = names

    async def get_suggestion(self, value: str) -> str | None:
        matches = complete(self._registry, self._names(), value)
        return matches[0] if matches else None


class CommandBar(Input):
    def __init__(
        self,
        registry: CommandRegistry,
        names: Callable[[], CompletionNames],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            placeholder="type a command…  (try: help)",
            suggester=_RegistrySuggester(registry, names),
            **kwargs,
        )
        self._registry = registry
        self._names = names
        self._history: list[str] = []
        self._index: int = 0  # == len(history) means "the new, empty line"
        # Tab-cycle state: the completions for the current stem, the position in
        # them, and the value we last applied (so any edit breaks the cycle).
        self._cycle: list[str] = []
        self._cycle_at: int = 0
        self._cycle_value: str | None = None

    def remember(self, text: str) -> None:
        if text and (not self._history or self._history[-1] != text):
            self._history.append(text)
        self._index = len(self._history)

    async def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            self._recall(-1)
        elif event.key == "down":
            self._recall(1)
        elif event.key == "escape":
            self.value = ""
        elif event.key == "tab":
            if not self._complete_or_cycle():
                return  # nothing to complete — let Tab fall through to focus
        else:
            return
        event.prevent_default()
        event.stop()

    def _complete_or_cycle(self) -> bool:
        """Apply the next completion on Tab; return ``False`` if there is none.

        Re-pressing Tab without editing advances through the matches (wrapping);
        any edit resets the cycle, since the value no longer matches what we
        last applied.
        """
        if self._cycle and self.value == self._cycle_value:
            self._cycle_at = (self._cycle_at + 1) % len(self._cycle)
        else:
            self._cycle = complete(self._registry, self._names(), self.value)
            self._cycle_at = 0
            if not self._cycle:
                return False
        self.value = self._cycle[self._cycle_at]
        self.cursor_position = len(self.value)
        self._cycle_value = self.value
        return True

    def _recall(self, step: int) -> None:
        if not self._history:
            return
        self._index = max(0, min(len(self._history), self._index + step))
        self.value = (
            self._history[self._index] if self._index < len(self._history) else ""
        )
        self.cursor_position = len(self.value)
