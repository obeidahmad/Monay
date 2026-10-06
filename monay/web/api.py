"""The JSON API the React frontend talks to (docs/DEVELOPING.md).

A thin adapter over the ``MonayApp`` use-case facade — the same role the command
registry used to play for the terminal UI. Every mutating call returns the whole
fresh UI state (``presenter.state``), so the frontend just replaces what it
shows; it never recomputes budget math itself. Names travel in JSON bodies (not
URL paths), so any name a user picks is addressable.

Endpoints are ``async`` on purpose: they run one at a time on the event loop, so
the single session in ``MonayApp`` (profile + month being viewed) is never
mutated concurrently. Monay is a local, single-user app.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from monay import __version__
from monay.app import inputs
from monay.app.errors import AppError
from monay.app.services import MonayApp
from monay.domain.errors import CapExceededError, MonayError, ValidationError
from monay.domain.values import Percentage
from monay.web import presenter
from monay.web.presenter import JSON

STATIC_DIR = Path(__file__).parent / "static"


# --- request bodies -----------------------------------------------------------
class Name(BaseModel):
    name: str


class ViewMonth(BaseModel):
    key: str | None = None  # None → back to the open month


class IncomeAdd(BaseModel):
    name: str
    amount: str


class IncomeEdit(BaseModel):
    income: str
    name: str | None = None
    amount: str | None = None


class IncomeRef(BaseModel):
    income: str


class SectionAdd(BaseModel):
    kind: Literal["tax", "pre", "post"]
    name: str
    alloc: str  # "50%" or an amount (pre only)


class SectionEdit(BaseModel):
    section: str
    name: str | None = None
    alloc: str | None = None
    rest: str | None = None  # income | self | <section>
    position: int | None = None


class SectionRef(BaseModel):
    section: str


class FieldAdd(BaseModel):
    section: str
    name: str
    budget: str | None = None  # amount or NN%; blank → 0
    max: str | None = None  # amount, or blank/inf → ∞


class FieldEdit(BaseModel):
    section: str
    field: str
    name: str | None = None
    budget: str | None = None
    max: str | None = None
    pocket: str | None = None
    current: str | None = None


class FieldRef(BaseModel):
    section: str
    field: str


class TxAdd(BaseModel):
    section: str
    field: str
    amount: str
    day: int | None = None
    description: str = ""


class TxEdit(BaseModel):
    index: int
    amount: str | None = None
    day: int | None = None
    description: str | None = None


class TxRef(BaseModel):
    index: int


class TransferAdd(BaseModel):
    from_section: str
    from_field: str
    to_section: str
    to_field: str
    amount: str
    day: int | None = None
    note: str = ""


class PocketEdit(BaseModel):
    pocket: str
    name: str | None = None
    main: bool = False


class PocketRef(BaseModel):
    pocket: str


class Expression(BaseModel):
    expr: str


# --- the app ------------------------------------------------------------------
def create_app(service: MonayApp, static_dir: Path = STATIC_DIR) -> FastAPI:
    api = FastAPI(title="Monay", version=__version__)

    @api.exception_handler(MonayError)
    @api.exception_handler(AppError)
    async def _domain_error(_: Request, exc: Exception) -> Response:
        body: JSON = {"detail": str(exc)}
        if isinstance(exc, CapExceededError) and exc.allowed is not None:
            body["allowed"] = presenter.money(exc.allowed)
        return JSONResponse(body, status_code=400)

    def state() -> JSON:
        return presenter.state(service)

    def run(fn: Callable[[], object]) -> JSON:
        fn()
        return state()

    # --- state / meta ---------------------------------------------------------
    @api.get("/api/state")
    async def get_state() -> JSON:
        return state()

    @api.get("/api/version")
    async def version() -> JSON:
        return {"version": __version__}

    @api.post("/api/evaluate")
    async def evaluate(body: Expression) -> JSON:
        """Preview an amount expression (``15.71+1.35`` → ``17.06``)."""
        return {"value": presenter.money(inputs.amount(body.expr))}

    # --- profiles -------------------------------------------------------------
    @api.post("/api/profiles")
    async def profile_add(body: Name) -> JSON:
        return run(lambda: service.create_profile(_name(body.name)))

    @api.post("/api/profiles/switch")
    async def profile_switch(body: Name) -> JSON:
        return run(lambda: service.switch_profile(body.name))

    @api.post("/api/profiles/rename")
    async def profile_rename(body: Name) -> JSON:
        return run(lambda: service.rename_profile(_name(body.name)))

    @api.post("/api/profiles/delete")
    async def profile_delete(body: Name) -> JSON:
        return run(lambda: service.delete_profile(body.name))

    # --- months ---------------------------------------------------------------
    @api.post("/api/month/view")
    async def month_view(body: ViewMonth) -> JSON:
        if body.key is None:
            return run(service.view_open_month)
        key = body.key
        return run(lambda: service.view_month(key))

    @api.get("/api/month/close-preview")
    async def close_preview() -> JSON:
        return presenter.close_preview(service.close_preview())

    @api.post("/api/month/close")
    async def close() -> JSON:
        return run(service.close_active)

    # --- income ---------------------------------------------------------------
    @api.post("/api/incomes")
    async def income_add(body: IncomeAdd) -> JSON:
        return run(
            lambda: service.add_income(_name(body.name), inputs.amount(body.amount))
        )

    @api.post("/api/incomes/edit")
    async def income_edit(body: IncomeEdit) -> JSON:
        amount = inputs.amount(body.amount) if body.amount is not None else None
        new_name = _name(body.name) if body.name is not None else None
        return run(
            lambda: service.set_income(body.income, new_name=new_name, amount=amount)
        )

    @api.post("/api/incomes/delete")
    async def income_delete(body: IncomeRef) -> JSON:
        return run(lambda: service.delete_income(body.income))

    # --- sections -------------------------------------------------------------
    @api.post("/api/sections")
    async def section_add(body: SectionAdd) -> JSON:
        alloc = inputs.allocation(body.alloc)
        name = _name(body.name)
        if isinstance(alloc, Percentage):
            return run(lambda: service.add_section(body.kind, name, percentage=alloc))
        return run(lambda: service.add_section(body.kind, name, amount=alloc))

    @api.post("/api/sections/edit")
    async def section_edit(body: SectionEdit) -> JSON:
        alloc = inputs.allocation(body.alloc) if body.alloc else None
        routing = inputs.routing(body.rest) if body.rest else None
        new_name = _name(body.name) if body.name is not None else None
        return run(
            lambda: service.edit_section(
                body.section,
                allocation=alloc,
                routing=routing,
                position=body.position,
                new_name=new_name,
            )
        )

    @api.post("/api/sections/delete")
    async def section_delete(body: SectionRef) -> JSON:
        return run(lambda: service.delete_section(body.section))

    # --- fields ---------------------------------------------------------------
    @api.post("/api/fields")
    async def field_add(body: FieldAdd) -> JSON:
        budget, cap = inputs.budget(body.budget), inputs.cap(body.max)
        name = _name(body.name)
        return run(lambda: service.add_field(body.section, name, budget, cap))

    @api.post("/api/fields/edit")
    async def field_edit(body: FieldEdit) -> JSON:
        budget = inputs.budget(body.budget) if body.budget is not None else None
        cap = inputs.cap(body.max) if body.max is not None else None
        current = inputs.amount(body.current) if body.current is not None else None
        new_name = _name(body.name) if body.name is not None else None
        return run(
            lambda: service.edit_field(
                body.section,
                body.field,
                budget=budget,
                cap=cap,
                pocket=body.pocket,
                current=current,
                new_name=new_name,
            )
        )

    @api.post("/api/fields/delete")
    async def field_delete(body: FieldRef) -> JSON:
        return run(lambda: service.delete_field(body.field, section=body.section))

    # --- transactions / transfers ---------------------------------------------
    @api.post("/api/transactions")
    async def tx_add(body: TxAdd) -> JSON:
        amount = inputs.amount(body.amount)
        return run(
            lambda: service.add_transaction(
                body.field,
                amount,
                body.day,
                body.description.strip(),
                section=body.section,
            )
        )

    @api.post("/api/transactions/edit")
    async def tx_edit(body: TxEdit) -> JSON:
        amount = inputs.amount(body.amount) if body.amount is not None else None
        return run(
            lambda: service.edit_transaction(
                body.index, amount=amount, day=body.day, description=body.description
            )
        )

    @api.post("/api/transactions/delete")
    async def tx_delete(body: TxRef) -> JSON:
        return run(lambda: service.delete_transaction(body.index))

    @api.post("/api/transfers")
    async def transfer(body: TransferAdd) -> JSON:
        amount = inputs.amount(body.amount)
        return run(
            lambda: service.transfer(
                amount,
                body.from_field,
                body.to_field,
                body.day,
                body.note.strip(),
                from_section=body.from_section,
                to_section=body.to_section,
            )
        )

    # --- pockets --------------------------------------------------------------
    @api.post("/api/pockets")
    async def pocket_add(body: Name) -> JSON:
        return run(lambda: service.add_pocket(_name(body.name)))

    @api.post("/api/pockets/edit")
    async def pocket_edit(body: PocketEdit) -> JSON:
        new_name = _name(body.name) if body.name is not None else None
        return run(
            lambda: service.edit_pocket(body.pocket, new_name=new_name, main=body.main)
        )

    @api.post("/api/pockets/delete")
    async def pocket_delete(body: PocketRef) -> JSON:
        return run(lambda: service.delete_pocket(body.pocket))

    _mount_frontend(api, static_dir)
    return api


def _name(text: str) -> str:
    name = text.strip()
    if not name:
        raise ValidationError("a name can't be empty")
    return name


def _mount_frontend(api: FastAPI, static_dir: Path) -> None:
    """Serve the built React app; a hint page when it hasn't been built."""
    index = static_dir / "index.html"
    if not index.is_file():

        @api.get("/", response_class=HTMLResponse)
        async def not_built() -> str:
            return _NOT_BUILT

        return

    assets = static_dir / "assets"
    if assets.is_dir():
        api.mount("/assets", StaticFiles(directory=assets), name="assets")

    @api.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = (static_dir / path).resolve()
        if (
            path
            and candidate.is_file()
            and candidate.is_relative_to(static_dir.resolve())
        ):
            return FileResponse(candidate)
        return FileResponse(index)


_NOT_BUILT = """<!doctype html><meta charset="utf-8"><title>Monay</title>
<body style="font-family:system-ui;padding:48px;background:#0e0e12;color:#cfcfd6">
<h1 style="color:#fff">Monay</h1>
<p>The API is running, but the web frontend hasn't been built yet.</p>
<pre style="background:#1c1c24;padding:16px;border-radius:8px">cd web
npm install
npm run build</pre>
<p>Then restart Monay. (For live development run <code>npm run dev</code>.)</p>
</body>"""
