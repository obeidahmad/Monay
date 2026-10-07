"""Profiles — fully independent budgets."""

from __future__ import annotations

from fastapi import APIRouter, Response

from monay.api import parsing
from monay.api.deps import Service
from monay.api.presenters import profile_out
from monay.api.schemas import ProfileCreate, ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("")
def list_profiles(service: Service) -> list[ProfileOut]:
    return [profile_out(p) for p in service.list_profiles()]


@router.post("", status_code=201)
def create_profile(body: ProfileCreate, service: Service) -> ProfileOut:
    """Create a profile with its first month (and a default ``Main`` pocket)."""
    first = None if body.first_month is None else parsing.month_key(body.first_month)
    return profile_out(service.create_profile(body.name, first))


@router.patch("/{profile_id}")
def rename_profile(
    profile_id: int, body: ProfileUpdate, service: Service
) -> ProfileOut:
    return profile_out(service.rename_profile(profile_id, body.name))


# response_class=Response: a 204 has no body, so it shouldn't claim to be JSON.
@router.delete("/{profile_id}", status_code=204, response_class=Response)
def delete_profile(profile_id: int, service: Service) -> None:
    """Delete a profile and every month it has. There is no undo."""
    service.delete_profile(profile_id)
