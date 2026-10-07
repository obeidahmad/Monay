"""Sections of a month, and the fields inside them."""

from __future__ import annotations

from fastapi import APIRouter

from monay.api import parsing
from monay.api.deps import Ref, Service
from monay.api.parsing import InputError
from monay.api.presenters import change_out
from monay.api.routes import MONTH
from monay.api.schemas import (
    ChangeOut,
    FieldCreate,
    FieldUpdate,
    SectionCreate,
    SectionUpdate,
)
from monay.domain.entities import SectionKind

router = APIRouter(prefix=f"{MONTH}/sections", tags=["sections"])


@router.post("")
def add_section(body: SectionCreate, ref: Ref, service: Service) -> ChangeOut:
    if body.kind is not SectionKind.PRE and body.allocation.type == "amount":
        raise InputError(
            "allocation",
            f"A {body.kind.value}-section takes a percentage, not a fixed amount.",
        )
    return change_out(
        service.add_section(
            ref,
            body.name,
            body.kind,
            parsing.allocation(body.allocation),
            None if body.rest_routing is None else parsing.routing(body.rest_routing),
        )
    )


@router.patch("/{section}")
def edit_section(
    section: int, body: SectionUpdate, ref: Ref, service: Service
) -> ChangeOut:
    """Edit a section. ``position`` moves it within the display order."""
    return change_out(
        service.edit_section(
            ref,
            section,
            name=body.name,
            allocation=(
                None if body.allocation is None else parsing.allocation(body.allocation)
            ),
            routing=(
                None
                if body.rest_routing is None
                else parsing.routing(body.rest_routing)
            ),
            position=body.position,
        )
    )


@router.delete("/{section}")
def delete_section(section: int, ref: Ref, service: Service) -> ChangeOut:
    """Delete a section that has no fields left."""
    return change_out(service.delete_section(ref, section))


@router.post("/{section}/fields")
def add_field(section: int, body: FieldCreate, ref: Ref, service: Service) -> ChangeOut:
    return change_out(
        service.add_field(
            ref,
            section,
            body.name,
            parsing.budget(body.budget),
            parsing.cap(body.max),
            pocket_index=body.pocket,
            current=(
                None
                if body.current is None
                else parsing.amount(body.current, "current")
            ),
        )
    )


@router.patch("/{section}/fields/{field}")
def edit_field(
    section: int, field: int, body: FieldUpdate, ref: Ref, service: Service
) -> ChangeOut:
    return change_out(
        service.edit_field(
            ref,
            section,
            field,
            name=body.name,
            budget=(
                None
                if body.budget is None
                else parsing.allocation(body.budget, "budget")
            ),
            # ``max: null`` means "no limit", so only its absence means unchanged.
            cap=parsing.cap(body.max) if "max" in body.model_fields_set else None,
            pocket_index=body.pocket,
            current=(
                None
                if body.current is None
                else parsing.amount(body.current, "current")
            ),
        )
    )


@router.delete("/{section}/fields/{field}")
def delete_field(section: int, field: int, ref: Ref, service: Service) -> ChangeOut:
    """Delete a field — only once it is empty (LEFT 0, no activity this month)."""
    return change_out(service.delete_field(ref, section, field))
