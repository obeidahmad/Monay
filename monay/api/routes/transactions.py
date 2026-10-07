"""Transactions (money leaving a field) and transfers (pot money moving)."""

from __future__ import annotations

from fastapi import APIRouter

from monay.api import parsing
from monay.api.deps import Ref, Service
from monay.api.parsing import InputError
from monay.api.presenters import change_out
from monay.api.routes import MONTH
from monay.api.schemas import (
    ChangeOut,
    TransactionCreate,
    TransactionUpdate,
    TransferCreate,
)

router = APIRouter(prefix=MONTH, tags=["transactions"])


@router.post("/transactions")
def add_transaction(body: TransactionCreate, ref: Ref, service: Service) -> ChangeOut:
    amount = parsing.positive_amount(body.amount)
    return change_out(
        service.add_transaction(
            ref,
            body.field.section,
            body.field.field,
            amount,
            body.day,
            description=body.description,
            expression=body.amount,
        )
    )


@router.patch("/transactions/{number}")
def edit_transaction(
    number: int, body: TransactionUpdate, ref: Ref, service: Service
) -> ChangeOut:
    """Correct a transaction; ``field`` moves it to another field."""
    amount = None if body.amount is None else parsing.positive_amount(body.amount)
    return change_out(
        service.edit_transaction(
            ref,
            number,
            field=None if body.field is None else parsing.field_ref(body.field),
            amount=amount,
            expression=body.amount,
            day=body.day,
            description=body.description,
        )
    )


@router.delete("/transactions/{number}")
def delete_transaction(number: int, ref: Ref, service: Service) -> ChangeOut:
    return change_out(service.delete_transaction(ref, number))


@router.post("/transfers")
def add_transfer(body: TransferCreate, ref: Ref, service: Service) -> ChangeOut:
    """Move accumulated pot money between two fields (never above a MAX)."""
    if body.from_field == body.to_field:
        raise InputError("to_field", "Choose a different field to move the money to.")
    amount = parsing.positive_amount(body.amount)
    return change_out(
        service.add_transfer(
            ref,
            parsing.field_ref(body.from_field),
            parsing.field_ref(body.to_field),
            amount,
            body.day,
            note=body.note,
        )
    )


@router.delete("/transfers/{number}")
def delete_transfer(number: int, ref: Ref, service: Service) -> ChangeOut:
    return change_out(service.delete_transfer(ref, number))
