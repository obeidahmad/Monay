"""A draggable vertical divider between the two body panes (docs/DEVELOPING.md).

A thin 1-cell grab handle: press and drag it left/right to resize the pane on its
right. It captures the mouse while dragging and emits a :class:`Dragged` message
(carrying the horizontal delta) that the app turns into a width change — the same
message pattern as Textual's own widgets.
"""

from __future__ import annotations

from textual import events
from textual.message import Message
from textual.widgets import Static


class PaneDivider(Static):
    """The grab handle between the working and helper panes."""

    class Dragged(Message):
        """The divider moved ``delta`` cells horizontally (right is positive)."""

        def __init__(self, delta: int) -> None:
            self.delta = delta
            super().__init__()

    def __init__(self, *, id: str | None = None) -> None:  # noqa: A002
        super().__init__(id=id)
        self._dragging = False

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self._dragging = True
        self.capture_mouse()
        event.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._dragging and event.delta_x:
            self.post_message(self.Dragged(event.delta_x))
            event.stop()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        self._dragging = False
        self.release_mouse()
        event.stop()
