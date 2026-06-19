---
description: Pull a PR's review comments and CI status, address them, and push
argument-hint: <pr-number>
---

You are iterating on **PR #$1** — folding in review feedback and fixing whatever
CI is unhappy about, then pushing. Make sure you're on the PR's branch first
(`gh pr checkout $1` if you aren't).

## 1. Gather the feedback

Run both and read everything:

```
gh pr view $1 --comments
gh pr checks $1
```

- **Review comments** come from the Claude GitHub App and any human reviewer.
  They're advisory — read them critically. If a comment is wrong or not worth
  doing, say so in your reply rather than complying blindly.
- **`gh pr checks`** shows the CI gate (ruff + pytest). Red there is a hard
  blocker on merge; treat those as must-fix.

For any failing check, open its log to see the actual error:

```
gh run view --log-failed --job <job-id>
```

## 2. Sort what to do

List the items you'll address and the ones you'll push back on (with a reason).
If review comments conflict with the issue's intent or each other, flag it and
ask me rather than picking silently.

## 3. Fix, verify, push

Make the changes. Before pushing, reproduce the gate locally so you don't burn a
CI round-trip:

```
uv run ruff check && uv run ruff format --check && uv run pytest
```

Commit with conventional-commit messages, then `git push`. CI re-runs on push.

## 4. Close the loop

Reply to the review threads you addressed (briefly note what you changed) and to
the ones you intentionally skipped (why). Repeat `/pr $1` until CI is green and
the review is satisfied — then it's mine to squash-merge.