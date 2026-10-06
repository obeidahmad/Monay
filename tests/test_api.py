"""The web API end to end: real SQLite (in memory), a fixed clock, TestClient."""

from datetime import date

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from monay.bootstrap import build_container
from monay.web.api import create_app
from tests.fakes import FixedClock


@pytest.fixture
def client(tmp_path):
    container = build_container("sqlite://")
    container.clock.override(providers.Object(FixedClock(date(2026, 6, 13))))
    # an empty static dir → the "not built" hint page, independent of a build
    return TestClient(create_app(container.app_service(), static_dir=tmp_path))


def post(client, url, body=None):
    r = client.post(url, json=body or {})
    assert r.status_code == 200, r.json()
    return r.json()


def section(state, name):
    return next(s for s in state["month"]["sections"] if s["name"] == name)


def setup_budget(client):
    post(client, "/api/profiles", {"name": "Demo"})
    post(client, "/api/sections", {"kind": "post", "name": "Need", "alloc": "50%"})
    post(client, "/api/sections", {"kind": "post", "name": "Want", "alloc": "30%"})
    post(client, "/api/sections", {"kind": "post", "name": "Save", "alloc": "20%"})
    return post(client, "/api/incomes", {"name": "Pay", "amount": "1000"})


def test_empty_state_has_no_profile(client):
    state = client.get("/api/state").json()
    assert state["profile"] is None and state["month"] is None


def test_full_budget_loop(client):
    state = setup_budget(client)
    assert state["viewing"] == {
        "key": "2026-06",
        "label": "June 2026",
        "closed": False,
        "first_month": True,
    }
    assert state["month"]["summary"]["balanced"] is True

    post(client, "/api/fields", {"section": "Need", "name": "Food", "budget": "300"})
    state = post(
        client,
        "/api/transactions",
        {"section": "Need", "field": "Food", "amount": "15.71+1.35", "day": 2},
    )
    food = section(state, "Need")["fields"][0]
    assert (food["paid"], food["left"], food["cap"]) == ("17.06", "282.94", None)
    assert state["month"]["transactions"][0]["index"] == 1

    state = post(client, "/api/transactions/edit", {"index": 1, "amount": "20"})
    assert section(state, "Need")["fields"][0]["paid"] == "20.00"
    state = post(client, "/api/transactions/delete", {"index": 1})
    assert state["month"]["transactions"] == []


def test_errors_are_400_with_a_message(client):
    setup_budget(client)
    r = client.post(
        "/api/sections", json={"kind": "post", "name": "Bad", "alloc": "300"}
    )
    assert r.status_code == 400
    assert "percentage" in r.json()["detail"]

    r = client.post("/api/incomes", json={"name": "X", "amount": "2**8"})
    assert r.status_code == 400 and r.json()["detail"]


def test_transfer_over_max_reports_what_fits(client):
    setup_budget(client)
    post(client, "/api/fields", {"section": "Save", "name": "A"})
    post(
        client, "/api/fields/edit", {"section": "Save", "field": "A", "current": "100"}
    )
    post(client, "/api/fields", {"section": "Save", "name": "B", "max": "50"})
    post(client, "/api/fields/edit", {"section": "Save", "field": "B", "current": "40"})
    body = {
        "from_section": "Save",
        "from_field": "A",
        "to_section": "Save",
        "to_field": "B",
        "amount": "20",
        "day": 1,
    }
    r = client.post("/api/transfers", json=body)
    assert r.status_code == 400 and r.json()["allowed"] == "10.00"
    state = post(client, "/api/transfers", {**body, "amount": "10"})
    assert state["month"]["transfers"][0]["amount"] == "10.00"


def test_close_preview_close_and_view_history(client):
    setup_budget(client)
    preview = client.get("/api/month/close-preview").json()
    assert preview["next_label"] == "July 2026"
    assert preview["leftovers"] == "1000.00"

    state = post(client, "/api/month/close")
    assert state["viewing"]["key"] == "2026-07"
    assert [h["key"] for h in state["history"]] == ["2026-07", "2026-06"]

    state = post(client, "/api/month/view", {"key": "2026-06"})
    assert state["viewing"]["closed"] is True
    r = client.post("/api/incomes", json={"name": "Late", "amount": "5"})
    assert r.status_code == 400 and "closed" in r.json()["detail"]
    state = post(client, "/api/month/view", {"key": None})
    assert state["viewing"]["key"] == "2026-07"


def test_sections_fields_pockets_edit_and_delete(client):
    setup_budget(client)
    post(client, "/api/pockets", {"name": "Bank"})
    state = post(client, "/api/pockets/edit", {"pocket": "Bank", "main": True})
    assert [p["name"] for p in state["month"]["pockets"] if p["is_default"]] == ["Bank"]
    post(client, "/api/fields", {"section": "Need", "name": "Rent", "budget": "10%"})
    state = post(
        client,
        "/api/fields/edit",
        {"section": "Need", "field": "Rent", "name": "Home", "max": "500"},
    )
    home = section(state, "Need")["fields"][0]
    assert (home["name"], home["budget_pct"], home["cap"]) == ("Home", "10", "500.00")

    state = post(
        client, "/api/sections/edit", {"section": "Need", "rest": "self", "name": "N"}
    )
    assert section(state, "N")["routing_label"] == "→ carries over"
    r = client.post("/api/sections/delete", json={"section": "N"})
    assert r.status_code == 400  # still has a field
    post(client, "/api/fields/edit", {"section": "N", "field": "Home", "budget": "0"})
    post(client, "/api/fields/delete", {"section": "N", "field": "Home"})
    state = post(client, "/api/sections/delete", {"section": "N"})
    assert all(s["name"] != "N" for s in state["month"]["sections"])


def test_profiles(client):
    post(client, "/api/profiles", {"name": "Alice"})
    post(client, "/api/profiles", {"name": "Bob"})
    state = post(client, "/api/profiles/switch", {"name": "Alice"})
    assert state["profile"]["name"] == "Alice"
    state = post(client, "/api/profiles/rename", {"name": "Al"})
    assert sorted(p["name"] for p in state["profiles"]) == ["Al", "Bob"]
    state = post(client, "/api/profiles/delete", {"name": "Al"})
    assert state["profile"]["name"] == "Bob"
    r = client.post("/api/profiles", json={"name": "  "})
    assert r.status_code == 400


def test_evaluate_previews_expressions(client):
    assert post(client, "/api/evaluate", {"expr": "(7.81)/2+6.5"})["value"] == "10.40"
    assert client.post("/api/evaluate", json={"expr": "1/0"}).status_code == 400


def test_serves_hint_page_when_frontend_not_built(client):
    r = client.get("/")
    assert r.status_code == 200 and "npm run build" in r.text


def test_serves_built_frontend_with_spa_fallback(tmp_path):
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    container = build_container("sqlite://")
    client = TestClient(create_app(container.app_service(), static_dir=tmp_path))
    assert "root" in client.get("/").text
    assert "root" in client.get("/budget").text  # client-side route
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/api/nope").status_code == 404
