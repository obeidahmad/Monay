<div align="center">

# 💰 Monay

**A calm web app for zero-based budgeting — with monthly rollover, pockets, and a flexible section model.**

Built with Python 3.14 · a pure budgeting engine behind a [FastAPI](https://fastapi.tiangolo.com/) API and a [React](https://react.dev/) UI.

![Python](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/UI-React-61DAFB?logo=react&logoColor=black)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

---

Monay brings **zero-based, envelope-style budgeting** to your browser — give
every dollar a job, then watch what you don't spend roll forward in its pot.
You define your own **sections** and **fields**, log spending as you go, and at
month-end **close** the month — unused money rolls forward, pots carry over, and
the next month is created for you automatically.

Monay runs locally: one command starts the engine and opens the app in your
browser. Your data stays in a `monay.db` file on your machine.

## ✨ Features

- **Zero-based by design** — every dollar of income gets a job: tax-sections skim a % off fresh income first, pre-sections come off the top, post-sections split the rest and must sum to 100%. Define your own tax/pre/post sections and fields — no two budgets look alike.
- **Envelope rollover** — close a month and unspent budget rolls forward into each field's envelope (its pot), capped at a per-field max (finite or ∞); section leftovers route to next month's income, back into themselves, or into another section.
- **Pockets** — per-account "how much should I have here right now?" counters, so you can reconcile against reality.
- **Borrowing, modeled honestly** — fields and sections can go negative (red) and heal over future months; supports one-time "advance" budgets.
- **Expressions everywhere** — type `15.71+1.35` or `(7.81)/2+6.5` for any amount.
- **Point and click** — add, edit and remove everything with buttons and forms; an accordion Budget view, live expression previews, and dark + light modes. Works on desktop and phone-sized screens.
- **Money done right** — `Decimal`, 4-decimal storage with banker's rounding; no floats ever touch a value.
- **Multiple profiles** — fully independent budgets in one app.

## 🚀 Install & run

### Standalone binary (no Python or Node needed)

Download the binary for your OS/arch from the [**Releases**](../../releases)
page, then run it:

```bash
# Linux / macOS
chmod +x monay-linux-x86_64
./monay-linux-x86_64

# Windows (PowerShell)
.\monay-windows-x86_64.exe
```

Monay starts a local server and opens **http://localhost:8765** in your
browser (press `Ctrl+C` in the terminal to stop it).

> Monay stores your data in a `monay.db` file in the **current working
> directory**, so run it from a folder you'll remember.

### From source (developers)

Monay uses [**uv**](https://docs.astral.sh/uv/) for the Python engine and
**npm** (Node 20+) for the web UI.

```bash
uv sync                                  # create the venv + install deps (fetches Python 3.14)
(cd web && npm install && npm run build) # build the React UI into monay/web/static
uv run python -m monay                   # launch: serves the app and opens your browser
uv run pytest                            # run the test suite
```

`MONAY_PORT` / `MONAY_HOST` change where it listens; `MONAY_NO_BROWSER=1` skips
opening a browser tab.

## 🧩 Concepts

A quick mental model — five ideas:

- **Income** enters the month as one or more named entries.
- **Sections** each receive a slice of income, called **AVAILABLE**:
  - **Tax-sections** come off the very top — a % of *fresh* income only
    (leftovers carried from last month were already taxed, so they're excluded).
  - **Pre-sections** are taken off the top next, in order — a fixed amount or a %
    of what income remains (e.g. rent, savings, charity).
  - **Post-sections** split whatever's left by percentage; their percentages
    must sum to **100%** (e.g. Needs 50 / Wants 30 / Savings 20).
- **Fields** are the budget lines inside a section. Each has a **BUDGET** (what
  you feed it this month — a fixed amount, or a % of the section's AVAILABLE
  remaining after its fixed budgets), a **CURRENT** pot (carried from last
  month), and a **MAX** rollover cap (a number, or **∞**).
- **Pockets** are where money physically sits (Main, Bank, Broker…). Each
  field belongs to one; a pocket's counter is the sum of its fields' balances —
  what you should actually have in that account.
- **Closing** a month rolls everything forward and locks it.

The core formula, per field:

```
LEFT     = min(CURRENT + BUDGET − PAID, MAX)     ← your pot after this month
```

Underspend and the pot grows (capped at MAX); overspend and it goes **red** and
is repaid by future budgets. A section's unused slice is its **REST**, which on
close routes to next month's income, back into the section, or into another one.

## 📖 Using Monay

Everything is a button or a form. Amount fields accept arithmetic
(`15.71+1.35`) and show the result as you type.

### First month, from scratch

1. **Create a profile** — the welcome screen asks for a name. This creates the
   current month and a default **Main** pocket.
2. **Add income** (Budget → *Add income*) — as many entries as you like.
3. **Add sections** (*Add section*) — pick **Tax** (a % of fresh income, off the
   very top), **Pre** (a fixed amount or a %, off the top) or **Post** (a % of
   the remainder; post sections must add up to 100%). The headline shows
   `Σ%` with ✓ when balanced.
4. **Add fields** — from a section's `⋯` menu → *Add field*: a monthly budget
   (an amount, or a % of the section's available after its fixed budgets) and an
   optional max (rollover cap; ∞ by default).
5. In your first month only, click a field and set its **Current** pot to what
   it already holds.
6. **Add transaction** (the primary button, or `+` on mobile) — pick a field
   (recent ones are one tap away), an amount, the day (defaults to today) and a
   description. The toast tells you what's left.

### Finding your way

- **Budget** — the month headline (income, post pool, allocation), an
  allocation bar, and the section accordion: click a section to expand its field
  table inline (any number at once, or *Expand all*). Each row shows avail, rest
  (⚠ when negative) and where its rest goes at close. Click a field row to edit
  it; the `⋯` menus hold add/edit/transfer/delete.
- **Transactions** — newest first, filterable by field or text; edit or delete
  from each row's `⋯` menu. *Transfer* moves pot money between fields (refused
  if it would break the target's max). Transfers are listed below.
- **Pockets** — how much each place should hold right now, with a per-field
  breakdown; the default pocket also holds live section rests.
- **Settings** — add, switch, rename and delete profiles; choose System, Light
  or Dark appearance.
- **History** — every month with income, spent and leftovers. Open a past month
  to view it read-only, then *Back to open month*.
- **Help** — the concepts above, in the app.

On a phone, a bottom tab bar holds Budget, Transactions, Pockets and **More**
(History, Settings, Help); forms open as bottom sheets.

### Closing a month

*Close month* shows a summary — leftovers going to next month's income and any
rests that carry — and asks you to confirm. It then locks the month and creates
the next: field pots carry forward as next month's current, section rests route
per their setting, and a single **Leftovers** income entry is created. Deleting a
profile, section, field, income, pocket or transaction also asks first.

## 🏗️ Building a standalone binary

PyInstaller produces a one-file binary containing the engine and the built UI;
it bundles the host interpreter, so **build on the OS/arch you're targeting**
(no cross-compiling).

```bash
(cd web && npm ci && npm run build)            # the UI must be built first
uv sync --no-dev --group build
uv run --group build pyinstaller monay.spec    # → dist/monay  (or dist/monay.exe)
```

The [`.github/workflows/build.yml`](.github/workflows/build.yml) workflow builds
**Linux** and **Windows** binaries for both **x86_64** and **arm64**, and
publishes them as a stable versioned release on each **`v*`** tag (see
[docs/RELEASING.md](docs/RELEASING.md)).

## 📁 Project layout

```
monay/
  domain/      pure engine: value objects, Month aggregate + recompute, closing, ports
  data/        SQLAlchemy Core adapters, schema, migrations, unit of work
  app/         use-case services + input interpreters (amounts, %, caps, routing)
  web/         FastAPI JSON API + presenter; serves the built UI from web/static
  bootstrap.py composition root (dependency-injector container)
web/           React + Vite + TypeScript frontend (npm run build → monay/web/static)
tests/         unit + engine + adapter + API tests
docs/          DEVELOPING (code guide)
```

Contributors: see **[CONTRIBUTING.md](CONTRIBUTING.md)** for the development
loop and **[docs/DEVELOPING.md](docs/DEVELOPING.md)** for how the code is
organized.

## 📜 License

MIT — see [`LICENSE`](LICENSE).
