"""Tokenize a command line, match it to a spec, and bind/convert its arguments.

Matching prefers a two-token path (``field add``) over a one-token one (``add``).
A ``d<day>`` token is pulled out wherever it appears; the final variadic arg
soaks up the rest of the line (descriptions/notes). Quotes group multi-word
names: ``field add Save "Emergency Cash" 200``.
"""

from __future__ import annotations

import re
import shlex

from monay.app.errors import BadUsageError, UnknownCommandError
from monay.domain.expressions import evaluate

from .registry import AMOUNT, CHOICE, DAY, INT, CommandRegistry, CommandSpec

_DAY_RE = re.compile(r"^d(\d+)$", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    try:
        return shlex.split(text)
    except ValueError as exc:
        raise BadUsageError(f"could not parse the command ({exc})") from exc


def parse(registry: CommandRegistry, text: str) -> tuple[CommandSpec, dict]:
    tokens = tokenize(text)
    if not tokens:
        raise BadUsageError("type a command — try: help")

    spec = None
    rest: list[str] = []
    if len(tokens) >= 2:
        spec = registry.find((tokens[0].lower(), tokens[1].lower()))
        if spec is not None:
            rest = tokens[2:]
    if spec is None:
        spec = registry.find((tokens[0].lower(),))
        if spec is not None:
            rest = tokens[1:]
    if spec is None:
        raise UnknownCommandError(f"unknown command: {tokens[0]!r} — try: help")

    return spec, _bind(spec, rest)


def _bind(spec: CommandSpec, tokens: list[str]) -> dict:
    tokens = list(tokens)
    values: dict = {}

    day_arg = next((a for a in spec.args if a.kind == DAY), None)
    if day_arg is not None:
        values[day_arg.name] = None
        for i, tok in enumerate(tokens):
            m = _DAY_RE.match(tok)
            if m:
                values[day_arg.name] = int(m.group(1))
                del tokens[i]
                break

    for arg in (a for a in spec.args if a.kind != DAY):
        if arg.variadic:
            joined = " ".join(tokens)
            tokens = []
            if not joined and arg.required:
                raise BadUsageError(f"missing {arg.name} — usage: {spec.usage()}")
            values[arg.name] = joined or None
            break
        if not tokens:
            if arg.required:
                raise BadUsageError(f"missing {arg.name} — usage: {spec.usage()}")
            values[arg.name] = None
            continue
        values[arg.name] = _convert(arg, tokens.pop(0), spec)

    if tokens:
        raise BadUsageError(f"too many arguments — usage: {spec.usage()}")
    return values


def _convert(arg, token: str, spec: CommandSpec):
    if arg.kind == AMOUNT:
        return evaluate(token)  # -> Money (ExpressionError if malformed)
    if arg.kind == INT:
        try:
            return int(token)
        except ValueError as exc:
            raise BadUsageError(
                f"{arg.name} must be a whole number, got {token!r}"
            ) from exc
    if arg.kind == CHOICE:
        for choice in arg.choices:
            if choice.lower() == token.lower():
                return choice
        raise BadUsageError(f"{arg.name} must be one of: {', '.join(arg.choices)}")
    return token  # field/section/pocket/word/month/cap — interpreted by the handler
