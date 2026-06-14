"""Rows ↔ domain graph. A ``Month`` is loaded and saved as one whole aggregate.

Saving uses delete-and-reinsert of the child rows (a month is tiny), so the
stored graph always matches the in-memory one without diffing. Loading rebuilds
the object graph and rewires transactions/transfers to their field objects.
"""

from __future__ import annotations

from sqlalchemy import delete, select, update

from monay.domain.entities import (
    AllocKind,
    Field,
    Income,
    IncomeKind,
    Pocket,
    Section,
    SectionKind,
    Transaction,
    Transfer,
)
from monay.domain.money import Money
from monay.domain.month import Month, MonthState
from monay.domain.values import Cap, Day, MonthKey, Percentage, RestRouting

from .schema import (
    fields,
    incomes,
    months,
    pockets,
    profiles,
    sections,
    transactions,
    transfers,
)


# --- save -----------------------------------------------------------------
def insert_month(conn, month: Month) -> None:
    month.id = conn.execute(
        months.insert().values(
            profile_id=month.profile_id, key=str(month.key), state=month.state.value
        )
    ).inserted_primary_key[0]
    _insert_children(conn, month.id, month)


def update_month(conn, month: Month) -> None:
    _delete_children(conn, month.id)
    conn.execute(
        update(months)
        .where(months.c.id == month.id)
        .values(state=month.state.value, key=str(month.key), profile_id=month.profile_id)
    )
    _insert_children(conn, month.id, month)


def _delete_children(conn, month_id: int) -> None:
    conn.execute(delete(transactions).where(transactions.c.month_id == month_id))
    conn.execute(delete(transfers).where(transfers.c.month_id == month_id))
    section_ids = select(sections.c.id).where(sections.c.month_id == month_id)
    conn.execute(delete(fields).where(fields.c.section_id.in_(section_ids)))
    conn.execute(delete(incomes).where(incomes.c.month_id == month_id))
    conn.execute(delete(sections).where(sections.c.month_id == month_id))
    conn.execute(delete(pockets).where(pockets.c.month_id == month_id))


def _insert_children(conn, month_id: int, month: Month) -> None:
    pocket_ids: dict[str, int] = {}
    for p in sorted(month.pockets, key=lambda p: p.position):
        p.id = conn.execute(
            pockets.insert().values(
                month_id=month_id, name=p.name, is_default=p.is_default, position=p.position
            )
        ).inserted_primary_key[0]
        pocket_ids[p.name] = p.id

    field_db_id: dict[int, int] = {}  # id(field_obj) -> db id (for tx/transfer wiring)
    for s in sorted(month.sections, key=lambda s: s.position):
        s.id = conn.execute(
            sections.insert().values(
                month_id=month_id,
                name=s.name,
                kind=s.kind.value,
                position=s.position,
                alloc_kind=s.alloc_kind.value,
                alloc_value=_alloc_value(s),
                rest_routing=s.rest_routing.kind.value,
                rest_target=s.rest_routing.target,
                carried_rest=s.carried_rest,
            )
        ).inserted_primary_key[0]
        for f in sorted(s.fields, key=lambda f: f.position):
            f.id = conn.execute(
                fields.insert().values(
                    section_id=s.id,
                    name=f.name,
                    budget=f.budget,
                    current=f.current,
                    cap_kind="inf" if f.cap.is_infinite else "finite",
                    cap_value=None if f.cap.is_infinite else f.cap.limit,
                    pocket_id=pocket_ids[f.pocket.name],
                    position=f.position,
                )
            ).inserted_primary_key[0]
            field_db_id[id(f)] = f.id

    for inc in month.incomes:
        conn.execute(
            incomes.insert().values(
                month_id=month_id,
                name=inc.name,
                amount=inc.amount,
                kind=inc.kind.value,
                position=inc.position,
            )
        )
    for tx in month.transactions:
        conn.execute(
            transactions.insert().values(
                month_id=month_id,
                field_id=field_db_id[id(tx.field)],
                day=int(tx.day),
                amount=tx.amount,
                amount_expr=tx.amount_expr,
                description=tx.description,
            )
        )
    for t in month.transfers:
        conn.execute(
            transfers.insert().values(
                month_id=month_id,
                from_field_id=field_db_id[id(t.from_field)],
                to_field_id=field_db_id[id(t.to_field)],
                day=int(t.day),
                amount=t.amount,
                amount_expr=t.amount_expr,
                note=t.note,
            )
        )


def _alloc_value(section: Section) -> str:
    if section.alloc_kind is AllocKind.PCT:
        return str(section.percentage.value)
    return str(section.amount.amount)


def delete_profile(conn, profile_id: int) -> None:
    """Cascade-delete a profile and all of its months + their children."""
    month_ids = [
        r.id for r in conn.execute(select(months.c.id).where(months.c.profile_id == profile_id))
    ]
    for mid in month_ids:
        _delete_children(conn, mid)
    conn.execute(delete(months).where(months.c.profile_id == profile_id))
    conn.execute(delete(profiles).where(profiles.c.id == profile_id))


# --- load -----------------------------------------------------------------
def load_month(conn, profile_id: int, key: MonthKey) -> Month | None:
    row = conn.execute(
        select(months).where(months.c.profile_id == profile_id, months.c.key == str(key))
    ).one_or_none()
    if row is None:
        return None

    month = Month(
        profile_id=row.profile_id,
        key=MonthKey.from_string(row.key),
        state=MonthState(row.state),
        id=row.id,
    )

    pocket_by_id: dict[int, Pocket] = {}
    for pr in conn.execute(
        select(pockets).where(pockets.c.month_id == row.id).order_by(pockets.c.position)
    ):
        p = Pocket(name=pr.name, is_default=bool(pr.is_default), position=pr.position, id=pr.id)
        month.pockets.append(p)
        pocket_by_id[pr.id] = p

    field_by_id: dict[int, Field] = {}
    for sr in conn.execute(
        select(sections).where(sections.c.month_id == row.id).order_by(sections.c.position)
    ):
        s = Section(
            name=sr.name,
            kind=SectionKind(sr.kind),
            alloc_kind=AllocKind(sr.alloc_kind),
            position=sr.position,
            percentage=Percentage(sr.alloc_value) if sr.alloc_kind == "pct" else None,
            amount=Money(sr.alloc_value) if sr.alloc_kind == "amount" else None,
            rest_routing=RestRouting(sr.rest_routing, sr.rest_target),
            carried_rest=sr.carried_rest,
            id=sr.id,
        )
        month.sections.append(s)
        for fr in conn.execute(
            select(fields).where(fields.c.section_id == sr.id).order_by(fields.c.position)
        ):
            cap = Cap.infinite() if fr.cap_kind == "inf" else Cap.finite(fr.cap_value)
            f = Field(
                name=fr.name,
                budget=fr.budget,
                current=fr.current,
                cap=cap,
                pocket=pocket_by_id[fr.pocket_id],
                position=fr.position,
                id=fr.id,
            )
            s.fields.append(f)
            field_by_id[fr.id] = f

    for ir in conn.execute(
        select(incomes).where(incomes.c.month_id == row.id).order_by(incomes.c.position)
    ):
        month.incomes.append(
            Income(name=ir.name, amount=ir.amount, kind=IncomeKind(ir.kind), position=ir.position, id=ir.id)
        )
    for tr in conn.execute(
        select(transactions).where(transactions.c.month_id == row.id).order_by(transactions.c.id)
    ):
        month.transactions.append(
            Transaction(
                field=field_by_id[tr.field_id],
                day=Day(tr.day),
                amount=tr.amount,
                amount_expr=tr.amount_expr,
                description=tr.description,
                id=tr.id,
            )
        )
    for tr in conn.execute(
        select(transfers).where(transfers.c.month_id == row.id).order_by(transfers.c.id)
    ):
        month.transfers.append(
            Transfer(
                from_field=field_by_id[tr.from_field_id],
                to_field=field_by_id[tr.to_field_id],
                day=Day(tr.day),
                amount=tr.amount,
                amount_expr=tr.amount_expr,
                note=tr.note,
                id=tr.id,
            )
        )
    return month