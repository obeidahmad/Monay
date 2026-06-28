# Monay — Roadmap

What's built and what's left. (How the code is organized:
[DEVELOPING.md](DEVELOPING.md). How to use the app: [README](../README.md).)

---

## Done

The full app is built and tested, inward-out (pure domain first, proven by a
hand-verified engine test, then persistence, wiring, and the TUI):

- **Domain** — `Money` (4dp/banker's) + safe expressions + value objects; the
  `Month` aggregate with `recompute()`; mutators with their invariants; the
  `MonthCloser` close/rollover service.
- **Persistence** — SQLAlchemy Core schema + mappers, repositories, Unit of
  Work, engine factory, and a forward-only migration runner.
- **Wiring** — the dependency-injector composition root; the `MonayApp` use-case
  facade; the spec-driven command registry (parser + help + execution from one
  source).
- **TUI** — the Textual shell (tabs, context bar, feedback line, command loop)
  and all five tabs: Budget (accordion sections), Transactions, Pockets,
  History, Settings.
- **Packaging** — a PyInstaller spec and a GitHub Actions matrix that builds
  Linux + Windows binaries (x86_64 and arm64) and smoke-tests each one.

This is the running v0: create a profile, define sections/fields/pockets, log
transactions and transfers, watch budgets/rollovers/pocket counters, browse
history, and close a month into the next.

## Next

- **Autocomplete** — dropdown + ghost-text in the command bar, driven entirely
  by the command registry (verbs, then section/field/pocket names, then argument
  hints), so it never drifts from execution.
- **Onboarding & polish** — empty-state hints per tab, a guided first-month
  setup flow, a startup **multi-profile picker** that remembers the last-used
  profile, and a final theme pass.

## Smaller improvements (surfaced in real use)

- Show each section's **REST routing** somewhere in the UI (it can be set but
  not seen).
- Store the database in a per-user data directory instead of the current working
  directory, so the standalone binary behaves predictably wherever it's run.
- Optional: a combined `field set` that takes several attributes at once.

## Deferred

- **Computed / remainder-split budget fields** (e.g. "split whatever's left
  between two fields"), and any other formula-driven budgets — fixed budgets
  cover v1.
