"""SQLAlchemy Core schema — the 9 tables from docs/DEVELOPING.md.

Money is stored via :class:`MoneyType`, a ``String``-backed decimal: the 4dp
value is persisted as TEXT and read back as ``Money``, so no float ever touches
a value round-trip (docs/DEVELOPING.md). No computed columns — PAID/LEFT/
CONSUMED/AVAILABLE/REST/counters are always recomputed from inputs on load.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator

from monay.domain.money import Money


class MoneyType(TypeDecorator[Money]):
    """Persists ``Money`` as a 4dp decimal string (TEXT); reads back ``Money``."""

    impl = sa.String
    cache_ok = True

    def process_bind_param(self, value: Money | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        m = value if isinstance(value, Money) else Money(value)
        return str(m.amount)

    def process_result_value(self, value: Any, dialect: Dialect) -> Money | None:
        return None if value is None else Money(value)


metadata = sa.MetaData()

profiles = sa.Table(
    "profiles",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String, nullable=False, unique=True),
    sa.Column("currency_symbol", sa.String, nullable=False, default="€"),
    sa.Column("created_at", sa.Date),
)

months = sa.Table(
    "months",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("profile_id", sa.Integer, sa.ForeignKey("profiles.id"), nullable=False),
    sa.Column("key", sa.String, nullable=False),
    sa.Column("state", sa.String, nullable=False),
    sa.UniqueConstraint("profile_id", "key", name="uq_month_profile_key"),
)

pockets = sa.Table(
    "pockets",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("month_id", sa.Integer, sa.ForeignKey("months.id"), nullable=False),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("is_default", sa.Boolean, nullable=False, default=False),
    sa.Column("position", sa.Integer, nullable=False, default=0),
    sa.UniqueConstraint("month_id", "name", name="uq_pocket_month_name"),
)

sections = sa.Table(
    "sections",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("month_id", sa.Integer, sa.ForeignKey("months.id"), nullable=False),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("kind", sa.String, nullable=False),  # tax | pre | post
    sa.Column("position", sa.Integer, nullable=False, default=0),
    sa.Column("alloc_kind", sa.String, nullable=False),  # pct | amount
    sa.Column("alloc_value", sa.String, nullable=False),  # decimal text (pct or amount)
    sa.Column("rest_routing", sa.String, nullable=False),  # income | self | section
    sa.Column("rest_target", sa.String),  # section name when routing == section
    sa.Column("carried_rest", MoneyType, nullable=False),
    sa.UniqueConstraint("month_id", "name", name="uq_section_month_name"),
)

fields = sa.Table(
    "fields",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("section_id", sa.Integer, sa.ForeignKey("sections.id"), nullable=False),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("budget", MoneyType, nullable=False),
    sa.Column("current", MoneyType, nullable=False),
    sa.Column("cap_kind", sa.String, nullable=False),  # finite | inf
    sa.Column("cap_value", MoneyType),  # null when infinite
    sa.Column("pocket_id", sa.Integer, sa.ForeignKey("pockets.id"), nullable=False),
    sa.Column("position", sa.Integer, nullable=False, default=0),
    sa.UniqueConstraint("section_id", "name", name="uq_field_section_name"),
)

incomes = sa.Table(
    "incomes",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("month_id", sa.Integer, sa.ForeignKey("months.id"), nullable=False),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("amount", MoneyType, nullable=False),
    sa.Column("kind", sa.String, nullable=False),  # manual | leftover
    sa.Column("position", sa.Integer, nullable=False, default=0),
)

transactions = sa.Table(
    "transactions",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("month_id", sa.Integer, sa.ForeignKey("months.id"), nullable=False),
    sa.Column("field_id", sa.Integer, sa.ForeignKey("fields.id"), nullable=False),
    sa.Column("day", sa.Integer, nullable=False),
    sa.Column("amount", MoneyType, nullable=False),
    sa.Column("amount_expr", sa.String, nullable=False, default=""),
    sa.Column("description", sa.String, nullable=False, default=""),
)

transfers = sa.Table(
    "transfers",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("month_id", sa.Integer, sa.ForeignKey("months.id"), nullable=False),
    sa.Column("from_field_id", sa.Integer, sa.ForeignKey("fields.id"), nullable=False),
    sa.Column("to_field_id", sa.Integer, sa.ForeignKey("fields.id"), nullable=False),
    sa.Column("day", sa.Integer, nullable=False),
    sa.Column("amount", MoneyType, nullable=False),
    sa.Column("amount_expr", sa.String, nullable=False, default=""),
    sa.Column("note", sa.String, nullable=False, default=""),
)

schema_version = sa.Table(
    "schema_version",
    metadata,
    sa.Column("version", sa.Integer, primary_key=True),
)
