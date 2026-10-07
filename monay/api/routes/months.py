"""Reading months, closing the open one, and undoing a change."""

from __future__ import annotations

from fastapi import APIRouter

from monay.api.deps import Key, Ref, Service
from monay.api.presenters import (
    change_out,
    close_preview_out,
    month_out,
    summary_out,
)
from monay.api.schemas import (
    ChangeOut,
    ClosePreviewOut,
    MonthOut,
    MonthSummaryOut,
    UndoRequest,
)
from monay.app.budgeting import Changed

router = APIRouter(prefix="/profiles/{profile_id}/months", tags=["months"])


@router.get("")
def list_months(profile_id: int, service: Service) -> list[MonthSummaryOut]:
    """Every month of a profile, newest first — the History list."""
    return [summary_out(s) for s in service.summaries(profile_id)]


@router.get("/{key}")
def get_month(profile_id: int, key: Key, service: Service) -> MonthOut:
    return month_out(service.month(profile_id, key))


@router.get("/{key}/close-preview")
def preview_close(profile_id: int, key: Key, service: Service) -> ClosePreviewOut:
    """What closing this month would carry forward. Changes nothing."""
    return close_preview_out(service.close_preview(profile_id, key))


@router.post("/{key}/close")
def close_month(ref: Ref, service: Service) -> MonthOut:
    """Lock the month for good and return the next one, now open."""
    return month_out(service.close(ref))


@router.post("/{key}/undo")
def undo_change(
    profile_id: int, key: Key, body: UndoRequest, service: Service
) -> ChangeOut:
    """Take back the change an ``undo_token`` came from."""
    return change_out(Changed(service.undo(profile_id, key, body.token)))
