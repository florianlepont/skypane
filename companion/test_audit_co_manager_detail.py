"""The Audit page shows who a co-manager row is about and why it exists, for
rows written by the real add, remove, leave, reassign, disable and retire
paths, without ever rendering the stored detail."""
import html
import json
import re
import urllib.parse

import pytest

import fleet_console_support as fx
from companion import prefs
from companion.pages import audit_page, co_managers_card as cards
from companion_app_server import InProcessAppServer, http_request, with_csrf
from server import fleet_db, fleet_ops

CO_EMAIL = "co-manager@example.test"
CO2_EMAIL = "co-manager-two@example.test"
INVITEE = "invitee@example.test"
NEW_OWNER = "new-owner@example.test"

REASON_EN = {
    "add_owner": "Added by the frame owner",
    "add_admin": "Added by an administrator",
    "self": "Left the frame",
    "owner": "Removed by the frame owner",
    "admin": "Removed by an administrator",
    "reassign": "Frame reassigned to a new owner",
    "retire": "Frame retired",
    "delete": "Frame deleted",
    "owner_disabled": "Frame owner was disabled",
}


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    ids = {}
    conn = fleet_db.connect(state_dir)
    try:
        ids["co"] = fleet_db.add_user(conn, CO_EMAIL, "user")
        ids["co2"] = fleet_db.add_user(conn, CO2_EMAIL, "user")
        ids["invitee"] = fleet_db.add_user(conn, INVITEE, "user")
        ids["new_owner"] = fleet_db.add_user(conn, NEW_OWNER, "user")
        fleet_db.add_co_manager(conn, seed.owned_id, ids["co"], None)
        fleet_db.add_co_manager(conn, seed.owned_id, ids["co2"], None)
    finally:
        conn.close()
    yield server, seed, ids
    server.stop()


def _post(server, cookie, device, route, form):
    status, _headers, _body = http_request(
        server.url("/devices/%s%s" % (device, route)), method="POST", cookie=cookie,
        data=with_csrf(cookie, form), extra_headers={"Origin": server.base_url()})
    assert status == 303


def _db(server, fn):
    conn = fleet_db.connect(server.state_dir)
    try:
        return fn(conn)
    finally:
        conn.close()


def _audit_body(server, language=None):
    extra = {"Accept-Language": language} if language else None
    status, _headers, body = http_request(
        server.url("/audit"), cookie=fx.admin_cookie(server.state_dir),
        extra_headers=extra)
    assert status == 200
    return body.decode("utf-8")


def _rows(body):
    return re.findall(r'<li class="audit-event">.*?</li>', body, re.S)


def _co_manager_rows(body):
    return [r for r in _rows(body) if "Co-manager" in r]


def _assert_shown(body, email, reason):
    rows = _co_manager_rows(body)
    assert rows
    assert any(email in html.unescape(r) and reason in r for r in rows), rows


def test_an_owner_add_shows_the_person_and_reason(rig):
    server, seed, ids = rig
    owner = fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL)
    _post(server, owner, seed.owned_id, cards.ADD_ROUTE, {"email": INVITEE})
    _assert_shown(_audit_body(server), INVITEE, REASON_EN["add_owner"])


def test_an_admin_add_shows_the_person_and_reason(rig):
    server, seed, ids = rig
    _post(server, fx.admin_cookie(server.state_dir), seed.owned_id,
          cards.ADD_ROUTE, {"email": INVITEE})
    _assert_shown(_audit_body(server), INVITEE, REASON_EN["add_admin"])


def test_an_owner_removal_shows_the_person_and_reason(rig):
    server, seed, ids = rig
    owner = fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL)
    _post(server, owner, seed.owned_id, cards.REMOVE_ROUTE, {"user_id": str(ids["co"])})
    _assert_shown(_audit_body(server), CO_EMAIL, REASON_EN["owner"])


def test_an_admin_removal_shows_the_person_and_reason(rig):
    server, seed, ids = rig
    _post(server, fx.admin_cookie(server.state_dir), seed.owned_id,
          cards.REMOVE_ROUTE, {"user_id": str(ids["co"])})
    _assert_shown(_audit_body(server), CO_EMAIL, REASON_EN["admin"])


def test_leaving_shows_the_person_and_reason(rig):
    server, seed, ids = rig
    co = fx.user_cookie(server.state_dir, email=CO_EMAIL)
    _post(server, co, seed.owned_id, cards.LEAVE_ROUTE, {})
    _assert_shown(_audit_body(server), CO_EMAIL, REASON_EN["self"])


def test_a_reassign_shows_every_person_and_reason(rig):
    server, seed, ids = rig
    actor = fx.ACTOR
    _db(server, lambda c: fleet_ops.reassign_frame(
        c, server.state_dir, seed.owned_id, ids["new_owner"], actor))
    body = _audit_body(server)
    _assert_shown(body, CO_EMAIL, REASON_EN["reassign"])
    _assert_shown(body, CO2_EMAIL, REASON_EN["reassign"])


def test_an_owner_disable_shows_every_person_and_reason(rig):
    server, seed, ids = rig
    _db(server, lambda c: fleet_db.set_user_disabled(c, fx.OWNER_EMAIL, True))
    body = _audit_body(server)
    _assert_shown(body, CO_EMAIL, REASON_EN["owner_disabled"])
    _assert_shown(body, CO2_EMAIL, REASON_EN["owner_disabled"])


def test_a_retire_shows_every_person_and_reason(rig):
    server, seed, ids = rig
    _db(server, lambda c: fleet_ops.retire_frame(
        c, server.state_dir, seed.owned_id, fx.ACTOR))
    body = _audit_body(server)
    _assert_shown(body, CO_EMAIL, REASON_EN["retire"])
    _assert_shown(body, CO2_EMAIL, REASON_EN["retire"])


def test_a_delete_shows_every_person_and_reason(rig):
    server, seed, ids = rig
    _db(server, lambda c: fleet_db.remove_device(c, fx.MAC_OWNED, fx.ACTOR))
    body = _audit_body(server)
    _assert_shown(body, CO_EMAIL, REASON_EN["delete"])


def _append(server, action, detail, outcome="ok", target="d_00000001"):
    def write(conn):
        with fleet_db.transaction(conn):
            fleet_db.audit_append(
                conn, fx.ACTOR, action, "device", target, outcome, detail)
    _db(server, write)


def test_an_unknown_via_gets_the_generic_label_never_the_raw_word(rig):
    server, seed, ids = rig
    _append(server, "device.co_manager_remove",
            {"co_manager_user_id": ids["co"], "via": "zz_secret_word"})
    _append(server, "device.co_manager_add",
            {"co_manager_user_id": ids["co"], "via": "reassign"})
    body = _audit_body(server)
    assert "zz_secret_word" not in body
    rows = _co_manager_rows(body)
    assert len(rows) == 2 and all("Other reason" in r for r in rows)


def test_an_unknown_or_missing_user_gets_the_neutral_text(rig):
    server, seed, ids = rig
    _append(server, "device.co_manager_remove",
            {"co_manager_user_id": 987654, "via": "owner"})
    _append(server, "device.co_manager_remove", {"via": "owner"})
    _append(server, "device.co_manager_remove",
            {"co_manager_user_id": "1 or 1=1", "via": "owner"})
    body = _audit_body(server)
    rows = _co_manager_rows(body)
    assert len(rows) == 3
    assert all("Unknown user" in r and REASON_EN["owner"] in r for r in rows)
    assert "987654" not in body


def test_the_raw_detail_and_unknown_keys_never_appear(rig):
    server, seed, ids = rig
    _append(server, "device.co_manager_remove",
            {"co_manager_user_id": ids["co"], "via": "owner",
             "extra_key": "leak-value-123", "typed": "typed@example.test"})
    _append(server, "device.co_manager_add", {"reason": "unknown"}, outcome="denied")
    _append(server, "device.co_manager_add", {"reason": "write"}, outcome="failed")
    body = _audit_body(server)
    for text in ("leak-value-123", "extra_key", "typed@example.test",
                 "co_manager_user_id", '"via"', "{", "unknown", "write"):
        assert text not in body.replace("Unknown user", ""), text
    rows = _co_manager_rows(body)
    assert len(rows) == 3
    assert sum(CO_EMAIL in r for r in rows) == 1


def test_a_malformed_stored_detail_does_not_break_the_page(rig):
    server, seed, ids = rig

    def write(conn):
        with fleet_db.transaction(conn):
            conn.execute(
                "INSERT INTO audit_log (ts, actor_label, action, target_type, target_id, "
                "outcome, detail) VALUES (4000000000, 'x', 'device.co_manager_add', "
                "'device', 'd_00000001', 'ok', ?)", ("{not json",))
    _db(server, write)
    body = _audit_body(server)
    assert "Unknown user" in body and "Other reason" in body
    assert "not json" not in body


def test_an_email_with_html_characters_is_escaped(rig):
    server, seed, ids = rig
    hostile = "<b>x</b>&\"'@example.test"
    ident = _db(server, lambda c: _force_user(c, hostile))
    _append(server, "device.co_manager_add", {"co_manager_user_id": ident, "via": "admin"})
    body = _audit_body(server)
    assert hostile not in body and "<b>x</b>" not in body
    assert "&lt;b&gt;x&lt;/b&gt;" in body


def _force_user(conn, email):
    with fleet_db.transaction(conn):
        cur = conn.execute(
            "INSERT INTO users (email, role, disabled, created_at) VALUES (?, 'user', 0, 1)",
            (email,))
        return int(cur.lastrowid)


def test_other_actions_are_unchanged(rig):
    server, seed, ids = rig
    _append(server, "pairing.claim", {"co_manager_user_id": ids["co"], "via": "owner"})
    body = _audit_body(server)
    row = _rows(body)[0]
    assert "Pairing code claimed" in row
    assert CO_EMAIL not in body and "Other reason" not in body


def test_the_french_page_shows_french_reasons(rig):
    server, seed, ids = rig
    _post(server, fx.admin_cookie(server.state_dir), seed.owned_id,
          cards.REMOVE_ROUTE, {"user_id": str(ids["co"])})
    body = html.unescape(_audit_body(server, language="fr"))
    assert CO_EMAIL in body
    assert "Retiré par un administrateur" in body
    assert "Personne" in body and "Raison" in body
    assert "Removed by" not in body


def test_every_whitelisted_reason_has_a_label():
    assert {via for _action, via in audit_page.REASON_LABELS} == {
        "owner", "admin", "self", "reassign", "retire", "delete", "owner_disabled",
        "user_deleted"}


def test_the_stored_detail_is_json_the_page_never_echoes(rig):
    server, seed, ids = rig
    detail = {"co_manager_user_id": ids["co"], "via": "owner"}
    _append(server, "device.co_manager_add", detail)
    body = _audit_body(server)
    assert json.dumps(detail, sort_keys=True) not in html.unescape(body)
    assert urllib.parse.quote("co_manager_user_id") not in body


def test_a_named_target_shows_its_id_as_a_separate_secondary_item(rig):
    """the target's stored id is never glued to its e-mail: the Target item holds the address
    alone and the id sits in an item of its own, labelled, in both languages"""
    server, seed, ids = rig

    def write(conn):
        with fleet_db.transaction(conn):
            fleet_db.audit_append(
                conn, fx.ACTOR, "user.delete", "user", str(ids["co"]), "ok", {})
    _db(server, write)
    for language, label in (("en", "Internal ID"), ("fr", "Identifiant interne")):
        body = _audit_body(server, language)
        row = next(r for r in _rows(body) if CO_EMAIL in html.unescape(r))
        assert re.search(
            r'<dt>%s</dt><dd><span class="cell-secondary mono">%d</span>' % (label, ids["co"]),
            row), row
        assert not re.search(r"%s</span><span" % re.escape(CO_EMAIL), row)
