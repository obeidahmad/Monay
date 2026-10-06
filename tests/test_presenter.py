"""The web view models: what the React Budget/Pockets/Transactions tabs show."""

from monay.domain.values import Cap, Percentage, RestRouting
from monay.web.presenter import budget_summary, month_view
from tests.fixtures.sample_budget import build_sample, section


def _sample():
    m = build_sample()
    m.recompute()
    return m


def _section(view, name):
    return next(s for s in view["sections"] if s["name"] == name)


def test_sections_carry_avail_rest_and_balance():
    view = month_view(_sample())
    needs = _section(view, "Needs")
    assert (needs["available"], needs["rest"]) == ("750.00", "350.00")
    assert needs["share_label"] == "post · 50%"
    assert view["summary"]["pct_total"] == "100"
    assert view["summary"]["balanced"] is True


def test_post_pool_subtracts_tax_share():
    m = _sample()  # income 2000, Bills (pre 500), Needs/Wants/Savings (post)
    m.add_section("VAT", "tax", percentage=Percentage(10))  # 10% of 2000 = 200
    view = month_view(m)
    assert _section(view, "VAT")["share_label"] == "tax · 10%"
    assert budget_summary(m)["post_pool"] == "1300.00"  # 2000 − 200 − 500


def test_negative_rest_is_a_negative_string_and_a_warning():
    m = _sample()
    m.set_field_budget("Savings", "Investments", "2000")  # blow past the slice
    view = month_view(m)
    assert _section(view, "Savings")["rest"].startswith("-")
    assert any("Savings" in w for w in view["warnings"])


def test_fields_show_budget_pct_and_infinite_cap():
    m = _sample()  # Needs: AVAILABLE 750, fixed budgets 300 + 50 + 100
    m.add_field("Needs", "Buffer", Percentage(50), Cap.infinite(), "Main")
    fields = {f["name"]: f for f in _section(month_view(m), "Needs")["fields"]}
    assert fields["Buffer"]["budget_pct"] == "50"
    assert fields["Buffer"]["budget"] == "150.00"  # 50% of (750 − 450)
    assert fields["Dining"]["cap"] is None  # ∞
    assert fields["Groceries"]["left"] == "350.00"


def test_rest_routing_labels():
    m = _sample()
    section(m, "Wants").rest_routing = RestRouting.to_section("Bills")
    view = month_view(m)
    assert _section(view, "Needs")["routing_label"] == "→ income"
    assert _section(view, "Savings")["routing_label"] == "→ carries over"
    assert _section(view, "Wants")["routing_label"] == "→ Bills"


def test_pockets_break_down_their_fields_and_default_holds_rests():
    view = month_view(_sample())
    pockets = {p["name"]: p for p in view["pockets"]}
    assert pockets["Main"]["is_default"] and pockets["Main"]["rests"] is not None
    assert pockets["Bank"]["rests"] is None
    assert all(f["left"] for f in pockets["Bank"]["fields"])


def test_section_accents_follow_position():
    view = month_view(_sample())
    assert [s["accent"] for s in view["sections"]] == [0, 1, 2, 3]
