# Monay — Developer Guide

How the code is organized and how the pieces fit, for anyone reading or
modifying Monay. (User-facing concepts and commands live in the
[README](../README.md); the remaining roadmap is in [PLAN.md](PLAN.md); how to
cut a release is in [RELEASING.md](RELEASING.md).)

---

## 1. Architecture at a glance

Strict one-directional layering — nothing lower imports anything higher:

```
┌─ tui/     Textual: tab strip, command bar, screens, rendering
│      │ calls down
├─ app/    application services (use cases) + the command registry
│      │ depends on PORTS only
├─ domain/ PURE Python: value objects, entities, the Month aggregate, the
│      │   budget math, domain services, and the repository/UoW PORTS
│      ▼
└─ data/   ADAPTERS: SQLAlchemy-Core repositories + Unit of Work that
           implement the domain ports; schema; migrations
```

- **`domain/` is pure** — no SQLAlchemy, no Textual, no I/O. It *defines* the
  ports (typing `Protocol`s); it never imports `data/`.
- **`data/` implements those ports.** `data/` imports `domain/`, never the
  reverse. Dependencies point inward.
- **`app/` orchestrates through the ports**, never against a concrete DB type.
- **`bootstrap.py`** is the single composition root — the only place that names
  every concrete type and wires them via a DI container.

## 2. Package map

```
monay/
  __main__.py        entry point: build the container, run the app
  bootstrap.py       dependency-injector Container (composition root)

  domain/            (pure)
    money.py         Money value object — 4dp, banker's rounding
    expressions.py   safe "15.71+1.35" → Money (AST whitelist)
    values.py        Cap, Percentage, MonthKey, Day, RestRouting
    entities.py      Profile, Pocket, Section, Field, Income, Transaction, Transfer
    month.py         the Month AGGREGATE: recompute() + all mutators
    closing.py       MonthCloser domain service (close + rollover)
    ports.py         Protocols: Clock, MonthRepository, ProfileRepository, UnitOfWork
    errors.py        the domain exception hierarchy

  data/              (adapters)
    schema.py        SQLAlchemy Core Table/MetaData (9 tables) + MoneyType
    mappers.py       rows ↔ domain graph (whole-aggregate load/save)
    repositories.py  SqlAlchemy{Month,Profile}Repository
    unit_of_work.py  SqlAlchemyUnitOfWork (one transaction)
    db.py            engine factory + forward-only migration runner
    migrations/      versioned migration modules (0001_initial, …)

  app/
    services.py      MonayApp — the session-bearing use-case facade
    clock.py         SystemClock adapter
    errors.py        application/command errors
    commands/        registry.py · parser.py · specs.py · handlers.py

  tui/
    app.py           Monay(App): shell, two-pane tabs, context bar, feedback, loop
    command_bar.py   the input widget (history, Esc-clear)
    theme.py         palette / section accents / column colors
    format.py        money formatting helpers
    screens/         budget · transactions · pockets · settings · docs · history
    widgets/         accordion · divider
```

---

## 3. The domain model (the heart)

Stateful, persistence-ignorant plain objects. `Month.recompute()` fills the
computed attributes in place. Names match the user-facing concepts in the
README exactly.

### Money

`Decimal` quantized to **4 decimal places**, **ROUND_HALF_EVEN** (banker's).
The stored 4dp value is the truth; `Money.display()` gives a cosmetic 2dp view.
All arithmetic goes through `Money`, and **floats are rejected** so no float
ever touches a value. In SQLite, money is stored as TEXT via `MoneyType`.

### Value objects (`values.py`)

| VO | Purpose |
|---|---|
| `Cap` | rollover MAX: `Cap.finite(x)` or `Cap.infinite()`; `.clamp(value)` |
| `Percentage` | a section's share, 0–100; `.of(amount)` |
| `MonthKey` | `yyyy-mm`, ordered; `.next()` / `.previous()` / `.from_date()` |
| `Day` | day-of-month 1–31 |
| `RestRouting` | `to_income()` \| `to_self()` \| `to_section(name)` |

### Entities & the aggregate

`Month` is the **aggregate root** and the consistency boundary. It owns
`Income[]`, `Pocket[]`, `Section[]` (each with `Field[]`), `Transaction[]`, and
`Transfer[]`. Outside code never mutates a `Field`/`Section` directly — it calls
intention-revealing methods on the root (`add_transaction`, `set_field_budget`,
`transfer`, `add_field`, …), each of which enforces its invariant and leaves the
month recomputed. `Profile` is a separate aggregate, referenced by id.

### The budget math (`Month.recompute`)

The sample test fixture and the engine test verify these formulas by hand.

Per **field**, with `PAID = Σ transaction amounts on it`:

```
LEFT     = min(CURRENT + BUDGET − PAID, MAX)      (no cap if MAX = ∞)
CONSUMED = LEFT − CURRENT + PAID                  (what it took from the section)
```

**FRESH INCOME** = Σ income that is not a leftover (`IncomeKind.LEFTOVER`).
Leftovers were already taxed when they first arrived last month, so they are
excluded from the tax base; `total_income` still includes them.

On the Budget tab, income is shown as a synthetic **income pseudo-section** — a
distinct row above the real sections carrying `total_income`, expandable (like any
section, via `expand income` or a click) to list the individual entries. It is not
a real `Section` (the name `income` is reserved, so no section can shadow it); it
just renders income on the same tab whether or not any section exists yet.

Per **section**:

```
AVAILABLE   = its income slice (+ any REST routed in last month)
REST        = AVAILABLE − Σ CONSUMED              (can be negative)
BUDGET LEFT = AVAILABLE − Σ field budgets         (planning indicator only)
```

Allocation order: **tax-sections** take their share off the top first — a % of
**fresh income** only (never of leftovers; every tax-section taxes the same fresh
base, they don't compound); then **pre-sections** take their share off what's
left, in `position` order (a fixed amount, or a % of the income *remaining* at
that point); then **post-sections** split what remains by percentage (the
percentages must sum to 100%). Per **pocket**: `counter = Σ LEFT of its fields`;
the default pocket also adds the live section RESTs and any income not given to a
section. **Transfers** are applied last and relocate `LEFT` only — they never
touch PAID/CONSUMED/REST.

`recompute()` also collects **warnings** (negative REST, post-% ≠ 100).

### Closing & rollover (`closing.py`)

`MonthCloser.close(month)` finalizes the month, routes each section's REST
(income → a single Leftovers entry; self/other → that section's `carried_rest`
next month, falling back to income if the target is gone), creates the next
month with the structure copied forward and each field's `current = its final
LEFT`, then locks the closed month forever.

---

## 4. Ports & adapters (the DI seam)

`domain/ports.py` declares `Clock`, `MonthRepository`, `ProfileRepository`, and
`UnitOfWork` as `Protocol`s. Application services depend only on these.

`data/` implements them with SQLAlchemy Core. A `Month` is loaded and saved as
one **whole graph** (`mappers.py` uses delete-and-reinsert of child rows on
save). The **Unit of Work** owns one transaction and exposes the repositories:

```python
with uow:
    month = uow.months.get(profile_id, key)
    month.add_transaction(...)   # the aggregate enforces invariants
    uow.months.save(month)
    uow.commit()                 # atomic; rollback on exception
```

The schema is nine tables (`schema.py`): `profiles`, `months`, `pockets`,
`sections`, `fields`, `incomes`, `transactions`, `transfers`, `schema_version`.
Everything is scoped by profile; structure is snapshot per month and copied
forward on close; there are **no computed columns** (all derived values come
from `recompute()`). Migrations are forward-only modules under
`data/migrations/`, applied by `db.run_migrations` keyed off `schema_version`.

## 5. Composition root (`bootstrap.py`)

A `dependency-injector` container: `Singleton` engine (migrated on build) and
`Clock`; `Factory` `UnitOfWork`; `Singleton` `MonayApp` (the session) and the
command registry. Tests swap any provider with a one-line `.override(...)` — the
in-memory `FakeUnitOfWork` makes service tests DB-free.

## 6. Application layer

`MonayApp` (`app/services.py`) is the use-case facade. It holds the session
(current profile + the month being viewed) and depends only on the ports. Each
use case: load the active month → call an aggregate mutator → save → commit.

The **command layer** (`app/commands/`) is spec-driven: every command is one
`CommandSpec` (`specs.py`) — path, argument schema, help, handler. The same
specs drive the parser (`parser.py`), `help`, and (later) autocomplete, so they
can never drift from execution. Handlers (`handlers.py`) are thin glue to
`MonayApp`.

**Adding a command:** add a `CommandSpec` in `specs.py`, write its `h_*` handler
in `handlers.py`, and add the use case to `MonayApp` if needed. Parser, help,
and autocomplete pick it up automatically.

## 7. TUI

`Monay(App)` (`tui/app.py`) hosts the context bar (month · state · profile), a
two-pane body, the feedback line, and the command bar. The body has a **left
pane** of working tabs (budget · transactions · pockets · settings) and a **right
pane** of helper tabs (docs · history); `Ctrl+B` toggles the right pane and a
draggable `PaneDivider` (`widgets/divider.py`) — or `Ctrl+←`/`Ctrl+→` — resizes
it (`_set_helper_width` clamps the split). The command loop is: parse via the
registry → run against `MonayApp` → render the
result (✓ / ✗ / a typed `Yes`/`No` confirmation). The Docs tab (`screens/docs.py`)
renders the man-style reference straight from `REGISTRY.specs()`, so it never
drifts from what the app accepts; `help` selects it (`help <command>` filters it).
Tab screens build Rich renderables; `format.py` + `theme.py` handle colors. The
Budget tab is an **accordion** (`widgets/accordion.py`): one summary row per
section (plus the income pseudo-section), any number expandable inline to their
field table. A row's name carries a Rich `@click` action (`app.toggle_section` /
`app.toggle_income`) so clicking toggles it; `expand`/`collapse` do the same from
the command bar. The set of open rows lives in `MonayApp.expanded_sections`.

---

## 8. Testing

```
uv run pytest                         # everything
uv run pytest tests/test_recompute.py # the engine's keystone test
```

| Layer | How it's tested | DB? |
|---|---|---|
| Value objects / expressions | pure units | no |
| `Month.recompute` | the sample budget, hand-verified | no |
| `MonthCloser` | close the sample → next month | no |
| Mutators & invariants | edge cases (cap, negative carry, advance, guards) | no |
| Application services | parsed command strings on a **fake UoW** | no |
| SQLAlchemy adapters | round-trip + guards on `:memory:` | yes |
| TUI | Textual `run_test()` smoke | fake |

`tests/fixtures/sample_budget.py` is a small, neutral budget with round numbers,
designed so every value is hand-verifiable against §3's formulas while
exercising the interesting behaviors.

## 9. Running & building

```
uv sync                  # dev environment (fetches Python 3.14)
uv run python -m monay   # run the app
```

Standalone binaries are produced by PyInstaller (`monay.spec`) and CI
(`.github/workflows/build.yml`); see the README's build section.
