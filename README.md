<div align="center">

# 💰 Monay

**A modern terminal budget app with monthly rollover, pockets, and a flexible section model.**

Built with [Textual](https://textual.textualize.io/) · Python 3.14 · a pure, fully-tested budgeting engine.

![Python](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)
![Textual](https://img.shields.io/badge/TUI-Textual-5A4FCF)
![Tests](https://img.shields.io/badge/tests-passing-3FB950)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

---

Monay replaces a spreadsheet budget with a fast, keyboard-driven terminal app.
You define your own **sections** and **fields**, log spending as you go, and at
month-end **close** the month — unused money rolls forward, pots carry over, and
the next month is created for you automatically.

```
 Monay  ┃ Budget ┃ Transactions │ Pockets │ Settings      Docs │ History
─────────────────────────────────────────────────────────────────
 January 2025   ● open                           Profile: alex
─────────────────────────────────────────────────────────────────
 SECTIONS                              avail        rest
 ▍Bills      pre · 500                500.00        0.00
 ▍Needs      post · 50%               750.00      350.00
 ▍Wants      post · 30%               450.00      300.00
 ▍Savings    post · 20%               300.00       60.00
                                  ──────────
 income 2000.00 · post pool 1500.00 · Σ% = 100 ✓
─────────────────────────────────────────────────────────────────
 ✓ Groceries −17.06 → LEFT 332.94 (Needs REST 350.00)
 > _
```

## ✨ Features

- **Dynamic structure** — define your own pre/post sections, fields, and pockets. No two budgets need look alike.
- **Monthly rollover** — close a month and unspent budget rolls into pots (with per-field caps, finite or ∞); section leftovers route to next month's income, back into themselves, or into another section.
- **Pockets** — per-account "how much should I have here right now?" counters, so you can reconcile against reality.
- **Borrowing, modeled honestly** — fields and sections can go negative (red) and heal over future months; supports one-time "advance" budgets.
- **Expressions everywhere** — type `15.71+1.35` or `(7.81)/2+6.5` for any amount.
- **Command-driven** — everything happens by typing bare-verb commands in one bar; arrows are only for navigation.
- **Money done right** — `Decimal`, 4-decimal storage with banker's rounding; no floats ever touch a value.
- **Multiple profiles** — fully independent budgets in one app.

## 🚀 Install & run

### Standalone binary (no Python needed)

Download the binary for your OS/arch from the [**Releases**](../../releases)
page, then run it from a terminal:

```bash
# Linux / macOS
chmod +x monay-linux-x86_64
./monay-linux-x86_64

# Windows (PowerShell)
.\monay-windows-x86_64.exe
```

> Monay stores your data in a `monay.db` file in the **current working
> directory**, so run it from a folder you'll remember.

### From source (developers)

Monay uses [**uv**](https://docs.astral.sh/uv/) for environment and dependency
management.

```bash
uv sync                      # create the venv + install deps (fetches Python 3.14)
uv run python -m monay       # launch the app
uv run pytest                # run the test suite
```

## 🧩 Concepts

A quick mental model — five ideas:

- **Income** enters the month as one or more named entries.
- **Sections** each receive a slice of income, called **AVAILABLE**:
  - **Pre-sections** are taken off the top, in order — a fixed amount or a % of
    what income remains (e.g. rent, savings, charity).
  - **Post-sections** split whatever's left by percentage; their percentages
    must sum to **100%** (e.g. Needs 50 / Wants 30 / Savings 20).
- **Fields** are the budget lines inside a section. Each has a **BUDGET** (what
  you feed it this month), a **CURRENT** pot (carried from last month), and a
  **MAX** rollover cap (a number, or **∞**).
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

Everything is a typed command. Names are case-insensitive; quote names with
spaces (`"Emergency Fund"`); amounts accept arithmetic.

### First month, from scratch

```text
profile add alex                  # create + select a profile (auto-creates the month + a Main pocket)
income add Salary 2000            # add income (have as many entries as you like)

section add pre  Bills 500        # pre-section: a fixed amount off the top (or a %)
section add post Needs 50%        # post-sections split the remainder; must sum to 100%
section add post Wants 30%
section add post Savings 20%

field add Needs Groceries 300 400  # field with budget 300, max 400 (use `inf` for ∞)
field set  Groceries current 100   # type your carried-over pot (first month only)

add Groceries 15.71+1.35 d5 weekly shop   # log a transaction (d5 = day 5; day defaults to today)
```

### Navigating

The screen has two panes: working tabs on the left (Budget, Transactions,
Pockets, Settings) and helper tabs on the right (**Docs**, **History**).

`open <section>` drills into a section's fields · `back` / `Esc` returns ·
`goto <tab>` switches tab (either pane) · `Tab` cycles tabs · `Ctrl+B` toggles
the helper pane.

### Closing a month

```text
close          # shows a summary, asks Type Yes or No, then locks the month and creates the next
```

Field pots carry forward as next month's `current`; section RESTs route per
their setting; a single **Leftovers** income entry is created. Closed months are
read-only in **History** (`month 2025-01` to view, `month` to return).

<details>
<summary><b>Full command reference</b></summary>

| Command | Effect |
|---|---|
| `add <field> <amount> [d<day>] [desc…]` | Record a transaction |
| `transfer <amount> <from> <to> [d<day>] [note…]` | Move pot money between fields |
| `tx [filter]` · `tx edit <#> <attr> <val>` · `tx del <#>` | View / edit / delete transactions |
| `section add pre\|post <name> <pct%\|amount>` | Create a section |
| `section set <name> pct\|amount\|name\|rest <value>` | Edit a section (`rest` = `income`/`self`/`<section>`) |
| `section order <name> <pos>` · `section del <name>` | Reorder / delete a section |
| `field add <section> <name> [budget] [max\|inf]` | Create a field |
| `field set <name> budget\|max\|pocket\|name\|current <value>` | Edit a field |
| `field del <name>` | Delete a field (only when empty) |
| `income add\|set\|del …` | Manage income entries |
| `pocket add\|rename\|del <name>` · `pocket main <name>` | Manage pockets |
| `month [<yyyy-mm>]` · `close` | View a month / close the open one |
| `open <section>` · `back` · `goto <tab>` | Navigation |
| `profile add\|switch\|rename\|del <name>` | Manage profiles |
| `help [command]` | Open the Docs tab — the full command reference (filter by command) |
| `quit` | Exit |

</details>

## 🏗️ Building a standalone binary

PyInstaller produces a one-file binary; it bundles the host interpreter, so
**build on the OS/arch you're targeting** (no cross-compiling).

```bash
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
  app/         use-case services + the spec-driven command registry
  tui/         Textual app: shell, command bar, theme, screens, widgets
  bootstrap.py composition root (dependency-injector container)
tests/         unit + engine + adapter + headless-TUI tests
docs/          DEVELOPING (code guide) · PLAN (roadmap)
```

Contributors: see **[CONTRIBUTING.md](CONTRIBUTING.md)** for the development
loop, **[docs/DEVELOPING.md](docs/DEVELOPING.md)** for how the code is organized,
and **[docs/PLAN.md](docs/PLAN.md)** for what's next.

## 📜 License

MIT — see [`LICENSE`](LICENSE).
