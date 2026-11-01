#!/usr/bin/env python3
"""Co-managers do not change the live frame.

A live-like state directory is migrated into fleet.db, the live frame is
polled, co-managers are added to and removed from it, and the poll response,
the state directory and the frame's `devices` row must come out identical.
The byos server never reads membership, so only fleet.db itself may change.
"""
import hashlib
import importlib.util
import json
import os
import sys
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from server import fleet_db, fleet_migrate  # noqa: E402
from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state, snapshot_dir  # noqa: E402

OWNER = "owner@example.com"
POLL_HEADERS = {
    "X-Battery-Mv": "3900",
    "X-Fw-Version": "1.0.0",
    "X-Boot-Reason": "timer",
    "X-Rssi": "-60",
}
LEGACY_FILES = ("devices.json", "byos_state.json", "device_config.json")
# The database and the server's own log are the only files a membership
# change or a running server may touch.
_MOVING_PREFIXES = ("fleet.db", "byos.stdout.log")
DEVICE_COLUMNS = (
    "id", "owner_user_id", "mac", "secret_sha256", "token", "state_path", "name",
    "location_id", "hardware_type")


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


def _fetch_bytes(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()


def _poll_via_url(server, token):
    status, doc = server.display(token, POLL_HEADERS)
    assert status == 200
    image = _fetch_bytes(doc["image_url"])
    normalised = dict(doc)
    normalised["image_url"] = doc["image_url"].replace(
        "127.0.0.1:%d" % server.port, "HOST")
    return normalised, hashlib.sha256(image).hexdigest()


def _stable_snapshot(state_dir):
    return {
        path: value for path, value in snapshot_dir(state_dir).items()
        if not path.startswith(_MOVING_PREFIXES)}


def _device_row(state_dir, mac):
    conn = fleet_db.connect_readonly(state_dir)
    try:
        row = fleet_db.get_device_by_mac(conn, mac)
        return {name: row[name] for name in DEVICE_COLUMNS}
    finally:
        conn.close()


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_byos_module():
    spec = importlib.util.spec_from_file_location(
        "byos_server_co_manager", os.path.join(HERE, "byos_server.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _add_two_co_managers(state_dir, device_id):
    """An admin and a user who never signed in become co-managers."""
    conn = fleet_db.connect(state_dir)
    try:
        owner_id = fleet_db.get_device_owner(conn, device_id)
        admin_id = fleet_db.add_user(conn, "admin@example.com", "admin")
        silent_id = fleet_db.add_user(conn, "never-signed-in@example.com", "user")
        for user_id in (admin_id, silent_id):
            fleet_db.add_co_manager(conn, device_id, user_id, owner_id)
        return [admin_id, silent_id]
    finally:
        conn.close()


def _remove_co_managers(state_dir, device_id, user_ids):
    conn = fleet_db.connect(state_dir)
    try:
        for user_id in user_ids:
            assert fleet_db.remove_co_manager(conn, device_id, user_id)
    finally:
        conn.close()


def _live_frame(tmp_path, servers):
    live = seed_live_like_state(str(tmp_path))
    assert fleet_migrate.main(
        ["--state-dir", live.state_dir, "--owner-email", OWNER]) == 0
    server = servers(live.state_dir)
    return live, server


def _live_device_id(live):
    return _device_row(live.state_dir, live.mac)["id"]


def test_co_managers_do_not_change_the_live_frame_poll_files_or_row(tmp_path, servers):
    live, server = _live_frame(tmp_path, servers)
    device_id = _live_device_id(live)
    poll = _poll_via_url(server, live.token)
    row = _device_row(live.state_dir, live.mac)
    snapshot_before_change = _stable_snapshot(live.state_dir)
    assert row["token"] == live.token and row["state_path"] == "."

    _add_two_co_managers(live.state_dir, device_id)

    # Adding membership rewrites no file except fleet.db: every other file
    # keeps its content and its modification time.
    assert _stable_snapshot(live.state_dir) == snapshot_before_change
    assert _device_row(live.state_dir, live.mac) == row
    assert _poll_via_url(server, live.token) == poll
    now = _stable_snapshot(live.state_dir)
    for name in LEGACY_FILES:
        assert now[name] == snapshot_before_change[name], name
    assert _device_row(live.state_dir, live.mac) == row


def test_removing_the_co_managers_leaves_the_live_frame_unchanged(tmp_path, servers):
    live, server = _live_frame(tmp_path, servers)
    device_id = _live_device_id(live)
    poll = _poll_via_url(server, live.token)
    row = _device_row(live.state_dir, live.mac)
    snapshot_before_change = _stable_snapshot(live.state_dir)

    user_ids = _add_two_co_managers(live.state_dir, device_id)
    _remove_co_managers(live.state_dir, device_id, user_ids)

    assert _stable_snapshot(live.state_dir) == snapshot_before_change
    assert _device_row(live.state_dir, live.mac) == row
    assert _poll_via_url(server, live.token) == poll
    now = _stable_snapshot(live.state_dir)
    for name in LEGACY_FILES:
        assert now[name] == snapshot_before_change[name], name


def test_co_managers_do_not_change_what_the_byos_loaders_read(tmp_path, servers):
    live, _server = _live_frame(tmp_path, servers)
    device_id = _live_device_id(live)
    byos = _load_byos_module()
    registry_before = byos.load_registry(live.state_dir)
    state_before = byos.load_state(live.state_dir)
    raw_before = {
        name: _read_json(os.path.join(live.state_dir, name)) for name in LEGACY_FILES}
    bytes_before = {
        name: _file_bytes(os.path.join(live.state_dir, name)) for name in LEGACY_FILES}

    _add_two_co_managers(live.state_dir, device_id)

    assert byos.load_registry(live.state_dir) == registry_before
    assert byos.load_state(live.state_dir) == state_before
    for name in LEGACY_FILES:
        path = os.path.join(live.state_dir, name)
        assert _file_bytes(path) == bytes_before[name], name
        assert _read_json(path) == raw_before[name], name
    assert byos.secret_matches(
        byos.load_registry(live.state_dir), live.mac, live.secret_hex)


def _file_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()
