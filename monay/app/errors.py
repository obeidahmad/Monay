"""Application-layer errors (session & use-case usage), distinct from domain errors."""

from __future__ import annotations


class AppError(Exception):
    """Base for application errors."""


class BadUsageError(AppError):
    """A use case was called with arguments it can't act on."""


class NoProfileError(AppError):
    """An operation needs a selected profile but none is active."""
