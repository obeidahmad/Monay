"""Request-scoped dependencies shared by the routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Path, Request

from monay.app.budgeting import BudgetingService, MonthRef
from monay.domain.values import MonthKey


def _service(request: Request) -> BudgetingService:
    service = request.app.state.budgeting  # set by the app's lifespan
    assert isinstance(service, BudgetingService)
    return service


Service = Annotated[BudgetingService, Depends(_service)]


def _month_key(
    key: Annotated[
        str,
        Path(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="A month, as yyyy-mm."),
    ],
) -> MonthKey:
    return MonthKey.from_string(key)


Key = Annotated[MonthKey, Depends(_month_key)]


def _month_ref(
    profile_id: int,
    key: Key,
    if_match: Annotated[
        str,
        Header(
            description="The `revision` of the month this change is based on. "
            "A 412 response means the month has changed since."
        ),
    ],
) -> MonthRef:
    return MonthRef(profile_id, key, _entity_tag(if_match))


Ref = Annotated[MonthRef, Depends(_month_ref)]


def _entity_tag(header: str) -> str:
    """Accept the revision bare or as an HTTP entity tag (``"abc"``, ``W/"abc"``)."""
    return header.strip().removeprefix("W/").strip('"')
