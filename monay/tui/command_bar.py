"""The command bar — an always-focused input with ↑/↓ history and Esc-clear.

Autocomplete (dropdown + ghost text) is Phase 12; this is the plain input loop.
"""

from __future__ import annotations

from textual import events
from textual.widgets import Input


class CommandBar(Input):
    def __init__(self, **kwargs) -> None:
        super().__init__(placeholder="type a command…  (try: help)", **kwargs)
        self._history: list[str] = []
        self._index: int = 0  # == len(history) means "the new, empty line"

    def remember(self, text: str) -> None:
        if text and (not self._history or self._history[-1] != text):
            self._history.append(text)
        self._index = len(self._history)

    async def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            self._recall(-1)
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            self._recall(1)
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.value = ""
            event.prevent_default()
            event.stop()

    def _recall(self, step: int) -> None:
        if not self._history:
            return
        self._index = max(0, min(len(self._history), self._index + step))
        self.value = (
            self._history[self._index] if self._index < len(self._history) else ""
        )
        self.cursor_position = len(self.value)
