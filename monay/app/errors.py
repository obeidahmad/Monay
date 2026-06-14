"""Application-layer errors (command parsing & session), distinct from domain errors."""

from __future__ import annotations


class AppError(Exception):
    """Base for application/command errors."""


class UnknownCommand(AppError):
    """The first token doesn't match any command."""


class BadUsage(AppError):
    """A command was recognized but its arguments are wrong."""


class NoProfile(AppError):
    """An operation needs a selected profile but none is active."""