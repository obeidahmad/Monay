"""Income entries of a month."""

from __future__ import annotations

from fastapi import APIRouter

from monay.api import parsing
from monay.api.deps import Ref, Service
from monay.api.presenters import change_out
from monay.api.routes import MONTH
from monay.api.schemas import ChangeOut, IncomeCreate, IncomeUpdate

router = APIRouter(prefix=f"{MONTH}/incomes", tags=["income"])


@router.post("")
def add_income(body: IncomeCreate, ref: Ref, service: Service) -> ChangeOut:
    amount = parsing.amount(body.amount)
    return change_out(service.add_income(ref, body.name, amount))


@router.patch("/{index}")
def edit_income(
    index: int, body: IncomeUpdate, ref: Ref, service: Service
) -> ChangeOut:
    amount = None if body.amount is None else parsing.amount(body.amount)
    return change_out(service.edit_income(ref, index, name=body.name, amount=amount))


@router.delete("/{index}")
def delete_income(index: int, ref: Ref, service: Service) -> ChangeOut:
    return change_out(service.delete_income(ref, index))
