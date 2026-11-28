#!/usr/bin/env python3
"""byos device authentication against fleet.db only: an absent, unmigrated,
corrupt or too-new fleet.db refuses every request (the legacy identity files
are never consulted), enrolment writes fleet.db only, there is no shared
"default" device bucket, and the one-time import of the legacy files. Everything
that touches the request path runs against a real byos_server.py subprocess."""
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from server import fleet_db, fleet_migrate  # noqa: E402
from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, HERE)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(HERE)
    return module


fleet_cli = _load("fleet_cli_for_auth", os.path.join(HERE, "fleet_cli.py"))
byos_server = fleet_cli.byos_server

OWNER = "owner@example.com"
NEW_SECRET = "9" * 64
NEW_MAC = "aa:bb:cc:dd:ee:09"


@pytest.fixture(autouse=True)
def _no_sim(monkeypatch):
    monkeypatch.delenv("SKYPANE_SIM_HARDWARE", raising=False)


@pytest.fixture
def servers():
    started = []

    def make(state_dir, **kw):
        server = FrameServer(state_dir, **kw)
        started.append(server)
        server.start()
        return server

    yield make
    for server in started:
        server.stop()


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _migrate(state_dir):
    assert fleet_migrate.main(["--state-dir", state_dir, "--owner-email", OWNER]) == 0


def _read_json(path):
    with open(path) as fh:
        return json.load(fh)


def _write_json(path, doc):
    with open(path, "w") as fh:
        json.dump(doc, fh)


def _register_new(state_dir):
    """A second device present in the legacy registry before migration."""
    path = os.path.join(state_dir, "devices.json")
    doc = _read_json(path)
    doc["devices"][NEW_MAC] = {
        "secret_sha256": hashlib.sha256(NEW_SECRET.encode()).hexdigest()}
    _write_json(path, doc)


def _status(state_dir):
    with open(os.path.join(state_dir, "fleet_status.json")) as fh:
        return json.load(fh)


def _fault_lines(server):
    return [ln for ln in server.stdout_text().splitlines() if "fleet.db: fault" in ln]


@pytest.fixture
def live(tmp_path):
    """Legacy identity files only; a test imports them with _migrate."""
    return seed_live_like_state(str(tmp_path), migrated=False)


def test_migrated_state_authenticates_pre_migration_token(live, servers):
    before = servers(live.state_dir)
    assert before.display(live.token)[0] == 401
    assert before.setup(live.mac, live.secret_hex)[0] == 403
    before.stop()
    _migrate(live.state_dir)
    server = servers(live.state_dir)
    status, doc = server.display(live.token)
    assert status == 200
    assert "image_url" in doc and "sleep_s" in doc
    assert server.display("wrong-token")[0] == 401


def test_enrolment_writes_fleet_db_only(live, servers):
    _register_new(live.state_dir)
    _migrate(live.state_dir)
    devices_before = _sha(live.devices_path)
    state_before = _sha(live.state_path)
    server = servers(live.state_dir)
    status, body = server.setup(NEW_MAC, NEW_SECRET)
    assert status == 200
    token = body["device_token"]
    assert server.display(token)[0] == 200
    assert _sha(live.devices_path) == devices_before
    assert _sha(live.state_path) == state_before
    conn = fleet_db.connect_readonly(live.state_dir)
    try:
        assert fleet_db.tokens_by_mac(conn)[NEW_MAC] == token
    finally:
        conn.close()
    assert token not in server.stdout_text()


def test_unmigrated_state_refuses_and_is_silent(live, servers):
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 401
    assert server.setup(live.mac, live.secret_hex)[0] == 403
    assert not os.path.exists(os.path.join(live.state_dir, "fleet.db"))
    assert _status(live.state_dir)["state"] == "absent"
    assert "fault" not in server.stdout_text()


def test_fleet_db_without_marker_refuses(live, servers):
    conn = fleet_db.connect(live.state_dir)
    conn.close()
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 401
    assert server.setup(live.mac, live.secret_hex)[0] == 403
    assert _status(live.state_dir)["state"] == "absent"


def test_corrupt_fleet_db_fails_closed_and_logs_once(live, servers):
    _migrate(live.state_dir)
    db_path = os.path.join(live.state_dir, "fleet.db")
    for suffix in ("-wal", "-shm"):
        if os.path.exists(db_path + suffix):
            os.unlink(db_path + suffix)
    with open(db_path, "wb") as fh:
        fh.write(b"this is not a sqlite database" * 100)
    server = servers(live.state_dir)
    for _ in range(3):
        assert server.display(live.token)[0] == 401
    assert server.display("wrong-token")[0] == 401
    assert server.setup(live.mac, live.secret_hex)[0] == 403
    assert len(_fault_lines(server)) == 1
    assert _status(live.state_dir)["state"] == "fault"
    assert live.token not in json.dumps(_status(live.state_dir))
    log = server.stdout_text()
    assert live.token not in log
    assert live.secret_hex not in log
    os.unlink(db_path)
    assert server.display(live.token)[0] == 401
    assert _status(live.state_dir)["state"] == "absent"


def test_too_new_fleet_db_is_fault_refused_and_not_written(live, servers):
    _migrate(live.state_dir)
    db_path = os.path.join(live.state_dir, "fleet.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA user_version = %d" % (fleet_db.SCHEMA_VERSION + 1))
    conn.close()
    before = _sha(db_path)
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 401
    assert server.setup(live.mac, live.secret_hex)[0] == 403
    assert _status(live.state_dir)["state"] == "fault"
    assert _sha(db_path) == before


def test_legacy_files_that_disagree_with_fleet_db_are_ignored(live, servers):
    _migrate(live.state_dir)
    _register_new(live.state_dir)
    state = _read_json(live.state_path)
    state["tokens"][NEW_MAC] = REMOVED_TOKEN
    state["tokens"][live.mac] = "stale-" + live.token
    _write_json(live.state_path, state)
    server = servers(live.state_dir)
    assert server.setup(NEW_MAC, NEW_SECRET)[0] == 403
    assert server.display(REMOVED_TOKEN)[0] == 401
    assert server.display("stale-" + live.token)[0] == 401
    assert server.display(live.token)[0] == 200


def test_revoke_token_is_immediate_and_reenrolment_works(live, servers):
    _migrate(live.state_dir)
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 200
    assert fleet_cli.main(
        ["--state-dir", live.state_dir, "devices", "revoke-token", "--mac", live.mac]) == 0
    assert server.display(live.token)[0] == 401
    status, body = server.setup(live.mac, live.secret_hex)
    assert status == 200
    assert server.display(body["device_token"])[0] == 200


def test_removed_device_is_refused_on_setup(live, servers):
    _migrate(live.state_dir)
    server = servers(live.state_dir)
    assert fleet_cli.main(
        ["--state-dir", live.state_dir, "devices", "remove", "--mac", live.mac]) == 0
    assert server.setup(live.mac, live.secret_hex)[0] == 403


def test_failed_fleet_token_write_gives_503_and_keeps_the_existing_token(live, servers):
    _migrate(live.state_dir)
    conn = fleet_db.connect(live.state_dir)
    conn.execute(
        "CREATE TRIGGER no_token BEFORE UPDATE ON devices "
        "BEGIN SELECT RAISE(ABORT, 'blocked'); END")
    conn.close()
    before = _sha(live.state_path)
    server = servers(live.state_dir)
    status, _ = server.setup(live.mac, live.secret_hex)
    assert status == 503
    assert _sha(live.state_path) == before
    assert server.display(live.token)[0] == 200


def test_simulated_hardware_row_authenticates_with_gate_off(live, servers):
    _register_new(live.state_dir)
    _migrate(live.state_dir)
    conn = fleet_db.connect(live.state_dir)
    conn.execute("UPDATE devices SET hardware_type = ?, token = ? WHERE mac = ?",
                 ("sim-gated-type", "sim-token", NEW_MAC))
    conn.close()
    server = servers(live.state_dir)
    assert server.display("sim-token")[0] == 200


@pytest.mark.parametrize("value", [
    "aa:bb:cc:dd:ee:ff", "AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee", "aa-bb-cc-dd-ee-ff",
    "aa:bb:cc:dd:ee:fg", "", None, 5, "aa:bb:cc:dd:ee:ff:00",
])
def test_mac_validators_agree(value):
    byos_ok = byos_server.normalize_mac(value) is not None
    fleet_ok = isinstance(value, str)
    if fleet_ok:
        try:
            fleet_db._check_mac(value.lower())
        except ValueError:
            fleet_ok = False
    assert byos_ok == fleet_ok


def test_bearer_compare_visits_every_candidate(monkeypatch):
    calls = []
    real = byos_server.hmac.compare_digest

    def spy(a, b):
        calls.append(b)
        return real(a, b)

    monkeypatch.setattr(byos_server.hmac, "compare_digest", spy)
    monkeypatch.setattr(
        byos_server, "effective_tokens",
        lambda state_dir: {"a": "t1", "b": "t2", "c": "t3"})
    handler = byos_server.Handler.__new__(byos_server.Handler)
    handler.headers = {"Authorization": "Bearer t1"}
    handler.args = type("A", (), {"state_dir": "/nonexistent-state-dir"})()
    assert handler.bearer_ok() is True
    assert len(calls) == 3


# ---- default bucket ---------------------------------------------------


def test_default_bucket_untouched_by_valid_poll(live, servers):
    _migrate(live.state_dir)
    report = os.path.join(live.state_dir, "firmware", "device_report.json")
    with open(report) as fh:
        default_events = json.load(fh)["devices"]["default"]["events"]
    server = servers(live.state_dir)
    assert server.display(live.token, {"X-Fw-Version": "1.2.3"})[0] == 200
    with open(report) as fh:
        doc = json.load(fh)
    # The report loader fills missing default fields on rewrite; the
    # legacy bucket gains no event and no version.
    assert doc["devices"]["default"]["events"] == default_events
    assert doc["devices"]["default"].get("fw_version") is None
    assert doc["devices"][live.mac]["fw_version"] == "1.2.3"


def _cli(*argv, state_dir):
    return fleet_cli.main(["--state-dir", state_dir, *argv])


def _fleet_row(state_dir, mac):
    conn = fleet_db.connect_readonly(state_dir)
    try:
        return fleet_db.get_device_by_mac(conn, mac)
    finally:
        conn.close()


# ---- removed and orphan tokens ----------------------------------------

REMOVED_TOKEN = "removed-device-token"


def _give_token(state_dir, mac, token):
    path = os.path.join(state_dir, "byos_state.json")
    state = _read_json(path)
    state["tokens"][mac] = token
    _write_json(path, state)


def test_orphan_token_is_skipped_by_migration_and_rejected(live, servers):
    _give_token(live.state_dir, NEW_MAC, REMOVED_TOKEN)
    _migrate(live.state_dir)
    conn = fleet_db.connect_readonly(live.state_dir)
    try:
        assert REMOVED_TOKEN not in fleet_db.tokens_by_mac(conn).values()
    finally:
        conn.close()
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 200
    assert server.display(REMOVED_TOKEN)[0] == 401


UPPER_TOKEN = "upper-case-key-token"


def test_upper_case_token_key_is_skipped_by_migration_and_rejected(live, servers):
    _give_token(live.state_dir, live.mac.upper(), UPPER_TOKEN)
    _migrate(live.state_dir)
    conn = fleet_db.connect_readonly(live.state_dir)
    try:
        assert UPPER_TOKEN not in fleet_db.tokens_by_mac(conn).values()
    finally:
        conn.close()
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 200
    assert server.display(UPPER_TOKEN)[0] == 401


def test_remove_after_migration_leaves_no_row_and_no_token(live, servers):
    _register_new(live.state_dir)
    _give_token(live.state_dir, NEW_MAC, REMOVED_TOKEN)
    _migrate(live.state_dir)
    assert _cli("devices", "remove", "--mac", NEW_MAC, state_dir=live.state_dir) == 0
    assert _fleet_row(live.state_dir, NEW_MAC) is None
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 200
    assert server.display(REMOVED_TOKEN)[0] == 401
