"""m0002 — fields gain ``budget_pct`` (percentage-based field budgets).

Nullable decimal text, like sections' ``alloc_value``; NULL means a fixed
budget. Guarded by a column-existence check because a fresh database gets the
column from m0001's ``create_all`` (which builds the *current* schema) and this
migration still runs after it.
"""

from __future__ import annotations

import sqlalchemy as sa

version = 2


def upgrade(conn: sa.Connection) -> None:
    columns = {c["name"] for c in sa.inspect(conn).get_columns("fields")}
    if "budget_pct" not in columns:
        conn.exec_driver_sql("ALTER TABLE fields ADD COLUMN budget_pct VARCHAR")
