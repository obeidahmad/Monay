"""m0003 — sections gain ``color`` and ``icon`` (chosen in the web app).

Both nullable: NULL colour means "by position" (the palette order the TUI has
always used), NULL icon means none. Guarded like m0002, because a fresh
database gets the columns from m0001's ``create_all``.
"""

from __future__ import annotations

import sqlalchemy as sa

version = 3


def upgrade(conn: sa.Connection) -> None:
    columns = {c["name"] for c in sa.inspect(conn).get_columns("sections")}
    if "color" not in columns:
        conn.exec_driver_sql("ALTER TABLE sections ADD COLUMN color INTEGER")
    if "icon" not in columns:
        conn.exec_driver_sql("ALTER TABLE sections ADD COLUMN icon VARCHAR")
