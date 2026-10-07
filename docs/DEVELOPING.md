# Monay — Developer Guide

How the code is organized and how the pieces fit, for anyone reading or
modifying Monay. (User-facing concepts and commands live in the
[README](../README.md); how to cut a release is in [RELEASING.md](RELEASING.md).)

---

## 1. Architecture at a glance

Strict one-directional layering — nothing lower imports anything higher:

```
   web/     React app (browser) ── HTTP/JSON ──┐
                                               ▼
┌─ tui/     Textual: tab strip, command      api/   FastAPI: routes, wire
│           bar, screens, rendering                 format, error mapping
│      │ both call down                              │
├─ app/    application services (use cases) + the command registry
│      │ depends on PORTS only
├─ domain/ PURE Python: value objects, entities, the Month aggregate, the
│      │   budget math, domain services, and the repository/UoW PORTS
│      ▼
└─ data/   ADAPTERS: SQLAlchemy-Core repositories + Unit of Work that
           implement the domain ports; schema; migrations
```

- **`domain/` is pure** — no SQLAlchemy, no Textual, no FastAPI, no I/O. It
  *defines* the ports (typing `Protocol`s); it never imports `data/`.
- **`data/` implements those ports.** `data/` imports `domain/`, never the
  reverse. Dependencies point inward.
- **`app/` orchestrates through the ports**, never against a concrete DB type.
- **`tui/` and `api/` are two front doors to the same `app/` layer.** Neither
  imports the other, and no budgeting rule lives in either: a rule added to the
  domain shows up in the terminal and in the browser at once.
- **`web/` is a separate program** (TypeScript, in the browser). It knows the
  engine only through the HTTP API — and its types for that API are generated
  from it (§9).
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
    services.py      MonayApp — the session-bearing use-case facade (the TUI's)
    budgeting.py     BudgetingService — the stateless use cases (the API's)
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

  api/
    __main__.py      entry point: serve with uvicorn (python -m monay.api)
    app.py           create_app() — the FastAPI factory; wiring in the lifespan
    settings.py      configuration from the environment (MONAY_DB_URL, …)
    schemas.py       the wire format (Pydantic) — source of the web app's types
    parsing.py       request values → domain values, errors pinned to a field
    presenters.py    domain objects → response models
    errors.py        engine errors → HTTP status + one error shape
    deps.py          request-scoped dependencies (service, month key, If-Match)
    openapi.py       write the OpenAPI document (python -m monay.api.openapi)
    routes/          meta · profiles · months · incomes · sections ·
                     transactions · pockets

web/                 the web app (its own toolchain: Node, Vite, TypeScript)
  design/tokens.json the Monay design tokens, vendored from the design system
  scripts/           build-tokens.mjs — tokens.json → CSS custom properties
  src/
    api/             client.ts (typed fetch) · queries.ts (server state)
    app/             shell, providers, routing glue, the Sheet host
    components/      the design system's components, one per file
    features/        the screens and their forms, by tab
    lib/             money · expression · dates · budget helpers
    styles/          global.css (the ground, glass, type helpers)

Dockerfile           two images: the engine's API, and the web UI on nginx
compose.yaml         runs both (docker compose up)
docker/nginx.conf    the web container: static app + /api reverse proxy
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

A field's BUDGET is a fixed amount, or a % (`budget_pct`) resolved each
recompute — after sections get their AVAILABLE, before LEFT — as:

```
BUDGET   = pct × max(AVAILABLE − Σ fixed budgets in the section, 0)
           floored to whole cents (50% of 250.25 → 125.12)
```

Unlike section slices (kept at the full 4dp), a resolved budget is directly
spendable money, so it is quantized to 2dp with `Money.floor_cents` —
flooring, never rounding up, so %-fields can never sum past their base; the
shaved fraction stays in the section's REST and rolls over. Every %-field
shares that same base, so resolution is order-independent; a negative base
(fixed budgets exceed AVAILABLE — or AVAILABLE itself is negative) resolves
every %-budget to 0, the deficit staying visible through BUDGET LEFT and the
negative-REST warning.

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

A section also stores how it looks in the web app — a palette slot (`color`,
1–8) and an icon name (`icon`), both optional and carried forward on close. The
engine never reads them.

The schema is nine tables (`schema.py`): `profiles`, `months`, `pockets`,
`sections`, `fields`, `incomes`, `transactions`, `transfers`, `schema_version`.
Everything is scoped by profile; structure is snapshot per month and copied
forward on close; there are **no computed columns** (all derived values come
from `recompute()`). Migrations are forward-only modules under
`data/migrations/`, applied by `db.run_migrations` keyed off `schema_version`.

## 5. Composition root (`bootstrap.py`)

A `dependency-injector` container: `Singleton` engine (migrated on build) and
`Clock`; `Factory` `UnitOfWork`; `Singleton` `MonayApp` (the TUI's session) and
the command registry; `Singleton` `BudgetingService` (the API's use cases).
Tests swap any provider with a one-line `.override(...)` — the in-memory
`FakeUnitOfWork` makes service tests DB-free.

## 6. Application layer

There are two application services, because the two front ends hold their
context differently:

- **`MonayApp`** (`app/services.py`) is the TUI's facade. A terminal app is one
  long-lived process with one person looking at one month, so it keeps a
  **session** — current profile + viewed month — in memory.
- **`BudgetingService`** (`app/budgeting.py`) is the API's. HTTP has no session
  to lean on (two browser tabs are two independent callers), so it is
  **stateless**: every use case names the profile and month it acts on (§8).

Both depend only on the ports, and both do the same thing per use case: load the
month → call an aggregate mutator → save → commit. The rules stay in the
`Month` aggregate, which is what keeps the two from drifting.

The **command layer** (`app/commands/`) is spec-driven: every command is one
`CommandSpec` (`specs.py`) — path, argument schema, help, handler. The same
specs drive the parser (`parser.py`), `help`, and (later) autocomplete, so they
can never drift from execution. Completion (`completion.py`) emits names in
their final parseable form — names `shlex` would split are auto-quoted — so an
accepted suggestion always executes. Handlers (`handlers.py`) are thin glue to
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
field table. A row's name carries its toggle target in cell metadata (a custom
key, not Rich's `@click` — which would override the accent color and underline the
name); the app's `on_click` reads that meta to toggle the row, and
`expand`/`collapse` do the same from the command bar. The set of open rows lives
in `MonayApp.expanded_sections`.

## 8. HTTP API (`api/`)

A FastAPI application over `BudgetingService`. `create_app()` only *declares*
the API; the container is built in the lifespan hook, when a server actually
starts — so importing the module, or dumping its OpenAPI document, opens no
database. Everything is served under `/api` (interactive reference at
`/api/docs`), so a single reverse-proxy rule covers it.

Every handler does the same three things: read the request into domain values
(`parsing.py`), call one use case, present the result (`presenters.py`).

### Addressing and concurrency

A month's children have no stable database identity (`mappers.py` rewrites them
on each save), and names don't belong in URLs. So sections, fields, pockets and
income entries are addressed by their **position** in the month, transactions
and transfers by their **`#`**:

```
PATCH /api/profiles/1/months/2025-01/sections/1/fields/0
```

A position only means something for the version of the month the caller was
looking at. Each month therefore carries a **`revision`** — a content hash of
everything it stores (`month_revision`) — and every change must send the
revision it was based on in `If-Match`. If the month has changed since, the
service refuses with `StaleRevisionError` → **412**, rather than apply an edit
to whatever now sits at that position. This is ordinary optimistic concurrency,
and it is what makes two open tabs (or a phone and a laptop) safe.

A change responds with **the month it produced** (`ChangeOut.month`), so a
client never recomputes anything: what it shows is what the engine computed.

### Undo

Deletions happen immediately and return an `undo_token`.
`POST …/months/{key}/undo` puts the month back *exactly* as it was:
`UndoJournal` keeps the pre-change aggregate in memory for two minutes, and
restores it only if nothing else has happened to the month since. Being in
memory is deliberate (an undo that outlives the minute is not an undo), and it
is one reason the API runs as a **single process** — SQLite's single writer is
the other.

### Wire format

- **Money is a string** at the stored 4dp (`"332.9400"`), never a JSON number:
  a client would parse that as a float. The client does the 2dp display.
- **Typed amounts are expressions** (`"15.71+1.35"`); the server evaluates them
  with the engine's own evaluator.
- **Errors have one shape**, `{code, message, field}` (`errors.py`). `message`
  is written for a person; `field` names the input at fault when the server
  can tell, so a form can put the message under it.

| Status | When |
|---|---|
| 404 | the profile / month / position doesn't exist |
| 409 | a rule about the *state* refused it: duplicate name, closed month, field not empty, month not balanced, undo no longer possible |
| 412 | the `If-Match` revision is stale |
| 422 | a value is wrong: unreadable amount, percentage out of range, transfer above a MAX |

**Adding an endpoint:** add the use case to `BudgetingService`, its request
model to `schemas.py`, a handler in `routes/`, and run `npm run gen` in `web/`
— the new operation is then typed on the client.

## 9. Web app (`web/`)

React + TypeScript on Vite. Server state is TanStack Query; routing is React
Router (one URL per tab, `?month=yyyy-mm` to look at another month); the HTTP
client is `openapi-fetch`. Its own guide is [`web/README.md`](../web/README.md);
the essentials:

**Two files are generated and never committed** (`npm run gen`, which `dev` and
`build` run for you):

| Generated | From | Why |
|---|---|---|
| `src/api/schema.gen.ts` | the API's OpenAPI document (`python -m monay.api.openapi`) | the client's types *are* the server's schema — a renamed property is a compile error, not a runtime surprise |
| `src/styles/tokens.gen.css` | `design/tokens.json` | components reference CSS variables only; re-syncing the design system is "replace `tokens.json`" |

**The design system is the spec.** `web/design/tokens.json` is vendored from
the Monay design system, and `src/components/` holds the building blocks
(`Widget`, `Button`, `Sheet`, `Toast`, `SectionIcon`, the charts in
`charts.tsx`, …), each with a CSS module beside it. No component hard-codes a colour, a radius or
a font: if a value isn't a token, it doesn't belong in the stylesheet.

**Data flow.** `api/queries.ts` is the only place that talks to the server.
Reads are queries; a change is a typed action that sends the cached month's
`revision`, and puts the month the server returns straight into the cache.
Changes to a profile's months run one at a time, each reading the revision when
it runs, so a quick second edit builds on the first one's result.

**Money on the client is never a float.** `lib/money.ts` works on `bigint`
ten-thousandths and rounds half-to-even for display, mirroring
`Money.display()`; `lib/expression.ts` evaluates amount expressions as exact
fractions for the live "= 17.06" preview. The server remains the authority.

**Forms and feedback.** Every form is a `Sheet` (a native modal `<dialog>`),
opened through one host (`app/SheetHost.tsx`). A refusal from the API goes
under the input it names (`useSubmit`), never into a toast. One-step actions
(`useAct`) answer with a toast, and deletions offer **Undo** there instead of
asking first. Only closing a month and deleting a profile use a
`ConfirmDialog`.

---

## 10. Testing

```
uv run pytest                         # everything
uv run pytest tests/test_recompute.py # the engine's keystone test
cd web && npm test                    # the web app's unit tests (vitest)
```

| Layer | How it's tested | DB? |
|---|---|---|
| Value objects / expressions | pure units | no |
| `Month.recompute` | the sample budget, hand-verified | no |
| `MonthCloser` | close the sample → next month | no |
| Mutators & invariants | edge cases (cap, negative carry, advance, guards) | no |
| Application services | parsed command strings on a **fake UoW** | no |
| SQLAlchemy adapters, migrations | round-trip + guards on `:memory:`; rewind the schema, migrate | yes |
| TUI | Textual `run_test()` smoke | fake |
| Revision hash, undo journal | pure units (`test_budgeting.py`) | no |
| HTTP API | `TestClient` on the real app + engine (`test_api.py`) | `:memory:` |
| Web money maths | vitest on `web/src/lib` (`*.test.ts` beside the code) | no |

`tests/fixtures/sample_budget.py` is a small, neutral budget with round numbers,
designed so every value is hand-verifiable against §3's formulas while
exercising the interesting behaviors.

`tests/test_api.py` builds that same sample budget through the HTTP API and
checks it against the same hand-verified numbers, so the API cannot drift from
the engine unnoticed. It also covers what only exists at that layer: the
`If-Match` revision check, undo, error codes and which input they name.

The web tests cover the code that must agree with the engine to the last digit:
money formatting and rounding (`money.ts`), the amount-expression evaluator
(`expression.ts`) and the LEFT preview (`budget.ts`).

CI (`.github/workflows/ci.yml`) runs three jobs on every PR: the Python gate,
the web gate (prettier, tsc, eslint, vitest, production build) and a build of
both Docker images.

**Not covered yet:** the React components and whole-app flows in a browser.
Those are still checked by hand; component tests and a Playwright run against
the Docker stack are the next step.

## 11. Running & building

```
uv sync                      # dev environment (fetches Python 3.14)
uv run python -m monay       # the terminal app
uv run python -m monay.api   # the HTTP API, on http://127.0.0.1:8000
```

The API reads three environment variables (`api/settings.py`):
`MONAY_DB_URL` (default `sqlite:///monay.db`, the file the TUI uses),
`MONAY_API_HOST` (default `127.0.0.1` — the API has no authentication, so it
isn't offered to the network unless asked) and `MONAY_API_PORT` (default
`8000`). For a reloading server while working on it:

```
uv run uvicorn monay.api.app:create_app --factory --reload
```

The web app runs beside it, forwarding `/api` to the API:

```
cd web
npm install
npm run dev                  # http://localhost:5173 (regenerates types + tokens first)
npm run typecheck && npm run lint && npm test
```

### Docker

```
docker compose up --build    # http://localhost:8080
```

One `Dockerfile`, two targets. `api` is the virtualenv on a slim Python image,
run as an unprivileged user, with the database in a volume at `/data`. `web` is
the built app on nginx, which also forwards `/api` to the engine — the browser
only ever talks to one origin, so there is no CORS to configure and no API
address baked into the bundle. They share a build stage because the web build
needs the Python package to produce the OpenAPI document its types come from.

The version in an image comes from the `MONAY_VERSION` build argument (there is
no `.git` in a build context for hatch-vcs to read):
`MONAY_VERSION=1.2.0 docker compose build`.

### Standalone binaries

The terminal app can still be packaged locally by PyInstaller (`monay.spec`);
see the README's build section. CI no longer builds or publishes binaries — the
web app needs a server and a browser, so Docker is how Monay ships.
