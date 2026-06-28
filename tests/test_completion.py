"""Registry-driven command-bar completion: verbs, subverbs, names, choices."""

from monay.app.commands.completion import CompletionNames, complete
from monay.app.commands.specs import build_registry

REGISTRY = build_registry()
NAMES = CompletionNames(
    sections=("Needs", "Wants"),
    fields=("Food", "Rent"),
    pockets=("Main", "Savings"),
)


def comp(text: str) -> list[str]:
    return complete(REGISTRY, NAMES, text)


def test_empty_and_whitespace_have_no_completion():
    assert comp("") == []
    assert comp("   ") == []


def test_completes_a_verb():
    assert comp("prof") == ["profile"]


def test_exact_verb_has_no_completion():
    # a fully-typed token suggests nothing (the `cand != low` filter)
    assert comp("profile") == []


def test_verb_prefix_lists_all_matches_in_order():
    assert comp("p") == ["pocket", "profile"]


def test_subverbs_are_offered_for_cycling():
    assert comp("section ") == [
        "section add",
        "section del",
        "section order",
        "section set",
    ]


def test_subverb_filtered_by_partial():
    assert comp("section a") == ["section add"]


def test_choice_argument_values_keep_declared_order():
    assert comp("section add ") == [
        "section add tax",
        "section add pre",
        "section add post",
    ]


def test_section_name_argument():
    assert comp("section set ") == ["section set Needs", "section set Wants"]


def test_field_name_argument():
    assert comp("add ") == ["add Food", "add Rent"]


def test_field_name_filtered_by_partial():
    assert comp("add Fo") == ["add Food"]


def test_pocket_name_argument():
    assert comp("pocket main ") == ["pocket main Main", "pocket main Savings"]


def test_no_completion_for_amount_or_free_text():
    assert comp("add Food ") == []  # the amount argument
    assert comp("income add ") == []  # a free WORD name


def test_day_token_is_ignored_when_indexing_args():
    # a dN before the field still leaves the field slot to complete (and the
    # suggestion keeps the typed day token, extending what's on screen)
    assert comp("add d5 ") == ["add d5 Food", "add d5 Rent"]
    # after the field + a dN, the next positional is the amount → no names
    assert comp("add Food d5 ") == []


def test_quoted_partial_is_skipped():
    assert comp('field add Needs "Em') == []


def test_tx_offers_subverbs_then_falls_back_to_free_filter():
    assert comp("tx ") == ["tx del", "tx edit"]
    assert comp("tx z") == []  # no subverb matches; the filter is free text
