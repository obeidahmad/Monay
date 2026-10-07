"""``BudgetingService`` pieces that are easier to pin down without HTTP: the
revision hash and the undo journal. No database."""

from monay.app.budgeting import UndoJournal, month_revision
from tests.fixtures.sample_budget import build_sample


def _sample():
    month = build_sample()
    month.recompute()
    return month


def test_revision_is_stable_and_ignores_computed_values():
    a, b = _sample(), _sample()
    assert month_revision(a) == month_revision(b)
    b.sections[0].rest = b.sections[0].rest + b.sections[0].rest  # computed only
    assert month_revision(a) == month_revision(b)


def test_revision_changes_with_anything_the_user_can_change():
    base = month_revision(_sample())
    renamed = _sample()
    renamed.rename_field("Needs", "Groceries", "Food")
    recoloured = _sample()
    recoloured.edit_section("Needs", color=6)
    spent = _sample()
    spent.add_transaction("Wants", "Clothes", 9, "1")
    revisions = {month_revision(m) for m in (renamed, recoloured, spent)}
    assert base not in revisions
    assert len(revisions) == 3


def test_revision_follows_display_order_not_list_order():
    a, b = _sample(), _sample()
    b.sections.reverse()  # same positions, different list order
    assert month_revision(a) == month_revision(b)


def test_undo_token_works_once():
    journal = UndoJournal()
    token = journal.remember(_sample(), "rev")
    assert journal.claim(token) is not None
    assert journal.claim(token) is None
    assert journal.claim("no-such-token") is None


def test_undo_entries_expire():
    now = [0.0]
    journal = UndoJournal(ttl_seconds=120, now=lambda: now[0])
    token = journal.remember(_sample(), "rev")
    now[0] = 119.0
    fresh = journal.remember(_sample(), "rev")
    now[0] = 121.0
    assert journal.claim(token) is None  # past its two minutes
    assert journal.claim(fresh) is not None


def test_undo_journal_is_bounded():
    journal = UndoJournal(capacity=2)
    first, second, third = (journal.remember(_sample(), "rev") for _ in range(3))
    assert journal.claim(first) is None  # the oldest made room
    assert journal.claim(second) is not None
    assert journal.claim(third) is not None
