"""Registry-driven completion for the command bar (docs/DEVELOPING.md).

Given the text typed so far, produce the ordered completions for the *trailing
token*: verbs, then subverbs, then in-context section/field/pocket names, then a
choice argument's fixed options. The logic mirrors the parser (``parser.parse`` /
``_bind``) — the same two-token-path preference, the same ``dN`` day pull-out,
the same argument order — so suggestions can never drift from what executes.

Suggestions come back in their final parseable form: a name that ``shlex``
would split or choke on (spaces, quotes, backslashes) is emitted double-quoted,
so an accepted completion always executes. Typing inside an open quote
completes too, closing the quote for you.

Everything here is pure (no Textual, no I/O): the caller passes in the current
names, and the TUI renders the result as ghost text and cycles it on Tab.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from .registry import (
    CHOICE,
    DAY,
    FIELD,
    POCKET,
    SECTION,
    CommandRegistry,
    CommandSpec,
)

_DAY_RE = re.compile(r"^d(\d+)$", re.IGNORECASE)
_NEEDS_QUOTES = re.compile(r"""[\s"'\\]""")


def _quoted(cand: str) -> str:
    """A candidate as it must be typed: quoted when shlex would split/choke on it."""
    if not _NEEDS_QUOTES.search(cand):
        return cand
    return '"' + cand.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _requoted(cand: str, quote: str) -> str:
    """``cand`` spliced back into its already-open ``quote``, closed.

    Backslash is still an escape char inside shlex double quotes, so it is
    doubled there (matching :func:`_quoted`); single quotes take everything
    literally.
    """
    if quote == '"':
        cand = cand.replace("\\", "\\\\")
    return quote + cand + quote


@dataclass(frozen=True)
class CompletionNames:
    """The in-context names autocomplete can offer, most-relevant first."""

    sections: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    pockets: tuple[str, ...] = ()


def complete(registry: CommandRegistry, names: CompletionNames, text: str) -> list[str]:
    """Ordered full-line completions of ``text``, best first.

    Each result is the whole line as it should read after accepting: names shlex
    would split are auto-quoted, so a suggestion may *replace* an unquoted
    partial rather than extend it (``… Long`` -> ``… "Long-Term Investing"``).
    Returns an empty list when nothing sensible can be completed: empty input, a
    free-text/amount/number argument, or an unparseable trailing token.
    """
    if not text.strip():
        return []

    # Split off the trailing token being completed, keeping the raw head text
    # (its spacing/quotes) so each suggestion builds on what's on screen.
    head_text, partial, open_quote = _split_trailing(text)
    if not open_quote and ("'" in partial or '"' in partial):
        return []  # closed/embedded quote in the trailing token: out of scope
    try:
        head_tokens = shlex.split(head_text)
    except ValueError:
        return []

    low = partial.casefold()
    # _candidates returns the raw candidate set for this position; the prefix
    # filter (and the "nothing to add" exclusion) is applied here, once.
    cands = _candidates(registry, names, head_tokens, low)
    if open_quote:
        # Inside an open quote: complete the name and close the quote. An
        # exactly-typed name still completes — the closing quote is the
        # addition — and names containing the opener itself are skipped.
        return [
            head_text + _requoted(cand, open_quote)
            for cand in cands
            if open_quote not in cand and cand.casefold().startswith(low)
        ]
    return [
        head_text + _quoted(cand)
        for cand in cands
        if cand.casefold().startswith(low) and cand.casefold() != low
    ]


def _split_trailing(text: str) -> tuple[str, str, str]:
    """``(head_text, partial, open_quote)`` for the token being completed.

    ``("section ", "", "")`` for a trailing space, ``("section ", "ad", "")``
    mid-word, and ``("section set ", "Long-Term Inv", '"')`` when the trailing
    token is an unclosed quote (the partial is what's inside it). head_text is
    "" when completing the verb.
    """
    quote = ""
    opened_at = 0
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote, opened_at = ch, i
    if quote:
        return text[:opened_at], text[opened_at + 1 :], quote
    if text.endswith(" "):
        return text, "", ""
    head, sep, partial = text.rpartition(" ")
    return head + sep, partial, ""


def _candidates(
    registry: CommandRegistry,
    names: CompletionNames,
    head_tokens: list[str],
    low: str,
) -> list[str]:
    # Returns the raw candidate set for the current position; complete() filters
    # it by prefix. The subverb branch is the one exception — it uses a pass/fail
    # gate on ``low`` to decide whether to offer subverbs at all, or fall through
    # to argument completion of a one-token form (e.g. `tx <filter>`).
    if not head_tokens:
        return registry.verbs()  # completing the verb itself

    verb = head_tokens[0].lower()
    if len(head_tokens) == 1:
        subverbs = sorted(
            {
                s.path[1]
                for s in registry.specs()
                if len(s.path) == 2 and s.path[0] == verb
            }
        )
        if subverbs and (
            not low or any(sv.casefold().startswith(low) for sv in subverbs)
        ):
            return subverbs
        # else fall through to argument completion of the one-token form, if any

    spec, arg_tokens = _resolve(registry, head_tokens)
    if spec is None:
        return []
    return _arg_candidates(spec, names, arg_tokens)


def _resolve(
    registry: CommandRegistry, head_tokens: list[str]
) -> tuple[CommandSpec | None, list[str]]:
    """The spec for ``head_tokens`` and the arg tokens after its path (parser order)."""
    if len(head_tokens) >= 2:
        spec = registry.find((head_tokens[0].lower(), head_tokens[1].lower()))
        if spec is not None:
            return spec, head_tokens[2:]
    spec = registry.find((head_tokens[0].lower(),))
    if spec is not None:
        return spec, head_tokens[1:]
    return None, []


def _arg_candidates(
    spec: CommandSpec, names: CompletionNames, arg_tokens: list[str]
) -> list[str]:
    non_day = [a for a in spec.args if a.kind != DAY]
    tokens = list(arg_tokens)
    if len(non_day) != len(spec.args):  # spec has a dN day arg: drop the first dN
        for i, tok in enumerate(tokens):
            if _DAY_RE.match(tok):
                del tokens[i]
                break

    index = len(tokens)
    if index >= len(non_day):
        return []
    arg = non_day[index]
    if arg.variadic:
        return []
    if arg.kind == CHOICE:
        return list(arg.choices)
    if arg.kind == SECTION:
        return list(names.sections)
    if arg.kind == FIELD:
        return list(names.fields)
    if arg.kind == POCKET:
        return list(names.pockets)
    return []  # amount / word / text / int / cap / month: nothing to complete
