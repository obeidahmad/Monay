# Contributing to Monay

Thanks for taking the time. This documents the day-to-day development loop —
how an idea becomes a merged change. For how the *code* is organized, read the
[Developer Guide](docs/DEVELOPING.md); for how a release is cut, read
[RELEASING.md](docs/RELEASING.md).

The loop is deliberately small: **issue → branch → PR → review → squash-merge.**
CI is the hard gate, an automated review is advisory, and a human always clicks
merge.

---

## Setup

Monay uses [**uv**](https://docs.astral.sh/uv/) for everything — environment,
dependencies, and running tools. There is no global `pip`; every command is
`uv run …`.

```bash
git clone https://github.com/obeidahmad/Monay
cd Monay
uv sync --group dev     # venv + deps (fetches Python 3.14) + dev tools
uv run python -m monay  # launch the app
uv run pytest           # run the suite
```

To open and address issues/PRs from the terminal you'll also want the
[GitHub CLI](https://cli.github.com/) authenticated once with `gh auth login`.

---

## The loop

```
1. Issue       A labeled issue describes the change (templates enforce structure)
2. Branch      Cut a branch off main, named for the issue
3. Build       Implement; commit with conventional-commit messages
4. PR          Open it: "Closes #<n>", conventional-commit title
   ├─ CI fires:        ruff + format + mypy + pytest   ← HARD gate, blocks merge
   └─ Claude reviews:  posts a summary + inline comments, incl. a docs check
5. Address     Fold in review comments, fix anything CI is unhappy about, push
   └─ repeat 4–5 until CI is green and the review is satisfied
6. Merge       A maintainer squash-merges to main; the branch auto-deletes
7. Release     (separate) tag vX.Y.Z to cut a binary release — see RELEASING.md
```

Testing and the docs check aren't separate end phases — they fold into the PR.
Tests are the automated CI gate; docs are covered by the review prompt and the
PR-template checkbox.

### 1. File an issue

Every change starts with an issue. Use a template from
[**New issue**](https://github.com/obeidahmad/Monay/issues/new/choose):

- **Bug** → labeled `bug`
- **Feature request** → labeled `feature`
- **Task** (chores, CI, refactors, docs) → pick the matching label

Each template asks for structured fields (problem, proposal, acceptance
criteria) — filling them in is what makes a change reviewable. Open-ended
questions and ideas belong in
[**Discussions**](https://github.com/obeidahmad/Monay/discussions), not issues.

The issue's label drives both the branch prefix and the conventional-commit
type below, so set it correctly.

### 2. Branch off `main`

Name the branch from the issue's type and a short slug:

| Issue label | Branch prefix | Commit type |
|---|---|---|
| `feature` | `feat/<n>-slug` | `feat:` |
| `bug` | `fix/<n>-slug` | `fix:` |
| `refactor` | `refactor/<n>-slug` | `refactor:` |
| `perf` | `perf/<n>-slug` | `perf:` |
| `ci` | `ci/<n>-slug` | `ci:` |
| `docs` | `docs/<n>-slug` | `docs:` |

```bash
git switch main && git pull && git switch -c feat/12-history-diff
```

`main` is protected — you can't push to it directly. All changes land through a
PR.

### 3. Build, with the local gate

Before you consider a change done, run exactly what CI will run, so you don't
burn a round-trip:

```bash
uv run ruff check        # lint
uv run ruff format       # auto-formats in place; CI verifies with --check
uv run mypy              # type-check monay/ (strict)
uv run pytest            # the suite
```

Add or update tests for the change — see the testing table in the
[Developer Guide](docs/DEVELOPING.md#8-testing). The keystone is
`tests/test_recompute.py`, which hand-verifies the budget math.

Commit with [conventional-commit](https://www.conventionalcommits.org/) messages
matching the issue type (`feat: …`, `fix: …`).

### 4. Open the PR

The [PR template](.github/pull_request_template.md) guides the body: a short
*what & why*, `Closes #<n>`, how to verify, and a checklist.

**The title is the changelog.** Releases are built with
`gh release create --generate-notes`, which lists each merged PR *by its title*.
So write the PR title as the line a user should read in the release notes, with a
conventional-commit prefix (`feat:`/`fix:`/`refactor:`/`perf:`/`ci:`/`docs:`).

### 5. CI and the review

Two things run automatically on the PR:

- **CI (`ci` workflow) is the hard gate.** It runs ruff lint, ruff
  format-check, mypy (strict), and pytest. Red here blocks merge — treat any
  failure as must-fix. Open a failing job's log to see the actual error.
- **The Claude review is advisory.** It posts a summary comment plus inline
  comments on anything worth a look, and flags whether the change needs docs
  updates. It has **no merge power** — read it critically; if a comment is wrong
  or not worth doing, say so on the thread rather than complying blindly.

Push fixes to the same branch; CI and the review re-run on each push. Reply on
the review threads you addressed (and the ones you intentionally skipped, with a
reason).

### 6. Merge

When CI is green and the review is satisfied, a maintainer **squash-merges** to
`main` (the only merge type enabled) and the branch auto-deletes. Squash-merge
keeps one tidy, conventional-titled commit per PR on `main` — which is what the
release notes are built from.

---

## Using Claude Code (optional accelerator)

Monay is developed with [Claude Code](https://claude.com/claude-code) in the
loop, and the repo ships two project commands in `.claude/commands/` that anyone
with Claude Code gets automatically. They're a convenience over the same manual
steps above — you never *need* them.

- **`/issue <n>`** — reads issue #`<n>` and its comments, proposes a plan, and
  **stops for your approval** before writing any code; then it cuts the branch
  and implements.
- **`/pr <n>`** — pulls the PR's review comments and CI status, sorts must-fix
  from advisory, makes the fixes, runs the local gate, and pushes.

There are two distinct "Claudes" worth keeping straight:

| | **Claude Code** (local CLI) | **Claude review** (GitHub Action) |
|---|---|---|
| Runs | On your machine, interactively | In CI, in the cloud |
| Triggered by | You, via the commands above | Opening/updating a PR |
| Role | **Author** — writes code, opens PRs | **Reviewer** — comments, advisory |

You can also mention `@claude` in an issue or PR comment to ask the GitHub-side
Claude to take a look.

---

## Ground rules, briefly

- **uv only** — never global `pip`. `uv add` / `uv run` / `uv sync`.
- **Fix lint findings, don't suppress them** — prefer a rename or refactor over
  an ignore rule.
- **Keep `domain/` pure** — no SQLAlchemy, no Textual, no I/O; dependencies point
  inward (see the architecture section of the
  [Developer Guide](docs/DEVELOPING.md#1-architecture-at-a-glance)).
- **A bot never gates merge.** CI is mechanical; the review is advice; a human
  approves and merges.
