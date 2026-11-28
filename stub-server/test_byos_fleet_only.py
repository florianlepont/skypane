#!/usr/bin/env python3
"""Device-server identity outcomes: fleet.db is the only source.

Frames are registered in a migrated fleet.db (the legacy devices.json and
byos_state.json are removed after the import, or written afterwards to prove
they are ignored). An absent, unmigrated or unreadable fleet.db refuses every
enrolment and poll. Everything runs against a real byos_server.py subprocess
with synthetic MACs, secrets and tokens.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from server import (  # noqa: E402
    device_dirs, fleet_db, fleet_migrate, fleet_ops, hardware,
)
from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state, secret_hash  # noqa: E402

OWNER = "owner@example.com"
LEGACY_FILES = ("devices.json", "byos_state.json")
FRESH_MAC = "aa:bb:cc:dd:ee:21"
FRESH_SECRET = "5" * 64
PENDING_MAC = "aa:bb:cc:dd:ee:22"
PENDING_SECRET = "6" * 64
UNKNOWN_MAC = "aa:bb:cc:dd:ee:99"
ACTOR = fleet_db.AuditActor(None, "cli", None)


@pytest.fixture(autouse=True)
def _no_sim(monkeypatch):
    monkeypatch.delenv("SKYPANE_SIM_HARDWARE", raising=False)


@pytest.fixture
def servers():
    started = []

    def make(state_dir):
        server = FrameServer(state_dir)
        started.append(server)
        server.start()
        return server

    yield make
    for server in started:
        server.stop()


@pytest.fixture
def fleet(tmp_path):
    """A migrated fleet.db with a live frame holding a token, a registered
    frame with no token yet and a pending frame; no legacy file remains."""
    live = seed_live_like_state(str(tmp_path))
    assert fleet_migrate.main(["--state-dir", live.state_dir, "--owner-email", OWNER]) == 0
    conn = fleet_db.connect(live.state_dir)
    try:
        owner_id = int(fleet_db.get_user_by_email(conn, OWNER)["id"])
        with fleet_db.transaction(conn):
            hw_type = live_hardware(conn, live.mac)
            new_id = fleet_db.add_device(
                conn, FRESH_MAC, secret_hash(FRESH_SECRET), hw_type, owner_id,
                state_path="auto")
            profile = hardware.get_profile(hw_type, os.environ)
            device_dirs.record_live_macs(live.state_dir, {live.mac})
            device_dirs.provision_device_dir(
                live.state_dir, new_id, profile.width, profile.height)
        fleet_ops.register_frame(
            conn, PENDING_MAC, secret_hash(PENDING_SECRET), live_hardware(conn, live.mac), ACTOR)
    finally:
        conn.close()
    for name in LEGACY_FILES:
        os.unlink(os.path.join(live.state_dir, name))
    return live


def live_hardware(conn, mac):
    return str(fleet_db.get_device_by_mac(conn, mac)["hardware_type"])


def _db_row(state_dir, table, mac):
    conn = fleet_db.connect_readonly(state_dir)
    try:
        return conn.execute(
            "SELECT token FROM %s WHERE mac = ?" % table, (mac,)).fetchone()
    finally:
        conn.close()


def test_registered_frame_enrols_and_the_token_authenticates(fleet, servers):
    server = servers(fleet.state_dir)
    status, body = server.setup(FRESH_MAC, FRESH_SECRET)
    assert status == 200
    token = body["device_token"]
    assert _db_row(fleet.state_dir, "devices", FRESH_MAC)["token"] == token
    assert server.display(token)[0] == 200
    assert server.display(token + "x")[0] == 401
    assert token not in server.stdout_text()
    assert FRESH_SECRET not in server.stdout_text()


def test_wrong_secret_is_401_and_keeps_the_existing_token(fleet, servers):
    server = servers(fleet.state_dir)
    assert server.setup(fleet.mac, "0" * 64)[0] == 401
    assert server.setup(fleet.mac, FRESH_SECRET)[0] == 401
    assert server.setup(fleet.mac, "not-hex")[0] == 401
    assert server.display(fleet.token)[0] == 200


def test_unknown_and_malformed_macs_are_refused(fleet, servers):
    server = servers(fleet.state_dir)
    assert server.setup(UNKNOWN_MAC, FRESH_SECRET)[0] == 403
    assert server.setup("not-a-mac", FRESH_SECRET)[0] == 422
    assert server.display("tok-unknown")[0] == 401
    assert server.display("")[0] == 401


def test_live_frame_keeps_polling_with_its_token(fleet, servers):
    server = servers(fleet.state_dir)
    status, doc = server.display(fleet.token)
    assert status == 200
    assert "image_url" in doc and "sleep_s" in doc
    status, body = server.setup(fleet.mac, fleet.secret_hex)
    assert status == 200
    assert server.display(body["device_token"])[0] == 200
    assert _db_row(fleet.state_dir, "devices", fleet.mac)["token"] == body["device_token"]


def test_pending_frame_enrols_and_polls(fleet, servers):
    server = servers(fleet.state_dir)
    status, body = server.setup(PENDING_MAC, PENDING_SECRET)
    assert status == 200
    token = body["device_token"]
    assert _db_row(fleet.state_dir, "pending_devices", PENDING_MAC)["token"] == token
    assert server.setup(PENDING_MAC, "1" * 64)[0] == 401
    status, doc = server.display(token)
    assert status == 200
    assert "image_url" in doc
    assert _db_row(fleet.state_dir, "devices", PENDING_MAC) is None


def test_fleet_status_is_ok_while_the_database_answers(fleet, servers):
    server = servers(fleet.state_dir)
    assert server.display(fleet.token)[0] == 200
    with open(os.path.join(fleet.state_dir, "fleet_status.json")) as fh:
        status = json.load(fh)
    assert status["state"] == "ok"
    assert fleet.token not in json.dumps(status)


# ---- legacy files are never a source --------------------------------------


def _write_legacy(state_dir, mac, secret_hex, token):
    with open(os.path.join(state_dir, "devices.json"), "w") as fh:
        json.dump({"devices": {mac: {"secret_sha256": secret_hash(secret_hex)}}}, fh)
    with open(os.path.join(state_dir, "byos_state.json"), "w") as fh:
        json.dump({"tokens": {mac: token}}, fh)


def _legacy_present(state_dir):
    return [n for n in LEGACY_FILES if os.path.exists(os.path.join(state_dir, n))]


def test_enrolment_creates_no_legacy_file(fleet, servers):
    server = servers(fleet.state_dir)
    assert server.setup(FRESH_MAC, FRESH_SECRET)[0] == 200
    assert server.setup(fleet.mac, fleet.secret_hex)[0] == 200
    assert server.setup(PENDING_MAC, PENDING_SECRET)[0] == 200
    assert _legacy_present(fleet.state_dir) == []


def test_stale_legacy_files_that_disagree_with_fleet_db_are_ignored(fleet, servers):
    _write_legacy(fleet.state_dir, UNKNOWN_MAC, FRESH_SECRET, "stale-token-only-in-legacy")
    server = servers(fleet.state_dir)
    assert server.setup(UNKNOWN_MAC, FRESH_SECRET)[0] == 403
    assert server.display("stale-token-only-in-legacy")[0] == 401
    assert server.display(fleet.token)[0] == 200


def _remove_fleet_db(state_dir):
    for suffix in ("", "-wal", "-shm"):
        path = os.path.join(state_dir, "fleet.db" + suffix)
        if os.path.exists(path):
            os.unlink(path)


def _corrupt_fleet_db(state_dir):
    _remove_fleet_db(state_dir)
    with open(os.path.join(state_dir, "fleet.db"), "wb") as fh:
        fh.write(b"this is not a sqlite database" * 100)


def _unmarked_fleet_db(state_dir):
    conn = fleet_db.connect(state_dir)
    try:
        conn.execute("DELETE FROM meta WHERE key = ?", (fleet_db.META_MIGRATED,))
    finally:
        conn.close()


@pytest.mark.parametrize("damage", [_remove_fleet_db, _corrupt_fleet_db, _unmarked_fleet_db])
def test_unreadable_fleet_db_refuses_even_with_valid_legacy_files(fleet, servers, damage):
    damage(fleet.state_dir)
    _write_legacy(fleet.state_dir, fleet.mac, fleet.secret_hex, fleet.token)
    before = {n: open(os.path.join(fleet.state_dir, n), "rb").read() for n in LEGACY_FILES}
    server = servers(fleet.state_dir)
    # The same statuses an unregistered frame and an unknown token get.
    assert server.setup(fleet.mac, fleet.secret_hex)[0] == 403
    assert server.setup(UNKNOWN_MAC, FRESH_SECRET)[0] == 403
    assert server.display(fleet.token)[0] == 401
    assert server.display("tok-unknown")[0] == 401
    log = server.stdout_text()
    for value in (fleet.secret_hex, fleet.token, secret_hash(fleet.secret_hex)):
        assert value not in log
    after = {n: open(os.path.join(fleet.state_dir, n), "rb").read() for n in LEGACY_FILES}
    assert after == before
