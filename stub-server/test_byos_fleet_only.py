#!/usr/bin/env python3
"""Device-server identity outcomes for a migrated fleet.db.

Every state directory here holds identity in fleet.db only (the legacy
devices.json and byos_state.json are removed after the import), so these
outcomes are the same whether or not the server still has a legacy
fallback. Everything runs against a real byos_server.py subprocess with
synthetic MACs, secrets and tokens.
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
