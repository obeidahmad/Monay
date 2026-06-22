# Review instructions

## Always check: docs are in sync with the code

Treat documentation drift as a review finding. For every PR, verify that ALL
documentation still matches the code's actual behavior, and flag anything stale:

- `README.md` — features, commands, concepts, usage examples, `--help`/command tables
- `docs/` — `DEVELOPING.md`, `RELEASING.md` (behaviour/process docs)
- `CONTRIBUTING.md` — the workflow, commands, and gate description
- docstrings / inline comments on the code being changed

If a change alters user-facing behavior, a command, a flag, an API, or a documented
invariant and the matching docs were not updated, post a finding that names the
specific doc and exactly what is now out of date. Check every doc above, not just
the file that changed.
