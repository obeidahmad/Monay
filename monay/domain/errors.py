"""Domain exceptions.

Every domain-level error inherits :class:`MonayError` so callers can catch the
whole family with one ``except``. Validation failures are also ``ValueError``s
so generic input handling still works.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .money import Money


class MonayError(Exception):
    """Base class for every domain-level error."""


class ValidationError(MonayError, ValueError):
    """A value object or input violated an invariant."""


class ExpressionError(ValidationError):
    """An amount expression could not be parsed or evaluated safely."""


# --- aggregate / mutation errors (Phase 3) --------------------------------
class MonthClosed(MonayError):
    """A write was attempted on a closed month (corrections go in the open one)."""


class NotFound(MonayError):
    """A referenced section / field / pocket / income does not exist."""


class Ambiguous(MonayError):
    """A bare field name matches fields in more than one section."""


class DuplicateName(MonayError):
    """A name collides with an existing one (sections, fields-in-section, pockets)."""


class FieldNotEmpty(MonayError):
    """A field cannot be deleted while it holds money (LEFT ≠ 0) or has activity."""


class SectionNotEmpty(MonayError):
    """A section cannot be deleted while it still has fields."""


class PocketInUse(MonayError):
    """A pocket cannot be deleted while fields still belong to it."""


class MonthNotBalanced(MonayError):
    """Post-section percentages do not sum to 100% (month can't be operated/closed)."""


class CapExceeded(MonayError):
    """A transfer would push the destination's LEFT above its MAX (a hard invariant).

    ``allowed`` carries the largest amount that would still fit, so the UI can
    tell the user (docs/DEVELOPING.md).
    """

    def __init__(self, message: str, allowed: "Money | None" = None) -> None:
        super().__init__(message)
        self.allowed = allowed