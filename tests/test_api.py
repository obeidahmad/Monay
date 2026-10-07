"""The HTTP API, end to end: real routes, real engine, real SQLite (in memory).

Each test drives the API the way the web app does — reading a month, sending its
``revision`` back with every change — and checks what comes out. The budget
built here is the sample from ``tests/fixtures/sample_budget.py``, so the
figures are the ones ``test_recompute.py`` verifies by hand.
"""

from datetime import date

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from monay.api.app import create_app
from monay.bootstrap import build_container
from tests.fakes import FixedClock


class Api:
    """A test client that keeps track of the month it is working on."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.path = ""
        self.month: dict = {}
        self.undo_token: str | None = None

    def call(self, method, path, body=None, rev=None, expect=200):
        headers = {} if rev is None else {"If-Match": f'"{rev}"'}
        res = self.client.request(method, path, json=body, headers=headers)
        assert res.status_code == expect, (method, path, res.status_code, res.text)
        return res.json() if res.content else None

    def open(self, profile_id, key):
        self.path = f"/api/profiles/{profile_id}/months/{key}"
        self.month = self.call("GET", self.path)
        return self.month

    def change(self, method, sub, body=None, expect=200):
        out = self.call(
            method, self.path + sub, body, rev=self.month["revision"], expect=expect
        )
        if expect == 200:
            self.month, self.undo_token = out["month"], out["undo_token"]
        return out

    def section(self, name):
        return next(s for s in self.month["sections"] if s["name"] == name)

    def field(self, section, name):
        return next(f for f in self.section(section)["fields"] if f["name"] == name)

    def ref(self, section, name):
        return {
            "section": self.section(section)["index"],
            "field": self.field(section, name)["index"],
        }

    def pocket(self, name):
        return next(p for p in self.month["pockets"] if p["name"] == name)


@pytest.fixture
def api():
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2025, 1, 15))))
    with TestClient(create_app(container)) as client:
        yield Api(client)


@pytest.fixture
def budget(api):
    """The sample budget, built through the API. Returns the profile id."""
    profile = api.call("POST", "/api/profiles", {"name": "Demo"}, expect=201)
    api.open(profile["id"], "2025-01")
    api.change("POST", "/incomes", {"name": "Salary", "amount": "1500+500"})
    for name, kind, alloc, routing in (
        ("Bills", "pre", {"type": "amount", "value": "500"}, "self"),
        ("Needs", "post", {"type": "percent", "value": "50"}, "income"),
        ("Wants", "post", {"type": "percent", "value": "30%"}, "income"),
        ("Savings", "post", {"type": "percent", "value": "20"}, "self"),
    ):
        api.change(
            "POST",
            "/sections",
            {
                "name": name,
                "kind": kind,
                "allocation": alloc,
                "rest_routing": {"kind": routing},
            },
        )
    api.change("POST", "/pockets", {"name": "Bank"})
    api.change("POST", "/pockets", {"name": "Broker"})
    for section, name, amount, current, cap, pocket in (
        ("Bills", "Utilities", "500", "0", None, None),
        ("Needs", "Groceries", "300", "100", "400", None),
        ("Needs", "Transport", "50", "50", "50", None),
        ("Needs", "Dining", "100", "0", None, None),
        ("Wants", "Clothes", "150", "0", None, None),
        ("Wants", "Gadgets", "0", "200", None, None),
        ("Savings", "Emergency", "100", "1000", "5000", "Bank"),
        ("Savings", "Investments", "140", "500", None, "Broker"),
    ):
        body = {
            "name": name,
            "budget": {"type": "amount", "value": amount},
            "current": current,
            "max": cap,
        }
        if pocket:
            body["pocket"] = api.pocket(pocket)["index"]
        api.change("POST", f"/sections/{api.section(section)['index']}/fields", body)
    for day, section, name, amount in (
        (3, "Bills", "Utilities", "450"),
        (5, "Needs", "Groceries", "30"),
        (6, "Needs", "Groceries", "10+10"),
        (8, "Needs", "Dining", "250"),
    ):
        api.change(
            "POST",
            "/transactions",
            {"field": api.ref(section, name), "amount": amount, "day": day},
        )
    return profile["id"]


# --- profiles ----------------------------------------------------------------
def test_health(api):
    assert api.call("GET", "/api/health")["status"] == "ok"


def test_create_profile_seeds_first_month_and_main_pocket(api):
    profile = api.call("POST", "/api/profiles", {"name": "  Demo  "}, expect=201)
    assert (profile["name"], profile["open_month"]) == ("Demo", "2025-01")
    month = api.open(profile["id"], "2025-01")
    assert (month["label"], month["state"], month["is_first"]) == (
        "January 2025",
        "open",
        True,
    )
    assert [(p["name"], p["is_default"]) for p in month["pockets"]] == [("Main", True)]


def test_profile_name_rules(api):
    api.call("POST", "/api/profiles", {"name": "Demo"}, expect=201)
    dup = api.call("POST", "/api/profiles", {"name": "Demo"}, expect=409)
    assert (dup["code"], dup["field"]) == ("duplicate_name", "name")
    blank = api.call("POST", "/api/profiles", {"name": "   "}, expect=422)
    assert (blank["code"], blank["field"]) == ("invalid_request", "name")
    api.call("POST", "/api/profiles", {"name": "X", "nope": 1}, expect=422)


def test_rename_and_delete_profile(api):
    a = api.call("POST", "/api/profiles", {"name": "A"}, expect=201)
    b = api.call("POST", "/api/profiles", {"name": "B"}, expect=201)
    taken = api.call("PATCH", f"/api/profiles/{b['id']}", {"name": "A"}, expect=409)
    assert taken["field"] == "name"
    assert api.call("PATCH", f"/api/profiles/{a['id']}", {"name": "A"})["name"] == "A"
    api.call("DELETE", f"/api/profiles/{b['id']}", expect=204)
    api.call("DELETE", f"/api/profiles/{b['id']}", expect=404)
    api.call("GET", f"/api/profiles/{b['id']}/months", expect=404)


# --- the engine's numbers, over the wire --------------------------------------
def test_sample_budget_matches_the_hand_verified_numbers(api, budget):
    left = {
        ("Bills", "Utilities"): "50.0000",
        ("Needs", "Groceries"): "350.0000",
        ("Needs", "Transport"): "50.0000",
        ("Needs", "Dining"): "-150.0000",
        ("Wants", "Clothes"): "150.0000",
        ("Wants", "Gadgets"): "200.0000",
        ("Savings", "Emergency"): "1100.0000",
        ("Savings", "Investments"): "640.0000",
    }
    for (section, name), expected in left.items():
        assert api.field(section, name)["left"] == expected, (section, name)
    for name, avail, rest in (
        ("Bills", "500.0000", "0.0000"),
        ("Needs", "750.0000", "350.0000"),
        ("Wants", "450.0000", "300.0000"),
        ("Savings", "300.0000", "60.0000"),
    ):
        assert (api.section(name)["available"], api.section(name)["rest"]) == (
            avail,
            rest,
        )
    month = api.month
    assert month["total_income"] == "2000.0000"
    assert month["post_pool"] == "1500.0000"
    assert month["post_pct_total"] == "100"
    assert month["spent"] == "750.0000"
    assert api.pocket("Main")["counter"] == "1360.0000"  # 650 fields + 710 rests
    assert api.pocket("Main")["rests"] == "710.0000"
    assert api.pocket("Bank")["counter"] == "1100.0000"
    assert month["transactions"][2]["expression"] == "10+10"
    # what a change returns is exactly what a fresh read returns
    assert api.call("GET", api.path) == month


def test_history_summarises_each_month_with_spend_by_section(api, budget):
    (summary,) = api.call("GET", f"/api/profiles/{budget}/months")
    assert (summary["key"], summary["state"]) == ("2025-01", "open")
    assert (summary["income"], summary["spent"], summary["leftovers"]) == (
        "2000.0000",
        "750.0000",
        "650.0000",
    )
    assert [(s["name"], s["spent"]) for s in summary["sections"]] == [
        ("Bills", "450.0000"),
        ("Needs", "300.0000"),
        ("Wants", "0.0000"),
        ("Savings", "0.0000"),
    ]


# --- optimistic concurrency ---------------------------------------------------
def test_a_change_needs_the_current_revision(api, budget):
    body = {"name": "Bonus", "amount": "1"}
    missing = api.call("POST", api.path + "/incomes", body, expect=422)
    assert missing["field"] == "if-match"
    stale = api.call("POST", api.path + "/incomes", body, rev="0000", expect=412)
    assert stale["code"] == "stale_revision"
    assert api.call("GET", api.path)["revision"] == api.month["revision"]


def test_refused_requests_save_nothing(api, budget):
    before = api.month["revision"]
    dining = api.ref("Needs", "Dining")
    for body, field in (
        ({"field": dining, "amount": "12,50", "day": 9}, "amount"),
        ({"field": dining, "amount": "0", "day": 9}, "amount"),
        ({"field": dining, "amount": "1/0", "day": 9}, "amount"),
        ({"field": dining, "amount": "9e999999", "day": 9}, "amount"),
        ({"field": dining, "amount": "5", "day": 32}, "day"),
    ):
        assert api.change("POST", "/transactions", body, expect=422)["field"] == field
    gone = {"field": {"section": 9, "field": 0}, "amount": "5", "day": 9}
    assert api.change("POST", "/transactions", gone, expect=404)["code"] == "not_found"
    assert api.call("GET", api.path)["revision"] == before


# --- transactions, undo -------------------------------------------------------
def test_edit_and_move_a_transaction(api, budget):
    before = api.month["revision"]
    api.change("PATCH", "/transactions/2", {"amount": "35"})
    assert api.field("Needs", "Groceries")["paid"] == "55.0000"
    api.change("PATCH", "/transactions/2", {"field": api.ref("Wants", "Clothes")})
    assert api.field("Needs", "Groceries")["paid"] == "20.0000"
    assert api.field("Wants", "Clothes")["paid"] == "35.0000"
    assert api.month["transactions"][1]["field"]["field"] == "Clothes"  # keeps its #
    api.change(
        "PATCH",
        "/transactions/2",
        {"field": api.ref("Needs", "Groceries"), "amount": "30"},
    )
    assert api.month["revision"] == before  # same content, same revision


def test_delete_can_be_undone_exactly_once(api, budget):
    before = api.month
    api.change("DELETE", "/transactions/2")
    assert len(api.month["transactions"]) == 3
    token = api.undo_token
    assert token
    undone = api.call("POST", api.path + "/undo", {"token": token})
    assert undone["month"] == before
    again = api.call("POST", api.path + "/undo", {"token": token}, expect=409)
    assert again["code"] == "undo_unavailable"


def test_undo_is_refused_once_the_month_has_moved_on(api, budget):
    api.change("DELETE", "/transactions/4")
    token = api.undo_token
    api.change(
        "POST",
        "/transactions",
        {"field": api.ref("Wants", "Clothes"), "amount": "1", "day": 9},
    )
    late = api.call("POST", api.path + "/undo", {"token": token}, expect=409)
    assert late["code"] == "undo_unavailable"


# --- transfers ----------------------------------------------------------------
def test_transfer_moves_left_but_never_past_a_max(api, budget):
    move = {
        "from_field": api.ref("Wants", "Gadgets"),
        "to_field": api.ref("Needs", "Groceries"),
        "amount": "100",
        "day": 10,
    }
    over = api.change("POST", "/transfers", move, expect=422)
    assert (over["code"], over["field"]) == ("cap_exceeded", "amount")
    same = api.change(
        "POST", "/transfers", {**move, "to_field": move["from_field"]}, expect=422
    )
    assert same["field"] == "to_field"
    api.change("POST", "/transfers", {**move, "amount": "50"})
    assert api.field("Wants", "Gadgets")["left"] == "150.0000"
    assert api.field("Needs", "Groceries")["left"] == "400.0000"
    assert api.section("Needs")["rest"] == "350.0000"  # REST untouched
    api.change("DELETE", "/transfers/1")
    assert api.month["transfers"] == []
    assert api.undo_token


# --- fields --------------------------------------------------------------------
def test_field_update_distinguishes_absent_from_null_max(api, budget):
    needs = api.section("Needs")["index"]
    path = f"/sections/{needs}/fields/{api.field('Needs', 'Groceries')['index']}"
    api.change("PATCH", path, {"max": None})
    assert api.field("Needs", "Groceries")["max"] is None
    api.change("PATCH", path, {"budget": {"type": "amount", "value": "300"}})
    assert api.field("Needs", "Groceries")["max"] is None  # absent = unchanged
    bank = api.pocket("Bank")["index"]
    api.change("PATCH", path, {"max": "400", "name": "Food", "pocket": bank})
    food = api.field("Needs", "Food")
    assert (food["max"], food["pocket"]) == ("400.0000", "Bank")
    assert api.change("PATCH", path, {"name": "Dining"}, expect=409)["field"] == "name"
    assert api.change("PATCH", path, {"max": "-1"}, expect=422)["field"] == "max"


def test_percentage_budget_and_deleting_only_empty_fields(api, budget):
    savings = api.section("Savings")["index"]
    api.change(
        "POST",
        f"/sections/{savings}/fields",
        {"name": "Extra", "budget": {"type": "percent", "value": "50"}},
    )
    extra = api.field("Savings", "Extra")
    assert (extra["budget_pct"], extra["budget"]) == ("50", "30.0000")
    assert extra["pocket"] == "Main"  # the default pocket
    path = f"/sections/{savings}/fields/{extra['index']}"
    assert api.change("DELETE", path, expect=409)["code"] == "field_not_empty"
    api.change("PATCH", path, {"budget": {"type": "amount", "value": "0"}})
    api.change("DELETE", path)
    assert [f["name"] for f in api.section("Savings")["fields"]] == [
        "Emergency",
        "Investments",
    ]


def test_current_can_only_be_set_in_the_first_month(api, budget):
    feb = api.call("POST", api.path + "/close", rev=api.month["revision"])
    assert (feb["key"], feb["is_first"]) == ("2025-02", False)
    api.open(budget, "2025-02")
    needs = api.section("Needs")["index"]
    refused = api.change(
        "PATCH", f"/sections/{needs}/fields/0", {"current": "5"}, expect=422
    )
    assert "first month" in refused["message"]


# --- sections ------------------------------------------------------------------
def test_section_rules_name_the_input_at_fault(api, budget):
    post_amount = {
        "name": "Bad",
        "kind": "post",
        "allocation": {"type": "amount", "value": "5"},
    }
    assert (
        api.change("POST", "/sections", post_amount, expect=422)["field"]
        == "allocation"
    )
    pre = {"kind": "pre", "allocation": {"type": "amount", "value": "5"}}
    reserved = api.change("POST", "/sections", {**pre, "name": "income"}, expect=422)
    assert reserved["code"] == "invalid"
    dup = api.change("POST", "/sections", {**pre, "name": "Needs"}, expect=409)
    assert (dup["code"], dup["field"]) == ("duplicate_name", "name")
    out_of_range = {
        "name": "Pct",
        "kind": "pre",
        "allocation": {"type": "percent", "value": "150"},
    }
    assert (
        api.change("POST", "/sections", out_of_range, expect=422)["field"]
        == "allocation"
    )


def test_section_colour_and_icon(api, budget):
    # Not chosen: the colour follows the section's position, and there is no icon.
    assert [(s["color"], s["icon"]) for s in api.month["sections"]] == [
        (1, None),
        (2, None),
        (3, None),
        (4, None),
    ]
    wants = api.section("Wants")["index"]
    api.change("PATCH", f"/sections/{wants}", {"color": 7, "icon": "gamepad"})
    assert (api.section("Wants")["color"], api.section("Wants")["icon"]) == (
        7,
        "gamepad",
    )
    api.change("PATCH", f"/sections/{wants}", {"icon": ""})  # "" removes it
    assert api.section("Wants")["icon"] is None
    assert api.change("PATCH", f"/sections/{wants}", {"color": 9}, expect=422)
    # ...and both survive closing the month
    api.change("PATCH", f"/sections/{wants}", {"icon": "gift"})
    feb = api.call("POST", api.path + "/close", rev=api.month["revision"])
    carried = next(s for s in feb["sections"] if s["name"] == "Wants")
    assert (carried["color"], carried["icon"]) == (7, "gift")


def test_rename_keeps_routing_and_reorder_keeps_the_maths(api, budget):
    wants, savings = api.section("Wants")["index"], api.section("Savings")["index"]
    api.change(
        "PATCH",
        f"/sections/{wants}",
        {"rest_routing": {"kind": "section", "target": "Savings"}},
    )
    api.change("PATCH", f"/sections/{savings}", {"name": "Save"})
    assert api.section("Wants")["rest_routing"] == {"kind": "section", "target": "Save"}
    no_target = {"rest_routing": {"kind": "section"}}
    assert (
        api.change("PATCH", f"/sections/{wants}", no_target, expect=422)["field"]
        == "rest_routing"
    )

    api.change("PATCH", f"/sections/{api.section('Save')['index']}", {"position": 0})
    assert [s["name"] for s in api.month["sections"]] == [
        "Save",
        "Bills",
        "Needs",
        "Wants",
    ]
    assert [s["index"] for s in api.month["sections"]] == [0, 1, 2, 3]
    assert api.section("Save")["rest"] == "60.0000"
    api.change("PATCH", f"/sections/{api.section('Save')['index']}", {"position": 99})
    assert api.month["sections"][-1]["name"] == "Save"  # clamped to the end
    assert (
        api.change("DELETE", f"/sections/{api.section('Wants')['index']}", expect=409)[
            "code"
        ]
        == "section_not_empty"
    )


# --- income and pockets --------------------------------------------------------
def test_income_edit_delete_undo(api, budget):
    api.change("POST", "/incomes", {"name": "Bonus", "amount": "100"})
    api.change("PATCH", "/incomes/1", {"name": "Gift", "amount": "50"})
    assert [(i["name"], i["amount"]) for i in api.month["incomes"]] == [
        ("Salary", "2000.0000"),
        ("Gift", "50.0000"),
    ]
    api.change("DELETE", "/incomes/1")
    undone = api.call("POST", api.path + "/undo", {"token": api.undo_token})
    assert len(undone["month"]["incomes"]) == 2


def test_pocket_rules(api, budget):
    bank = api.pocket("Bank")["index"]
    in_use = api.change("DELETE", f"/pockets/{bank}", expect=409)
    assert in_use["code"] == "pocket_in_use"
    main = api.pocket("Main")["index"]
    assert api.change("DELETE", f"/pockets/{main}", expect=422)["code"] == "invalid"
    api.change("POST", "/pockets", {"name": "Cash"})
    cash = api.pocket("Cash")["index"]
    api.change("PATCH", f"/pockets/{cash}", {"name": "Wallet", "is_default": True})
    assert api.pocket("Wallet")["is_default"]
    assert api.pocket("Wallet")["counter"] == "710.0000"  # RESTs follow the default


# --- closing --------------------------------------------------------------------
def test_an_unbalanced_month_cannot_be_closed(api, budget):
    needs = api.section("Needs")["index"]
    api.change(
        "PATCH",
        f"/sections/{needs}",
        {"allocation": {"type": "percent", "value": "45"}},
    )
    assert api.month["post_pct_total"] == "95"
    assert api.month["unallocated"] == "75.0000"
    assert api.pocket("Main")["unallocated"] == "75.0000"
    blocked = api.call("GET", api.path + "/close-preview", expect=409)
    assert blocked["code"] == "month_not_balanced"


def test_preview_then_close(api, budget):
    before = api.month["revision"]
    preview = api.call("GET", api.path + "/close-preview")
    assert (preview["next_label"], preview["leftovers"]) == (
        "February 2025",
        "650.0000",
    )
    assert preview["carries"] == [{"section": "Savings", "amount": "60.0000"}]
    assert api.call("GET", api.path)["revision"] == before  # a preview changes nothing

    api.call("POST", api.path + "/close", rev="0000", expect=412)
    feb = api.call("POST", api.path + "/close", rev=before)
    assert (feb["key"], feb["state"]) == ("2025-02", "open")
    assert [(i["name"], i["amount"], i["kind"]) for i in feb["incomes"]] == [
        ("January 2025 Leftovers", "650.0000", "leftover")
    ]
    current = {
        (s["name"], f["name"]): f["current"]
        for s in feb["sections"]
        for f in s["fields"]
    }
    assert current[("Needs", "Dining")] == "-150.0000"
    assert next(s for s in feb["sections"] if s["name"] == "Savings")[
        "carried_rest"
    ] == ("60.0000")

    api.open(budget, "2025-01")
    assert api.month["state"] == "closed"
    late = api.change("POST", "/incomes", {"name": "Late", "amount": "1"}, expect=409)
    assert late["code"] == "month_closed"
    months = api.call("GET", f"/api/profiles/{budget}/months")
    assert [(m["key"], m["state"]) for m in months] == [
        ("2025-02", "open"),
        ("2025-01", "closed"),
    ]


def test_unknown_and_malformed_months(api, budget):
    api.call("GET", f"/api/profiles/{budget}/months/2031-01", expect=404)
    api.call("GET", f"/api/profiles/{budget}/months/2031-13", expect=422)
