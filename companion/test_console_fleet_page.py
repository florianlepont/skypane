"""The admin Fleet page: rows by state, row actions, absence of secret
material, the empty state, role gating and French rendering."""
import re

import pytest

import fleet_console_support as fx
from companion import console_routes, prefs
from server import fleet_db


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def fleet(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.set_device_token(conn, fx.MAC_OWNED, "tok-fake-owned")
        fleet_db.set_pending_token(conn, fx.MAC_PENDING, "tok-fake-pending")
    finally:
        conn.close()
    fx.issue_code(server.state_dir, seed.pending_id)
    return server, seed, fx.admin_cookie(server.state_dir)


def _table(page):
    return re.search(r"<table.*?</table>", page, re.S).group(0)


def _rows(page):
    return {
        match.group(1): (match.group(2), match.group(3))
        for match in re.finditer(
            r'<tr data-frame="([^"]+)" data-kind="([^"]+)">(.*?)</tr>',
            _table(page), re.S)}


def _text(markup):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", markup)).strip()


def test_an_admin_sees_every_frame_with_its_columns_in_state_order(fleet):
    server, seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet")
    assert status == 200
    rows = _rows(page)
    assert list(rows) == [
        *sorted([seed.live_id, seed.owned_id]), seed.pending_id, seed.retired_id]
    assert [kind for kind, _ in rows.values()] == [
        "live", "live", "pending", "retired"]
    for header in ("Frame", "Owner", "Hardware", "Last seen", "Battery", "Firmware",
                   "Status", "Actions"):
        assert "<th>%s</th>" % header in page
    owned = _text(rows[seed.owned_id][1])
    assert "Kitchen" in owned and seed.owned_id in owned
    assert fx.OWNER_EMAIL in owned and "XIAO ePaper EE02" in owned
    assert "Live" in owned and "n/a" in owned and "Never" in owned
    pending = _text(rows[seed.pending_id][1])
    assert "Waiting for pairing" in pending and "Pending" in pending
    assert fx.MAC_PENDING in pending
    retired = _text(rows[seed.retired_id][1])
    assert "formerly %s" % fx.OWNER_EMAIL in retired and "Retired" in retired
    assert "Attic" in retired
    assert "4 frames" in page


def test_row_actions_follow_the_frame_state(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    rows = _rows(page)
    prefix = console_routes.FRAME_ACTION_PREFIX

    owned_cell = rows[seed.owned_id][1]
    assert "Open frame" in owned_cell and "/devices/%s/" % seed.owned_id in owned_cell
    for suffix in (console_routes.FRAME_REASSIGN_SUFFIX, console_routes.FRAME_RETIRE_SUFFIX):
        assert 'action="%s%s%s"' % (prefix, seed.owned_id, suffix) in owned_cell
    assert "Reassign frame" in owned_cell and "Retire frame" in owned_cell
    assert "Keep frame" in owned_cell
    live_cell = rows[seed.live_id][1]
    assert "Open frame" in live_cell
    assert 'action="%s%s%s"' % (prefix, seed.live_id, console_routes.FRAME_REASSIGN_SUFFIX) in live_cell
    assert "Only the owner changes. Nothing is erased." in live_cell
    assert console_routes.FRAME_RETIRE_SUFFIX not in live_cell
    pending_cell = rows[seed.pending_id][1]
    assert "<form" not in pending_cell and "Open frame" not in pending_cell
    retired_cell = rows[seed.retired_id][1]
    assert 'action="%s%s%s"' % (
        prefix, seed.retired_id, console_routes.FRAME_REACTIVATE_SUFFIX) in retired_cell
    assert "Re-activate frame" in retired_cell and "Open frame" not in retired_cell
    assert console_routes.FRAME_RETIRE_SUFFIX not in retired_cell
    assert console_routes.FRAME_REASSIGN_SUFFIX not in retired_cell
    for cell in (owned_cell, live_cell, retired_cell):
        for form in re.findall(r"<form.*?</form>", cell, re.S):
            assert 'name="csrf_token"' in form
    assert "{owner_email}" not in owned_cell
    assert "%s&#x27;s settings" % fx.OWNER_EMAIL in owned_cell


def test_the_markup_carries_no_secret_material(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    conn = fleet_db.connect(server.state_dir)
    try:
        stored_code_hash = conn.execute(
            "SELECT code_hash FROM pending_devices WHERE id = ?", (seed.pending_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    for secret in (
            fx.SECRET_HASH, "tok-fake-owned", "tok-fake-pending", fx.FAKE_CODE,
            "ABCD-2345", stored_code_hash, "code_expires_at", "code_hash", "code_salt"):
        assert secret not in page, secret


def test_the_empty_state_and_the_two_form_cards(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_users(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.set_user_disabled(conn, fx.USER_EMAIL, True)
    finally:
        conn.close()
    cookie = fx.admin_cookie(server.state_dir)
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    assert "No frames yet" in page and "<table" not in page
    assert "Pair a frame" in page and "Register a frame" in page
    owners = re.search(r'<select id="pair-owner".*?</select>', page, re.S).group(0)
    assert fx.ADMIN_EMAIL in owners and fx.OWNER_EMAIL in owners
    assert fx.USER_EMAIL not in owners
    assert 'value="%d"' % seed.user_id not in owners
    assert "No frame is waiting for a code" in page
    assert "<dialog" not in page and "confirm(" not in page
    assert "Pair frame" in page and "Register frame" in page


def test_the_pair_hint_disappears_when_a_frame_waits(fleet):
    server, _seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    assert "No frame is waiting for a code" not in page
    assert "<dialog" not in page and "confirm(" not in page


def test_autofocus_only_with_the_pair_flag(fleet):
    server, _seed, cookie = fleet
    _status, _headers, plain = fx.get(server, cookie, "/fleet")
    _status, _headers, flagged = fx.get(server, cookie, "/fleet?pair=1")
    assert "autofocus" not in plain and "autofocus" in flagged


def test_a_user_gets_the_unknown_path_404_and_anonymous_the_sign_in_redirect(fleet):
    server, _seed, _cookie = fleet
    user = fx.user_cookie(server.state_dir)
    refused = fx.get(server, user, "/fleet")
    unknown = fx.get(server, user, "/no-such-page-anywhere")
    assert refused[0] == 404 and refused[2] == unknown[2]
    status, headers, _body = fx.get(server, None, "/fleet")
    assert status == 303 and "/login" in headers["Location"]


def test_french_rendering_uses_the_console_terms(fleet):
    server, _seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie, "/fleet", headers={"Accept-Language": "fr"})
    for term in ("Cadres", "En attente", "Retiré", "Associer le cadre",
                 "Enregistrer le cadre", "En attente d’association"):
        assert term in page, term
    assert "Pair frame" not in page and "Waiting for pairing" not in page


def test_battery_last_seen_and_ordering_inside_a_state(fleet):
    import json
    import os
    import time

    from server import device_dirs
    server, seed, cookie = fleet
    directory = device_dirs.resolve_state_dir(
        server.state_dir, device_dirs.state_path_for(seed.owned_id))
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": 3900, "received_at": time.time() - 60}, fh)
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    rows = _rows(page)
    assert list(rows)[0] == seed.owned_id
    owned = _text(rows[seed.owned_id][1])
    assert re.search(r"\b\d{1,3}%", owned) and "Never" not in owned
    assert "1 min ago" in owned or "ago" in owned
