# Monay — Releasing

How to cut a release. (Code layout lives in the [Developer Guide](DEVELOPING.md);
the build/release automation is `.github/workflows/build.yml`.)

---

## The model in one line

**Committing to main is continuous; releasing is deliberate.** A release is a
specific commit you decide is worth shipping, marked with a permanent version
**tag** (`vX.Y.Z`). Pushing that tag — and *only* that — builds the binaries and
publishes a GitHub Release. Pushing to main on its own releases nothing.

So you don't "release on every push." You release when you choose to, by tagging.
The tag is also the *only* place the version lives — see
[Where the version comes from](#where-the-version-comes-from).

## Picking the version number

Monay uses [semantic versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

| Bump | When | Example |
|------|------|---------|
| **PATCH** | Bug fixes only, no behaviour change for users | `1.0.1 → 1.0.2` |
| **MINOR** | New feature, backwards-compatible | `1.0.1 → 1.1.0` |
| **MAJOR** | Breaking change (data format, removed commands, …) | `1.0.1 → 2.0.0` |

## Steps

### 1. Make sure main is ready

Everything you want in the release must already be merged/pushed to `main`. The
release workflow refuses to build a tag whose commit isn't part of main's
history (see [How the guard works](#why-the-tag-has-to-be-on-main)).

```bash
git checkout main
git pull
```

### 2. Tag the release and push the tag

There is **no version file to edit** — the tag *is* the version. Pick the number
with semver (table above), tag the current commit on `main`, and push the tag:

```bash
git tag vX.Y.Z          # label main's current commit
git push origin vX.Y.Z  # push the TAG (not main) — this is what publishes
```

You push the *tag*, not `main` — `main` is already up to date. hatch-vcs reads
`vX.Y.Z` during the build and bakes the version `X.Y.Z` into the binaries.

### 3. Watch it build

GitHub Actions builds the Linux + Windows (x86_64 + arm64) binaries and
publishes a **Monay vX.Y.Z** release with all the assets attached. Check the
**Actions** tab; the result appears under **Releases**.
Every release stays forever — older versions are never lost.

The release notes are **generated automatically** (`gh release create
--generate-notes`): GitHub lists every pull request merged since the previous
tag as the "What's Changed" section, with a full-changelog compare link. The
bullets come from **PR titles**, so write the PR title as the line you want a
user to read — that *is* the changelog entry. (Commits pushed straight to main
without a PR fall back to their commit message.)

## Where the version comes from

There is no hand-maintained version string anywhere in the repo. At build time
[hatch-vcs](https://github.com/ofek/hatch-vcs) runs `git describe`, turns the
tag (`v1.2.0`) into a version (`1.2.0`), and writes `monay/_version.py`
(gitignored). `monay/__init__.py` imports it, so `monay.__version__` — and the
version baked into the PyInstaller binary — is always exactly the tag.

Two consequences worth knowing:

- **Between releases**, a local/dev build reports a *development* version like
  `1.2.1.dev3+g1a2b3c4` (next version, commits since the tag, the commit hash,
  and a dirty-tree marker). That's expected — only a clean checkout sitting
  exactly on a tag produces a bare `1.2.0`.
- **To change the version, you make a tag.** There is nothing else to edit.

## Why the tag has to be on main

A git tag is its own ref; it isn't "on" a branch. To stop a stray tag (say, one
left on an abandoned feature branch) from cutting a release, the `guard` job
checks that the tagged commit is reachable from `origin/main`
(`git merge-base --is-ancestor`). If it isn't, the build is skipped — the run
goes green with a notice and nothing is published. So make sure the commit is on
`main` before you tag it.

## Fixing a botched release

Tags are meant to be permanent, but if you tagged the wrong commit or a build
was broken, you can delete and redo **before** anyone has pulled it:

```bash
git push origin :vX.Y.Z      # delete the remote tag
git tag -d vX.Y.Z            # delete the local tag
gh release delete vX.Y.Z     # delete the GitHub Release (if it was created)
```

Then fix the problem and tag again. If people may already have the release,
don't reuse the number — ship the fix as the next PATCH instead.

## Manual builds (no release)

Running the workflow by hand from the **Actions** tab (`workflow_dispatch`)
builds and smoke-tests the binaries without publishing anything — handy for
checking a build still works without committing to a release.
