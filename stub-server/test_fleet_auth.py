#!/usr/bin/env python3
"""byos device authentication against fleet.db, with fallback to the legacy
files, dual-written enrolment tokens, no shared "default" device bucket and
the legacy devices_cli mirroring into a migrated fleet.db. Everything that
touches the request path runs against a real byos_server.py subprocess."""
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
devices_cli = _load("devices_cli_for_auth", os.path.join(HERE, "devices_cli.py"))
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


def _register_new(state_dir):
    """A second device present in the legacy registry before migration."""
    byos_server.register_device(
        state_dir, NEW_MAC, hashlib.sha256(NEW_SECRET.encode()).hexdigest())


def _status(state_dir):
    with open(os.path.join(state_dir, "fleet_status.json")) as fh:
        return json.load(fh)


def _fault_lines(server):
    return [ln for ln in server.stdout_text().splitlines() if "fleet.db: fault" in ln]


@pytest.fixture
def live(tmp_path):
    return seed_live_like_state(str(tmp_path))


def test_migrated_state_authenticates_pre_migration_token(live, servers):
    legacy_server = servers(live.state_dir)
    status, legacy_doc = legacy_server.display(live.token)
    assert status == 200
    legacy_server.stop()
    _migrate(live.state_dir)
    server = servers(live.state_dir)
    status, doc = server.display(live.token)
    assert status == 200
    assert set(doc) == set(legacy_doc)
    assert server.display("wrong-token")[0] == 401


def test_enrolment_dual_writes_and_old_readers_accept(live, servers):
    _register_new(live.state_dir)
    _migrate(live.state_dir)
    devices_before = _sha(live.devices_path)
    server = servers(live.state_dir)
    status, body = server.setup(NEW_MAC, NEW_SECRET)
    assert status == 200
    token = body["device_token"]
    assert server.display(token)[0] == 200
    assert _sha(live.devices_path) == devices_before
    assert byos_server.load_state(live.state_dir)["tokens"][NEW_MAC] == token
    conn = fleet_db.connect_readonly(live.state_dir)
    try:
        assert fleet_db.tokens_by_mac(conn)[NEW_MAC] == token
    finally:
        conn.close()
    registry = byos_server.load_registry(live.state_dir)
    assert byos_server.secret_matches(registry, NEW_MAC, NEW_SECRET)
    assert token not in server.stdout_text()


def test_unmigrated_state_is_silent_and_unchanged(live, servers):
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 200
    assert not os.path.exists(os.path.join(live.state_dir, "fleet.db"))
    assert _status(live.state_dir)["state"] == "absent"
    assert "fault" not in server.stdout_text()


def test_fleet_db_without_marker_is_ignored(live, servers):
    conn = fleet_db.connect(live.state_dir)
    conn.close()
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 200
    assert _status(live.state_dir)["state"] == "absent"


def test_corrupt_fleet_db_falls_back_and_logs_once(live, servers):
    _migrate(live.state_dir)
    db_path = os.path.join(live.state_dir, "fleet.db")
    for suffix in ("-wal", "-shm"):
        if os.path.exists(db_path + suffix):
            os.unlink(db_path + suffix)
    with open(db_path, "wb") as fh:
        fh.write(b"this is not a sqlite database" * 100)
    server = servers(live.state_dir)
    for _ in range(3):
        assert server.display(live.token)[0] == 200
    assert server.display("wrong-token")[0] == 401
    assert server.setup(live.mac, live.secret_hex)[0] == 200
    assert len(_fault_lines(server)) == 1
    assert _status(live.state_dir)["state"] == "fault"
    assert live.token not in json.dumps(_status(live.state_dir))
    os.unlink(db_path)
    assert server.display(live.token)[0] in (200, 401)
    assert _status(live.state_dir)["state"] == "absent"


def test_too_new_fleet_db_is_fault_and_not_written(live, servers):
    _migrate(live.state_dir)
    db_path = os.path.join(live.state_dir, "fleet.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA user_version = %d" % (fleet_db.SCHEMA_VERSION + 1))
    conn.close()
    before = _sha(db_path)
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 200
    assert server.setup(live.mac, live.secret_hex)[0] == 200
    assert _status(live.state_dir)["state"] == "fault"
    assert _sha(db_path) == before


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


def test_failed_fleet_token_write_gives_503_and_leaves_legacy_state(live, servers):
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


def test_legacy_file_names_agree_with_byos():
    assert fleet_migrate.LEGACY_REGISTRY_FILE == byos_server.REGISTRY_FILE
    assert fleet_migrate.LEGACY_STATE_FILE == os.path.basename(byos_server.state_path("d"))


def test_bearer_compare_visits_every_candidate(monkeypatch):
    calls = []
    real = byos_server.hmac.compare_digest

    def spy(a, b):
        calls.append(b)
        return real(a, b)

    monkeypatch.setattr(byos_server.hmac, "compare_digest", spy)
    handler = byos_server.Handler.__new__(byos_server.Handler)
    handler.headers = {"Authorization": "Bearer t1"}
    handler.args = type("A", (), {"state_dir": "/nonexistent-state-dir"})()
    handler.state = {"tokens": {"a": "t1", "b": "t2", "c": "t3"}}
    assert handler.bearer_ok() is True
    assert len(calls) == 3


# ---- default bucket ---------------------------------------------------


def test_default_bucket_untouched_by_valid_poll(live, servers):
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


# ---- legacy devices_cli mirroring -------------------------------------


def _cli(*argv, state_dir):
    return devices_cli_main(["--state-dir", state_dir, *argv])


def devices_cli_main(argv):
    old = sys.argv
    sys.argv = ["devices_cli.py", *argv]
    try:
        return devices_cli.main()
    finally:
        sys.argv = old


def _fleet_row(state_dir, mac):
    conn = fleet_db.connect_readonly(state_dir)
    try:
        return fleet_db.get_device_by_mac(conn, mac)
    finally:
        conn.close()


def test_devices_cli_without_fleet_db_creates_none(tmp_path):
    sd = str(tmp_path)
    assert _cli("add", "--mac", NEW_MAC, "--secret-sha256", "a" * 64, state_dir=sd) == 0
    assert _cli("revoke-token", "--mac", NEW_MAC, state_dir=sd) == 1
    assert _cli("remove", "--mac", NEW_MAC, state_dir=sd) == 0
    assert not os.path.exists(os.path.join(sd, "fleet.db"))


def test_devices_cli_mirrors_into_migrated_fleet_db(live):
    _migrate(live.state_dir)
    sd = live.state_dir
    owner_id = _fleet_row(sd, live.mac)["owner_user_id"]
    assert _cli("add", "--mac", NEW_MAC, "--secret-sha256", "a" * 64, state_dir=sd) == 0
    row = _fleet_row(sd, NEW_MAC)
    assert row["owner_user_id"] == owner_id
    assert row["hardware_type"] == fleet_migrate.hardware.LEGACY_KEY
    assert row["state_path"] == "."
    assert _cli("add", "--mac", NEW_MAC, "--secret-sha256", "b" * 64, "--replace",
                state_dir=sd) == 0
    row = _fleet_row(sd, NEW_MAC)
    assert row["secret_sha256"] == "b" * 64
    assert row["owner_user_id"] == owner_id
    assert _cli("revoke-token", "--mac", live.mac, state_dir=sd) == 0
    assert _fleet_row(sd, live.mac)["token"] is None
    assert _cli("remove", "--mac", NEW_MAC, state_dir=sd) == 0
    assert _fleet_row(sd, NEW_MAC) is None


def test_devices_cli_ignores_unmigrated_fleet_db(live):
    fleet_db.connect(live.state_dir).close()
    assert _cli("add", "--mac", NEW_MAC, "--secret-sha256", "a" * 64,
                state_dir=live.state_dir) == 0
    assert _fleet_row(live.state_dir, NEW_MAC) is None


def test_devices_cli_mirror_failure_warns_and_exits_1(live, capsys):
    _migrate(live.state_dir)
    conn = fleet_db.connect(live.state_dir)
    conn.execute(
        "CREATE TRIGGER no_insert BEFORE INSERT ON devices "
        "BEGIN SELECT RAISE(ABORT, 'blocked'); END")
    conn.close()
    rc = _cli("add", "--mac", NEW_MAC, "--secret-sha256", "a" * 64,
              state_dir=live.state_dir)
    assert rc == 1
    assert "warning: fleet.db not updated" in capsys.readouterr().err
    with open(live.devices_path) as fh:
        assert NEW_MAC in json.load(fh)["devices"]


# ---- removed and orphan tokens ----------------------------------------

REMOVED_TOKEN = "removed-device-token"


def _give_token(state_dir, mac, token):
    state = byos_server.load_state(state_dir)
    state["tokens"][mac] = token
    byos_server.save_state(state_dir, state)


def test_removed_device_token_is_rejected_after_migration(live, servers):
    _register_new(live.state_dir)
    _give_token(live.state_dir, NEW_MAC, REMOVED_TOKEN)
    assert _cli("remove", "--mac", NEW_MAC, state_dir=live.state_dir) == 0
    _migrate(live.state_dir)
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 200
    assert server.display(REMOVED_TOKEN)[0] == 401


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
    assert _cli("remove", "--mac", NEW_MAC, state_dir=live.state_dir) == 0
    assert _fleet_row(live.state_dir, NEW_MAC) is None
    assert NEW_MAC not in byos_server.load_state(live.state_dir)["tokens"]
    server = servers(live.state_dir)
    assert server.display(live.token)[0] == 200
    assert server.display(REMOVED_TOKEN)[0] == 401
