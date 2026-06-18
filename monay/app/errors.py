"""Application-layer errors (command parsing & session), distinct from domain errors."""

from __future__ import annotations


class AppError(Exception):
    """Base for application/command errors."""


class UnknownCommandError(AppError):
    """The first token doesn't match any command."""


class BadUsageError(AppError):
    """A command was recognized but its arguments are wrong."""


class NoProfileError(AppError):
    """An operation needs a selected profile but none is active."""
