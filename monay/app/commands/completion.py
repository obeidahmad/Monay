"""Registry-driven completion for the command bar (docs/DEVELOPING.md).

Given the text typed so far, produce the ordered completions for the *trailing
token*: verbs, then subverbs, then in-context section/field/pocket names, then a
choice argument's fixed options. The logic mirrors the parser (``parser.parse`` /
``_bind``) — the same two-token-path preference, the same ``dN`` day pull-out,
the same argument order — so suggestions can never drift from what executes.

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


@dataclass(frozen=True)
class CompletionNames:
    """The in-context names autocomplete can offer, most-relevant first."""

    sections: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    pockets: tuple[str, ...] = ()


def complete(registry: CommandRegistry, names: CompletionNames, text: str) -> list[str]:
    """Ordered completions of ``text`` (each one extends it), best first.

    Returns an empty list when nothing sensible can be completed: empty input, a
    free-text/amount/number argument, or an unparseable or quoted trailing token.
    """
    if not text.strip():
        return []

    # Split off the trailing token being completed, keeping the raw head text
    # (its spacing/quotes) so each suggestion literally extends what's on screen.
    head_text, partial = _split_trailing(text)
    if "'" in partial or '"' in partial:
        return []  # quoted-name completion is out of scope here
    try:
        head_tokens = shlex.split(head_text)
    except ValueError:
        return []

    low = partial.casefold()
    return [
        head_text + cand
        for cand in _candidates(registry, names, head_tokens, partial)
        if cand.casefold().startswith(low) and cand.casefold() != low
    ]


def _split_trailing(text: str) -> tuple[str, str]:
    """``("section ", "")`` for a trailing space, else ``("section ", "ad")``."""
    if text.endswith(" "):
        return text, ""
    head, sep, partial = text.rpartition(" ")
    return head + sep, partial  # head_text is "" when completing the verb


def _candidates(
    registry: CommandRegistry,
    names: CompletionNames,
    head_tokens: list[str],
    partial: str,
) -> list[str]:
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
        low = partial.casefold()
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
