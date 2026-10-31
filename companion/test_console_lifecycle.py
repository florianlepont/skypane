"""Reassign, retire and re-activate over real HTTP: data handling, the live
frame guard, access loss for the previous owner, refusals and CSRF/role gates."""
import hashlib
import json
import os

import pytest

import fleet_console_support as fx
import provisioned_fleet as pf
from companion import console_lifecycle, console_routes, device_scope, prefs
from companion_app_server import http_request
from server import device_dirs, fleet_db, history_db, state_store


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    fleet = pf.provision_fleet(server.state_dir)
    return server, fleet, fx.admin_cookie(server.state_dir)


def _root_snapshot(state_dir):
    """Relative path -> sha256 of every file under the state
    directory except the database and its journal files."""
    out = {}
    for root, _dirs, names in os.walk(state_dir):
        for name in names:
            if name.startswith("fleet.db") or name.endswith(("-wal", "-shm", "-journal")):
                continue
            full = os.path.join(root, name)
            with open(full, "rb") as fh:
                out[os.path.relpath(full, state_dir)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def _device_row(state_dir, device_id):
    conn = fleet_db.connect(state_dir)
    try:
        row = fleet_db.get_device(conn, device_id)
        return None if row is None else dict(row)
    finally:
        conn.close()


def _pending_row(state_dir, pending_id):
    conn = fleet_db.connect(state_dir)
    try:
        row = fleet_db.get_pending(conn, pending_id)
        return None if row is None else dict(row)
    finally:
        conn.close()


def _frame_post(server, cookie, frame_id, action, **form):
    return fx.post(server, cookie, "/fleet/frames/%s/%s" % (frame_id, action), form)


def _flash_page(server, cookie, headers):
    cookies = [value.split(";")[0] for key, value in headers.items()
               if key.lower() == "set-cookie" and value.startswith("sp_flash=")]
    return fx.get(server, cookie + "; " + cookies[0], "/fleet")[2]


def _files(directory):
    found = set()
    for root, _dirs, names in os.walk(directory):
        for name in names:
            found.add(os.path.relpath(os.path.join(root, name), directory))
    return found


def _dirty(state_dir, device_id):
    """Fill the frame's directory with every kind of per-owner data."""
    directory = pf.device_dir(state_dir, device_id)
    with history_db.open_db(directory):
        pass
    state_store.save_poll_state(directory, {"hold": None})
    for name in ("calendar_secret.json", "name_overrides.json", "rules.json"):
        with open(os.path.join(directory, name), "w") as fh:
            fh.write('{"marker": "previous-owner"}')
    return directory


def _identity(state_dir, device_id):
    conn = fleet_db.connect(state_dir)
    try:
        row = conn.execute(
            "SELECT mac, secret_sha256, token FROM devices WHERE id = ?",
            (device_id,)).fetchone()
        return tuple(row)
    finally:
        conn.close()


# --- reassign ---------------------------------------------------------------


def test_reassign_wipes_the_previous_owners_data_and_keeps_the_identity(rig):
    server, fleet, cookie = rig
    directory = _dirty(server.state_dir, fleet.a1)
    assert {"history.db", "poll_state.json", "calendar_secret.json",
            "gallery/sample.png"} <= _files(directory)
    before = _identity(server.state_dir, fleet.a1)
    status, headers, _ = _frame_post(
        server, cookie, fleet.a1, "reassign", owner_user_id=str(fleet.b_id))
    assert status == 303 and headers["Location"] == "/fleet"
    assert "Frame reassigned" in _flash_page(server, cookie, headers)
    assert _files(directory) == {device_dirs.CONFIG_FILENAME, device_dirs.PANEL_FILENAME}
    with open(os.path.join(directory, device_dirs.CONFIG_FILENAME)) as fh:
        assert json.load(fh) == {}
    row = _device_row(server.state_dir, fleet.a1)
    assert row["owner_user_id"] == fleet.b_id
    assert row["location_id"] is None and row["name"] is None
    assert _identity(server.state_dir, fleet.a1) == before
    audit_rows = fx.audit_rows(server.state_dir, "device.reassign")
    assert audit_rows[-1]["outcome"] == "ok" and audit_rows[-1]["target_id"] == fleet.a1


def test_the_previous_owner_loses_access_and_the_new_owner_gains_it(rig):
    server, fleet, cookie = rig
    old_cookie = fx.user_cookie(server.state_dir, pf.USER_A_EMAIL)
    new_cookie = fx.user_cookie(server.state_dir, pf.USER_B_EMAIL)
    path = "/devices/%s/" % fleet.a1
    assert fx.get(server, old_cookie, path)[0] == 200
    assert fx.get(server, new_cookie, path)[0] == 404
    _frame_post(server, cookie, fleet.a1, "reassign", owner_user_id=str(fleet.b_id))
    assert fx.get(server, old_cookie, path)[0] == 404
    status, _headers, body = fx.get(server, new_cookie, path)
    assert status == 200
    assert pf.NAME_A1 not in body


def test_reassigning_the_live_frame_changes_only_the_owner(rig):
    server, fleet, cookie = rig
    before = _root_snapshot(server.state_dir)
    status, headers, _ = _frame_post(
        server, cookie, fleet.live, "reassign", owner_user_id=str(fleet.a_id))
    assert status == 303
    assert _device_row(server.state_dir, fleet.live)["owner_user_id"] == fleet.a_id
    after = _root_snapshot(server.state_dir)
    assert after == before


def test_retiring_the_live_frame_is_refused_and_audited(rig):
    server, fleet, cookie = rig
    before = _root_snapshot(server.state_dir)
    status, headers, _ = _frame_post(server, cookie, fleet.live, "retire")
    assert status == 303
    after = _root_snapshot(server.state_dir)
    assert after == before
    assert "Action refused" in _flash_page(server, cookie, headers)
    row = _device_row(server.state_dir, fleet.live)
    assert row is not None and row["state_path"] == "."
    rows = fx.audit_rows(server.state_dir, "device.retire")
    assert [r["outcome"] for r in rows] == ["denied"]


# --- retire and re-activate -------------------------------------------------


def test_retire_parks_the_frame_and_keeps_its_data(rig):
    server, fleet, cookie = rig
    directory = _dirty(server.state_dir, fleet.a1)
    files = _files(directory)
    old_cookie = fx.user_cookie(server.state_dir, pf.USER_A_EMAIL)
    assert pf.NAME_A1 in fx.get(server, old_cookie, "/account")[2]
    status, headers, _ = _frame_post(server, cookie, fleet.a1, "retire")
    assert status == 303
    assert "Frame retired" in _flash_page(server, cookie, headers)
    assert _device_row(server.state_dir, fleet.a1) is None
    conn = fleet_db.connect(server.state_dir)
    try:
        retired = [dict(r) for r in fleet_db.list_pending(conn)
                   if r["previous_device_id"] == fleet.a1]
    finally:
        conn.close()
    assert len(retired) == 1 and retired[0]["status"] == "retired"
    assert retired[0]["previous_owner_user_id"] == fleet.a_id
    assert _files(directory) == files
    assert fx.audit_rows(server.state_dir, "device.retire")[-1]["outcome"] == "ok"
    assert fx.get(server, old_cookie, "/devices/%s/" % fleet.a1)[0] == 404
    assert pf.NAME_A1 not in fx.get(server, old_cookie, "/account")[2]
    fleet_page_text = fx.get(server, cookie, "/fleet")[2]
    assert 'data-kind="retired"' in fleet_page_text and retired[0]["id"] in fleet_page_text


def test_reactivate_returns_the_frame_to_pairing_with_a_wiped_directory(rig):
    server, fleet, cookie = rig
    source = fleet.retired
    pending = _pending_row(server.state_dir, source)
    previous = pending["previous_state_path"]
    directory = device_dirs.resolve_state_dir(server.state_dir, previous)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "calendar_secret.json"), "w") as fh:
        fh.write("{}")
    status, headers, _ = _frame_post(server, cookie, source, "reactivate")
    assert status == 303
    assert "Frame re-activated" in _flash_page(server, cookie, headers)
    row = _pending_row(server.state_dir, source)
    assert row["status"] == "pending" and row["code_hash"] is None
    assert not os.path.exists(directory)
    assert fx.audit_rows(server.state_dir, "device.reactivate")[-1]["outcome"] == "ok"


def test_reactivating_a_row_that_is_not_retired_changes_nothing(rig):
    server, fleet, cookie = rig
    before = _pending_row(server.state_dir, fleet.pending)
    status, headers, _ = _frame_post(server, cookie, fleet.pending, "reactivate")
    assert status == 303
    assert "Frame not found" in _flash_page(server, cookie, headers)
    assert _pending_row(server.state_dir, fleet.pending) == before
    assert fx.audit_rows(server.state_dir, "device.reactivate") == []


# --- guards -----------------------------------------------------------------


def _state_fingerprint(server):
    conn = fleet_db.connect(server.state_dir)
    try:
        tables = {
            name: [tuple(r) for r in conn.execute("SELECT * FROM %s" % name)]
            for name in ("devices", "pending_devices", "audit_log")}
    finally:
        conn.close()
    files = _root_snapshot(server.state_dir)
    return tables, files


@pytest.mark.parametrize("action", ["retire", "reactivate", "reassign"])
@pytest.mark.parametrize("frame_id", [
    "d_ffffffff", "p_ffffffff", "..", "d_ZZZZZZZZ", "d_" + "0" * 40, "x"])
def test_unknown_or_malformed_ids_change_nothing(rig, action, frame_id):
    server, fleet, cookie = rig
    before = _state_fingerprint(server)
    status, headers, _ = _frame_post(
        server, cookie, frame_id, action, owner_user_id=str(fleet.b_id))
    assert status in (303, 404)
    assert _state_fingerprint(server) == before


@pytest.mark.parametrize("owner", ["", "abc", "999999", "-1", "1; DROP"])
def test_a_bad_target_owner_changes_nothing(rig, owner):
    server, fleet, cookie = rig
    before = _state_fingerprint(server)
    status, headers, _ = _frame_post(
        server, cookie, fleet.a1, "reassign", owner_user_id=owner)
    assert status == 303
    assert _state_fingerprint(server) == before
    assert "Choose an active owner" in _flash_page(server, cookie, headers)


def test_a_disabled_target_owner_changes_nothing(rig):
    server, fleet, cookie = rig
    conn = fleet_db.connect(server.state_dir)
    try:
        with fleet_db.transaction(conn):
            conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (fleet.b_id,))
    finally:
        conn.close()
    before = _state_fingerprint(server)
    status, headers, _ = _frame_post(
        server, cookie, fleet.a1, "reassign", owner_user_id=str(fleet.b_id))
    assert status == 303
    assert _state_fingerprint(server) == before
    assert "Choose an active owner" in _flash_page(server, cookie, headers)


def test_reassigning_to_the_same_owner_changes_nothing(rig):
    server, fleet, cookie = rig
    before = _state_fingerprint(server)
    status, headers, _ = _frame_post(
        server, cookie, fleet.a1, "reassign", owner_user_id=str(fleet.a_id))
    assert status == 303
    assert _state_fingerprint(server) == before
    assert "Already the owner" in _flash_page(server, cookie, headers)


def test_a_busy_frame_is_refused_without_changes(rig):
    server, fleet, cookie = rig
    directory = pf.device_dir(server.state_dir, fleet.a1)
    lock = device_scope.poll_lock_for(directory)
    assert lock.acquire(blocking=False)
    try:
        before = _state_fingerprint(server)
        status, headers, _ = _frame_post(
            server, cookie, fleet.a1, "reassign", owner_user_id=str(fleet.b_id))
        assert status == 303
        assert _state_fingerprint(server) == before
        assert "Frame is busy" in _flash_page(server, cookie, headers)
    finally:
        lock.release()


def test_a_poll_cycle_in_another_process_blocks_the_wipe(rig):
    from server import poll_cycle
    server, fleet, cookie = rig
    directory = pf.device_dir(server.state_dir, fleet.a1)
    with poll_cycle.poll_cycle_lock(directory):
        before = _state_fingerprint(server)
        status, headers, _ = _frame_post(
            server, cookie, fleet.a1, "reassign", owner_user_id=str(fleet.b_id))
        assert status == 303
        assert _state_fingerprint(server) == before
        assert "Frame is busy" in _flash_page(server, cookie, headers)


def test_the_busy_guard_releases_both_locks(rig):
    _server, fleet, _cookie = rig
    directory = pf.device_dir(_server.state_dir, fleet.a1)
    with console_lifecycle.busy_guard(directory) as free:
        assert free is True
    lock = device_scope.poll_lock_for(directory)
    assert lock.acquire(blocking=False)
    lock.release()
    with console_lifecycle.busy_guard(directory) as free:
        assert free is True


# --- access gates -----------------------------------------------------------


@pytest.mark.parametrize("action", ["retire", "reactivate", "reassign"])
def test_the_routes_are_admin_only_and_need_the_csrf_token(rig, action):
    server, fleet, cookie = rig
    before = _state_fingerprint(server)[0]
    path = "/fleet/frames/%s/%s" % (fleet.a1, action)
    user = fx.user_cookie(server.state_dir, pf.USER_A_EMAIL)
    assert fx.post(server, user, path, {"owner_user_id": str(fleet.b_id)})[0] == 404
    body = ("owner_user_id=%s" % fleet.b_id).encode()
    status, headers, _ = http_request(server.url(path), "POST", data=body)
    assert status in (302, 303) and "/" in headers["Location"]
    status, _headers, _body = http_request(
        server.url(path), "POST", data=body, cookie=cookie)
    assert status == 403
    assert _state_fingerprint(server)[0] == before


def test_the_paths_match_the_console_route_constants():
    assert console_lifecycle.FRAME_ACTION_PREFIX == console_routes.FRAME_ACTION_PREFIX
    assert console_lifecycle.RETIRE_SUFFIX == console_routes.FRAME_RETIRE_SUFFIX
    assert console_lifecycle.REACTIVATE_SUFFIX == console_routes.FRAME_REACTIVATE_SUFFIX
    assert console_lifecycle.REASSIGN_SUFFIX == console_routes.FRAME_REASSIGN_SUFFIX
    assert console_lifecycle.FLEET_PATH == console_routes.FLEET_ROUTE
    assert console_lifecycle.AUDIT_PATH == console_routes.AUDIT_ROUTE


def test_the_french_flash_strings_exist():
    from companion import i18n_fr
    keys = [k for k in i18n_fr.BY_ID if k.startswith("admin_lifecycle.")]
    assert len(keys) >= 15
