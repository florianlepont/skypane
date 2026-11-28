# SPDX-License-Identifier: AGPL-3.0-only
"""POST /airlines/suggest and /airlines/suggest/reject: administrators only, the
prefix re-checked against the live registry, the service reached only through
the injected fake, nothing applied without the resolve route, and the key
never in any output."""
import urllib.parse

import pytest
from fake_anthropic import DUMMY_KEY

from companion.test_airline_suggest_helpers import FakeClient, make_rig, rig_with_gaps
from server.plane import airline_suggest as ais
from server.plane import manual_resolutions


@pytest.fixture
def rig(tmp_path, monkeypatch):
    yield from rig_with_gaps(tmp_path, monkeypatch)


def test_an_administrator_gets_the_row_with_its_suggestion(rig):
    status, answer = rig.suggest("OCN", "2")
    assert status == 200
    assert answer["state"] == "suggested"
    row = answer["html"]
    assert row.startswith('<tbody class="airline-group airline-group--gap"')
    assert '<span class="airlines-gap__name">Oceanair</span>' in row
    assert "#name-prefix-2" in row and "data-suggest" not in row
    assert 'formaction="%s/airlines/suggest/reject"' % rig.frame in row
    assert len(rig.client.bodies) == 1
    sent = rig.client.bodies[0]["messages"][0]["content"]
    assert sent == "Designator: OCN\nSample callsigns: OCN123"
    assert ais.cached(rig.root, "OCN")["name"] == "Oceanair"


def test_the_row_comes_back_in_the_request_language(rig):
    _status, answer = rig.suggest("OCN", "0", lang="fr")
    assert ">Modifier</a>" in answer["html"] and "Utiliser la suggestion Oceanair pour OCN" in answer["html"]
    _status, english = rig.suggest("OCN", "0", lang="en")
    assert ">Edit</a>" in english["html"]


def test_a_second_request_for_the_same_prefix_makes_no_second_call(rig):
    rig.suggest("OCN")
    status, again = rig.suggest("OCN")
    assert status == 200 and again["state"] == "suggested"
    assert len(rig.client.bodies) == 1


def test_a_model_that_does_not_know_gives_the_plain_row(rig):
    rig.client.name = None
    _status, answer = rig.suggest("CMA", "3")
    assert answer["state"] == "none"
    assert "airlines-tag" not in answer["html"] and ">Name it</a>" in answer["html"]
    assert rig.suggest("CMA", "3")[1]["state"] == "none"
    assert len(rig.client.bodies) == 1


def test_a_failing_service_gives_the_plain_row_and_is_not_asked_again_soon(rig):
    rig.client.reply = ais.Reply(529, None, "http_529")
    _status, answer = rig.suggest("OCN")
    assert answer["state"] == "failed"
    assert "airlines-tag" not in answer["html"] and ">Name it</a>" in answer["html"]
    rig.suggest("OCN")
    assert len(rig.client.bodies) == 1


def test_over_the_cap_the_route_answers_busy_without_a_call(rig, monkeypatch):
    monkeypatch.setattr(ais, "HOURLY_CAP", 1)
    assert rig.suggest("OCN")[1]["state"] == "suggested"
    _status, answer = rig.suggest("ITI")
    assert answer["state"] == "busy" and ">Name it</a>" in answer["html"]
    assert len(rig.client.bodies) == 1


def test_with_no_key_the_route_answers_off_without_a_call(tmp_path, monkeypatch):
    off = make_rig(tmp_path, monkeypatch, key=None)
    try:
        off.seed_gaps()
        _status, answer = off.suggest("OCN")
        assert answer["state"] == "off" and ">Name it</a>" in answer["html"]
        assert off.client.bodies == []
        assert not (tmp_path / "state" / ais.CACHE_FILENAME).exists()
    finally:
        off.server.stop()


@pytest.mark.parametrize("prefix, index", [
    ("QQQ", "0"), ("oc", "0"), ("", "0"), ("OCNX", "0"), ("../x", "0"),
    ("OCN", "-1"), ("OCN", "1000"), ("OCN", "x"), ("OCN", ""), ("OCN", "1" * 40)])
def test_a_stale_or_malformed_request_calls_nothing_and_writes_nothing(rig, prefix, index):
    rig.seed_gaps(("OCN",))
    before = rig.files()
    status, answer = rig.suggest(prefix, index)
    assert status == 200 and answer == {"state": "stale", "html": ""}
    assert rig.client.bodies == [] and rig.files() == before


@pytest.mark.parametrize("who, expected", [("owner", 404), ("co", 404), ("anonymous", 303)])
def test_everyone_but_an_administrator_is_refused_and_the_service_is_not_called(rig, who, expected):
    unknown = rig.get(who, "/no-such-page-anywhere")
    for route in ("/airlines/suggest", "/airlines/suggest/reject"):
        status, headers, body = rig.post(who, rig.frame + route, {"prefix": "OCN", "index": "0"})
        assert status == expected
        if expected == 404:
            assert body == unknown[2]
        else:
            assert headers["Location"].startswith("/login")
    assert rig.client.bodies == []
    assert ais.cached(rig.root, "OCN") is None


@pytest.mark.parametrize("route", ("/airlines/suggest", "/airlines/suggest/reject"))
def test_a_missing_or_wrong_token_is_refused(rig, route):
    status, _h, _b = rig.post("admin", rig.frame + route, {"prefix": "OCN", "index": "0"}, csrf=False)
    assert status == 403 and rig.client.bodies == []
    status, _h, _b = rig.post(
        "admin", rig.frame + route, {"prefix": "OCN", "index": "0", "csrf_token": "wrong"}, csrf=False)
    assert status == 403 and rig.client.bodies == []
    assert ais.cached(rig.root, "OCN") is None


def test_removing_a_suggestion_returns_to_name_it_and_is_never_asked_again(rig):
    rig.suggest("OCN")
    status, headers, _b = rig.post("admin", rig.frame + "/airlines/suggest/reject", {"prefix": "OCN"})
    assert status == 303 and urllib.parse.urlsplit(headers["Location"]).path == rig.frame + "/airlines/manage"
    entry = ais.cached(rig.root, "OCN")
    assert entry["state"] == "rejected" and "name" not in entry
    assert "OCN" not in manual_resolutions.load_manual_resolutions(rig.owned_dir)
    page = rig.get("admin", rig.frame + "/airlines/manage")[2]
    assert "Oceanair" not in page and 'data-suggest-prefix="OCN"' not in page
    assert rig.suggest("OCN")[1]["state"] == "none"
    assert len(rig.client.bodies) == 1


def test_naming_with_the_suggested_name_records_accepted_and_with_another_edited(rig):
    rig.suggest("OCN")
    rig.client.name = "Itavia Express"
    rig.suggest("ITI")
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/resolve",
        {"prefix": "OCN", "airline_name": "Oceanair", "inline": "1"})
    assert status == 303 and "flash=manual_resolved" in headers["Location"]
    rig.post("admin", rig.frame + "/airlines/resolve",
             {"prefix": "ITI", "airline_name": "Itavia Express Cargo", "inline": "1"})
    assert ais.cached(rig.root, "OCN")["state"] == "accepted"
    assert ais.cached(rig.root, "ITI")["state"] == "edited"
    names = manual_resolutions.load_manual_resolutions(rig.owned_dir)
    assert names["OCN"]["airline_name"] == "Oceanair"
    assert names["ITI"]["airline_name"] == "Itavia Express Cargo"
    details = {row["target_id"]: row["detail"] for row in rig.audit() if row["action"] == "airline.resolve"}
    assert "accepted" in details["oceanair"] and "edited" in details["itavia-express-cargo"]


def test_naming_by_hand_without_a_suggestion_says_nothing_about_one(rig):
    rig.post("admin", rig.frame + "/airlines/resolve", {"prefix": "ZLN", "airline_name": "Zephyr", "inline": "1"})
    rows = [row for row in rig.audit() if row["action"] == "airline.resolve"]
    assert len(rows) == 1 and "suggest" not in (rows[0]["detail"] or "")
    assert ais.cached(rig.root, "ZLN") is None


@pytest.mark.parametrize("name", ["", "x" * 101, "generic-thing"])
def test_a_refused_name_changes_nothing_in_the_cache(rig, name):
    rig.suggest("OCN")
    before = ais.cached(rig.root, "OCN")
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/resolve", {"prefix": "OCN", "airline_name": name, "inline": "1"})
    assert status == 303 and "flash=manual_resolved" not in headers["Location"]
    assert ais.cached(rig.root, "OCN") == before
    assert "OCN" not in manual_resolutions.load_manual_resolutions(rig.owned_dir)


def test_nothing_is_applied_without_a_person_posting_the_resolve_form(rig):
    rig.suggest("OCN")
    rig.suggest("ITI")
    for path in (rig.frame + "/airlines/manage", "/airlines/manage", "/fleet", "/airlines", "/health"):
        rig.get("admin", path)
    assert manual_resolutions.load_manual_resolutions(rig.owned_dir) == {}
    assert not any(name.endswith("manual_resolutions.json") for name in rig.files())


def test_the_key_never_leaves_the_server(tmp_path, monkeypatch, capsys):
    leaky = FakeClient(error=RuntimeError("401 invalid x-api-key %s" % DUMMY_KEY))
    built = make_rig(tmp_path, monkeypatch, client=leaky)
    try:
        built.seed_gaps()
        status, headers, body = built.post(
            "admin", built.frame + "/airlines/suggest", {"prefix": "OCN", "index": "0"})
        page = built.get("admin", built.frame + "/airlines/manage")
        errors = built.get("admin", built.frame + "/no-such-page")
        seen = capsys.readouterr()
        blob = "".join([
            body, repr(headers), page[2], repr(page[1]), errors[2],
            "".join(v.decode("utf-8", "replace") for v in built.files().values()),
            seen.out, seen.err])
        assert status == 200 and DUMMY_KEY not in blob
        assert ais.cached(built.root, "OCN")["state"] == "failed"
    finally:
        built.server.stop()


def test_the_editor_declares_the_suggestion_script(rig):
    _page = rig.get("admin", rig.frame + "/airlines/manage")[2]
    assert '<script src="/static/airline-suggest.js' in _page
    assert "airline-suggest.js" not in rig.get("admin", "/airlines")[2]
