"""The spec-driven command registry — one source for parse + help + execution.

A ``CommandSpec`` declares a command's path (verb + optional subverb), its
argument schema, help text, and handler. The same specs drive the parser, the
``help`` output, and (Phase 12) autocomplete, so they can never drift from
execution (docs/DEVELOPING.md).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from monay.app.errors import AppError
from monay.domain.errors import MonayError

if TYPE_CHECKING:
    from monay.app.services import MonayApp

# A parsed command's arguments: name -> value, where the value type depends on
# the arg's kind (str, Money, int, or None), so it is intentionally dynamic.
Args = dict[str, Any]

# --- argument kinds -------------------------------------------------------
FIELD = "field"
SECTION = "section"
POCKET = "pocket"
AMOUNT = "amount"
CAP = "cap"
DAY = "day"
TEXT = "text"
CHOICE = "choice"
MONTH = "month"
INT = "int"
WORD = "word"


@dataclass(frozen=True)
class Arg:
    name: str
    kind: str
    required: bool = True
    choices: tuple[str, ...] = ()
    variadic: bool = False  # consumes the rest of the line (descriptions/notes)


@dataclass(frozen=True)
class CommandSpec:
    path: tuple[str, ...]
    args: tuple[Arg, ...]
    help: str
    handler: Handler
    confirm: bool = False
    summary: SummaryFn | None = None  # builds the confirmation prompt

    @property
    def name(self) -> str:
        return " ".join(self.path)

    def usage(self) -> str:
        parts = [self.name]
        for a in self.args:
            inner = f"{a.name}…" if a.variadic else a.name
            parts.append(f"[{inner}]" if not a.required else f"<{inner}>")
        return " ".join(parts)


@dataclass
class Result:
    status: str  # "ok" | "error" | "confirm" | "info"
    message: str
    month: object = None
    data: object = None
    pending: str | None = None

    @classmethod
    def ok(cls, message: str, month: object = None) -> Result:
        return cls("ok", message, month=month)

    @classmethod
    def error(cls, message: str) -> Result:
        return cls("error", message)

    @classmethod
    def info(cls, message: str, data: object = None) -> Result:
        return cls("info", message, data=data)

    @classmethod
    def confirm(cls, prompt: str, pending: str) -> Result:
        return cls("confirm", prompt, pending=pending)


# A handler turns (app, parsed args) into a Result; a summary builds the
# confirmation prompt for commands that ask before acting.
Handler = Callable[["MonayApp", Args], Result]
SummaryFn = Callable[["MonayApp", Args], str]


class CommandRegistry:
    def __init__(self, specs: list[CommandSpec]) -> None:
        self._specs = list(specs)
        self._by_path = {s.path: s for s in self._specs}

    def specs(self) -> list[CommandSpec]:
        return list(self._specs)

    def find(self, path: tuple[str, ...]) -> CommandSpec | None:
        return self._by_path.get(path)

    def verbs(self) -> list[str]:
        return sorted({s.path[0] for s in self._specs})

    def execute(self, app: MonayApp, text: str, confirmed: bool = False) -> Result:
        from .parser import parse  # local import to avoid a cycle

        try:
            spec, args = parse(self, text)
        except (AppError, MonayError) as exc:
            return Result.error(str(exc))

        if spec.confirm and not confirmed:
            try:
                prompt = (
                    spec.summary(app, args)
                    if spec.summary
                    else f"{spec.name}: are you sure?"
                )
            except (AppError, MonayError) as exc:
                return Result.error(str(exc))
            return Result.confirm(f"{prompt} Type Yes or No:", pending=text)

        try:
            return spec.handler(app, args)
        except (AppError, MonayError) as exc:
            return Result.error(str(exc))
