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
gh pr view $1 --json number,title,state,body,comments,reviews
gh api repos/{owner}/{repo}/pulls/$1/comments   # inline review-thread comments
gh pr checks $1
```

Use the `--json` form, not `gh pr view --comments`: the bare `--comments` view
prints nothing in a non-interactive shell when there are no conversation
comments. Note the second call — inline code-review comments (what the Claude
review posts) live on the review *threads*, not in `--json comments`, so fetch
them via `gh api`. `{owner}`/`{repo}` are auto-filled from the current repo.

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