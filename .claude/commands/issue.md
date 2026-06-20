---
description: Read a GitHub issue, agree on a plan, then start a branch for it
argument-hint: <issue-number>
---

You are picking up GitHub issue **#$1** to implement in this repo. Work in
phases and **stop for my go-ahead before writing any code** — planning first is
the rule here.

## 1. Read the issue

Run `gh issue view $1 --json number,title,state,labels,body,comments` and read the
full body and every comment. Use the `--json` form, not `--comments`: in a
non-interactive shell the bare `--comments` view prints *only* the comment stream,
so an issue with zero comments returns nothing and you never see the body. The
issue was filed from a template, so it has structured fields (problem, proposal,
acceptance criteria). Note its label — `feature` / `bug` / `refactor` / `perf` /
`ci` / `docs` — you'll need the matching conventional-commit type below.

If anything material is ambiguous, ask me before planning rather than guessing.

## 2. Understand the code

Find and read the parts of the codebase the issue touches. Confirm how the
relevant pieces work today before proposing a change. `docs/DEVELOPING.md` is the
code guide; start there if you need orientation.

## 3. Propose a plan — then stop

Write a short plan: the approach, the files you'll change, the tests you'll add
or update, and anything that needs a decision. Keep it tight. **Do not start
implementing until I approve it.**

## 4. Create the branch (after I approve)

Derive the branch from the issue's conventional-commit type and a short slug:

- `feature` → `feat/$1-<slug>`   · `bug` → `fix/$1-<slug>`
- `refactor` → `refactor/$1-<slug>` · `perf` → `perf/$1-<slug>`
- `ci` → `ci/$1-<slug>`   · `docs` → `docs/$1-<slug>`

Branch off the latest `main`:

```
git switch main && git pull && git switch -c <branch>
```

## 5. Implement

Build it per the approved plan. Use conventional-commit messages that match the
issue type. Run `uv run ruff check`, `uv run ruff format`, and `uv run pytest`
before you consider a change done — that's exactly what the CI gate enforces. Add
or update tests for the change.

When it's ready, open the PR with a conventional title and `Closes #$1` in the
body (the PR template will guide the rest).
