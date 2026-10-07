"""Errors → HTTP responses, all in one shape (``schemas.ErrorOut``).

The engine raises typed errors with a message written for a person; this module
only decides the status code, a stable machine-readable ``code``, and — where
the error type implies it — which form field is at fault.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from monay.app.errors import (
    AppError,
    NoProfileError,
    StaleRevisionError,
    UndoUnavailableError,
)
from monay.domain.errors import (
    AmbiguousError,
    CapExceededError,
    DuplicateNameError,
    FieldNotEmptyError,
    MonayError,
    MonthClosedError,
    MonthNotBalancedError,
    NotFoundError,
    PocketInUseError,
    SectionNotEmptyError,
)

from .parsing import InputError
from .schemas import ErrorOut

# (error type, status, code, field at fault). First match wins.
_RULES: tuple[tuple[type[Exception], int, str, str | None], ...] = (
    (StaleRevisionError, 412, "stale_revision", None),
    (UndoUnavailableError, 409, "undo_unavailable", None),
    (NoProfileError, 404, "not_found", None),
    (NotFoundError, 404, "not_found", None),
    (DuplicateNameError, 409, "duplicate_name", "name"),
    (CapExceededError, 422, "cap_exceeded", "amount"),
    (MonthClosedError, 409, "month_closed", None),
    (MonthNotBalancedError, 409, "month_not_balanced", None),
    (FieldNotEmptyError, 409, "field_not_empty", None),
    (SectionNotEmptyError, 409, "section_not_empty", None),
    (PocketInUseError, 409, "pocket_in_use", None),
    (AmbiguousError, 409, "ambiguous", None),
)

# Documented on every route so the generated client types the error body.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorOut} for status in (404, 409, 412, 422)
}


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(InputError, _input_error)
    app.add_exception_handler(MonayError, _engine_error)
    app.add_exception_handler(AppError, _engine_error)
    app.add_exception_handler(RequestValidationError, _malformed_request)


def _respond(status: int, code: str, message: str, field: str | None) -> JSONResponse:
    body = ErrorOut(code=code, message=message, field=field)
    return JSONResponse(status_code=status, content=body.model_dump())


def _sentence(text: str) -> str:
    """Engine messages are lower-case fragments; a form shows sentences."""
    text = text.strip()
    if not text:
        return "Something went wrong."
    text = text[0].upper() + text[1:]
    return text if text[-1] in ".!?" else text + "."


async def _input_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, InputError)
    return _respond(422, "invalid_input", exc.message, exc.field)


async def _engine_error(_request: Request, exc: Exception) -> JSONResponse:
    for kind, status, code, field in _RULES:
        if isinstance(exc, kind):
            return _respond(status, code, _sentence(str(exc)), field)
    # Whatever is left is a broken rule or a bad value (ValidationError,
    # BadUsageError, …): the request was understood and refused.
    return _respond(422, "invalid", _sentence(str(exc)), None)


async def _malformed_request(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    first = exc.errors()[0] if exc.errors() else {}
    location = [str(part) for part in first.get("loc", ())]
    # ("body", "name") → "name"; ("header", "if-match") → "if-match"
    field = ".".join(location[1:]) or None
    return _respond(422, "invalid_request", _sentence(str(first.get("msg", ""))), field)
