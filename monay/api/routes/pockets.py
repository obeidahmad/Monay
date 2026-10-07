"""Pockets — where the money physically sits."""

from __future__ import annotations

from fastapi import APIRouter

from monay.api.deps import Ref, Service
from monay.api.presenters import change_out
from monay.api.routes import MONTH
from monay.api.schemas import ChangeOut, PocketCreate, PocketUpdate

router = APIRouter(prefix=f"{MONTH}/pockets", tags=["pockets"])


@router.post("")
def add_pocket(body: PocketCreate, ref: Ref, service: Service) -> ChangeOut:
    return change_out(service.add_pocket(ref, body.name))


@router.patch("/{index}")
def edit_pocket(
    index: int, body: PocketUpdate, ref: Ref, service: Service
) -> ChangeOut:
    """Rename a pocket and/or make it the default."""
    return change_out(
        service.edit_pocket(
            ref, index, name=body.name, make_default=body.is_default is True
        )
    )


@router.delete("/{index}")
def delete_pocket(index: int, ref: Ref, service: Service) -> ChangeOut:
    """Delete a pocket no field belongs to (never the default)."""
    return change_out(service.delete_pocket(ref, index))
