<!--
Title: use a conventional-commit prefix — feat: / fix: / perf: / refactor: /
ci: / docs:. The squash-merge commit becomes the release-notes line, so write
the title for the changelog.
-->

## What & why

<!-- What does this change, and why? Keep it short; link the issue for detail. -->

Closes #

## How to verify

<!-- The commands or steps a reviewer runs to confirm it works. -->

```
uv run pytest
```

## Checklist

- [ ] Title is a conventional commit (`feat:`/`fix:`/`perf:`/`refactor:`/`ci:`/`docs:`)
- [ ] `uv run ruff check` and `uv run ruff format --check` pass locally
- [ ] Tests added or updated for the change
- [ ] Docs updated if behaviour changed (`docs/`, `README`, `--help`), or N/A