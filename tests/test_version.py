"""The version is derived from the git tag by hatch-vcs (see docs/RELEASING.md);
there is no hand-maintained version string. This guards that a build actually
populated monay/_version.py rather than falling back to the un-built sentinel.
"""

import re

import monay


def test_version_is_populated_from_vcs():
    # A release looks like "1.0.2"; a between-tags dev build looks like
    # "1.0.2.dev3+g<hash>". Either is fine — what must never ship is the
    # fallback from a checkout that was never built.
    assert monay.__version__ != "0.0.0+unknown", (
        "monay/_version.py is missing — run `uv sync` to let hatch-vcs generate it"
    )
    assert re.match(r"^\d+\.\d+", monay.__version__), monay.__version__
