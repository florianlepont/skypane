#!/usr/bin/env python3
"""Tests for server/fleet_migrate.py: identity-preserving, idempotent,
previewable import of the legacy device files into fleet.db."""
import json
import os
import stat
import subprocess
import sys
import zoneinfo

import pytest

import server.fleet_db as fleet_db
import server.fleet_migrate as fleet_migrate
import server.hardware as hardware
import skypane_live_state as live
from skypane_test_support import child_env

OWNER = "owner@example.com"


@pytest.fixture
def seeded(tmp_path):
    return live.seed_live_like_state(str(tmp_path))


def _run(seeded, *extra, owner=OWNER):
    args = ["--state-dir", seeded.state_dir, *extra]
    if owner:
        args += ["--owner-email", owner]
    return fleet_migrate.main(args)


def _db_files(snap):
    return {k: v for k, v in snap.items() if not k.startswith("fleet.db")}


def _without_wal_sides(snap):
    # A read-only WAL connection may leave empty -wal/-shm files behind.
    return {k: v for k, v in snap.items() if not k.endswith(("-wal", "-shm"))}


def _db_main(state_dir):
    path = fleet_db.fleet_db_path(state_dir)
    return live.snapshot_dir(state_dir)[os.path.basename(path)]


def _logical(state_dir):
    conn = fleet_db.connect_readonly(state_dir)
    try:
        return [s for s in fleet_db.dump_logical(conn) if "created_at" not in s]
    finally:
        conn.close()


def _write(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc if isinstance(doc, str) else json.dumps(doc))


def test_first_run_imports_live_frame_identity(seeded, capsys):
    before = live.snapshot_dir(seeded.state_dir)
    assert _run(seeded) == 0
    after = live.snapshot_dir(seeded.state_dir)
    assert _db_files(after) == before

    path = fleet_db.fleet_db_path(seeded.state_dir)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    conn = fleet_db.connect_readonly(seeded.state_dir)
    try:
        users = fleet_db.list_users(conn)
        assert [(u["email"], u["role"]) for u in users] == [(OWNER, "admin")]
        locs = fleet_db.list_locations(conn)
        assert [(r["name"], r["latitude"], r["longitude"], r["timezone"]) for r in locs] == [
            ("Orly", 48.7233, 2.3794, "Europe/Paris")
        ]
        dev = fleet_db.get_device_by_mac(conn, seeded.mac)
        assert dev["secret_sha256"] == live.secret_hash(seeded.secret_hex)
        assert dev["token"] == seeded.token
        assert dev["hardware_type"] == hardware.LEGACY_KEY
        assert dev["state_path"] == "."
        assert dev["owner_user_id"] == users[0]["id"]
        assert dev["location_id"] == locs[0]["id"]
        assert fleet_db.meta_get(conn, fleet_db.META_MIGRATED) is not None
        assert fleet_db.meta_get(conn, fleet_db.META_BOOTSTRAP_OWNER) == str(users[0]["id"])
    finally:
        conn.close()
    out = capsys.readouterr()
    for text in (out.out, out.err):
        assert seeded.token not in text
        assert live.secret_hash(seeded.secret_hex) not in text


def test_second_run_is_a_noop(seeded, capsys):
    assert _run(seeded) == 0
    capsys.readouterr()
    main_before = _db_main(seeded.state_dir)
    logical = _logical(seeded.state_dir)
    assert _run(seeded) == 0
    assert "nothing to do" in capsys.readouterr().out
    assert _db_main(seeded.state_dir) == main_before
    assert _logical(seeded.state_dir) == logical


def test_second_run_needs_no_owner_email(seeded):
    assert _run(seeded) == 0
    assert _run(seeded, owner=None) == 0


def test_failure_inside_transaction_leaves_nothing(seeded, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("injected")

    monkeypatch.setattr(fleet_db, "add_device", boom)
    with pytest.raises(RuntimeError):
        fleet_migrate.migrate(seeded.state_dir, OWNER, dry_run=False)
    conn = fleet_db.connect_readonly(seeded.state_dir)
    try:
        assert fleet_db.list_users(conn) == []
        assert fleet_db.list_devices(conn) == []
        assert fleet_db.meta_get(conn, fleet_db.META_MIGRATED) is None
    finally:
        conn.close()
    monkeypatch.undo()
    assert _run(seeded) == 0


def test_dry_run_fresh_directory_writes_nothing(seeded, capsys):
    before = live.snapshot_dir(seeded.state_dir)
    assert _run(seeded, "--dry-run") == 0
    assert live.snapshot_dir(seeded.state_dir) == before
    assert not os.path.exists(fleet_db.fleet_db_path(seeded.state_dir))
    assert "would add device " + seeded.mac in capsys.readouterr().out


def test_dry_run_on_migrated_directory_changes_nothing(seeded):
    assert _run(seeded) == 0
    before = _without_wal_sides(live.snapshot_dir(seeded.state_dir))
    assert _run(seeded, "--dry-run") == 0
    assert _without_wal_sides(live.snapshot_dir(seeded.state_dir)) == before


@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_missing_owner_email_aborts_before_writing(seeded, flags, capsys):
    assert _run(seeded, *flags, owner=None) == 2
    assert "owner-email" in capsys.readouterr().err
    assert not os.path.exists(fleet_db.fleet_db_path(seeded.state_dir))


def test_invalid_owner_email_is_rejected(seeded):
    assert _run(seeded, owner="not-an-email") == 2
    assert not os.path.exists(fleet_db.fleet_db_path(seeded.state_dir))


@pytest.mark.parametrize(
    "doc",
    [
        "{not json",
        {"devices": []},
        ["x"],
        {"devices": {"AA-BB": {"secret_sha256": "0" * 64}}},
        {"devices": {"aa:bb:cc:dd:ee:01": {"secret_sha256": "xyz"}}},
        {"devices": {"aa:bb:cc:dd:ee:01": {"secret_sha256": "A" * 64}}},
    ],
)
def test_malformed_registry_aborts(seeded, doc):
    _write(seeded.devices_path, doc)
    assert _run(seeded) == 2
    assert not os.path.exists(fleet_db.fleet_db_path(seeded.state_dir))


@pytest.mark.parametrize(
    "doc",
    [
        "[",
        {"tokens": []},
        {"tokens": {"aa:bb:cc:dd:ee:01": 5}},
        {"tokens": {"zz": "t"}},
        {"tokens": {"DE:AD:BE:EF:00:0G": "t"}},
        {"tokens": {"DE-AD-BE-EF-00-01": "t"}},
        {"tokens": {"DE:AD:BE:EF:00": "t"}},
        {"tokens": {"de:ad:be:ef:00:01\n": "t"}},
    ],
)
def test_malformed_state_aborts(seeded, doc):
    _write(seeded.state_path, doc)
    assert _run(seeded) == 2
    assert not os.path.exists(fleet_db.fleet_db_path(seeded.state_dir))


STRAY_MAC = "aa:bb:cc:dd:ee:99"
STRAY_TOKEN = "secret-stray-token"
UPPER_MAC = "DE:AD:BE:EF:00:01"
UPPER_TOKEN = "secret-upper-token"
SKIPPED_LINE = "skipped 1 token(s) for unregistered device(s)"


def _add_stray_token(seeded):
    _write(seeded.state_path,
           {"tokens": {seeded.mac: seeded.token, STRAY_MAC: STRAY_TOKEN}})


def _device_tokens(state_dir):
    conn = fleet_db.connect_readonly(state_dir)
    try:
        return fleet_db.tokens_by_mac(conn)
    finally:
        conn.close()


def test_orphan_token_is_skipped_counted_and_never_imported(seeded, capsys):
    _add_stray_token(seeded)
    assert _run(seeded, "--dry-run") == 0
    dry = capsys.readouterr()
    assert SKIPPED_LINE in dry.out
    assert not os.path.exists(fleet_db.fleet_db_path(seeded.state_dir))

    assert _run(seeded) == 0
    real = capsys.readouterr()
    assert SKIPPED_LINE in real.out
    assert _device_tokens(seeded.state_dir) == {seeded.mac: seeded.token}
    for text in (dry.out, dry.err, real.out, real.err):
        assert STRAY_TOKEN not in text


def test_second_run_with_orphan_token_is_a_noop(seeded, capsys):
    _add_stray_token(seeded)
    assert _run(seeded) == 0
    capsys.readouterr()
    legacy_before = {
        k: v for k, v in live.snapshot_dir(seeded.state_dir).items()
        if not k.startswith("fleet.db")
    }
    main_before = _db_main(seeded.state_dir)
    assert _run(seeded) == 0
    out = capsys.readouterr().out
    assert "nothing to do" in out
    assert SKIPPED_LINE in out
    assert _db_main(seeded.state_dir) == main_before
    assert _db_files(live.snapshot_dir(seeded.state_dir)) == legacy_before


def test_remove_then_migrate_succeeds_in_both_modes(seeded, capsys):
    second = "aa:bb:cc:dd:ee:02"
    registry = json.load(open(seeded.devices_path, encoding="utf-8"))
    registry["devices"][second] = {"secret_sha256": "1" * 64}
    _write(seeded.devices_path, registry)
    _write(seeded.state_path,
           {"tokens": {seeded.mac: seeded.token, second: "second-token"}})
    cli = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "stub-server", "devices_cli.py")
    result = subprocess.run(
        [sys.executable, cli, "--state-dir", seeded.state_dir, "remove", "--mac", second],
        capture_output=True, text=True, env=child_env(),
    )
    assert result.returncode == 0, result.stderr

    assert _run(seeded, "--dry-run") == 0
    assert _run(seeded) == 0
    capsys.readouterr()
    assert _device_tokens(seeded.state_dir) == {seeded.mac: seeded.token}
    with open(seeded.state_path, encoding="utf-8") as fh:
        assert json.load(fh)["tokens"] == {seeded.mac: seeded.token}


@pytest.mark.parametrize("key", [STRAY_MAC, UPPER_MAC])
@pytest.mark.parametrize("bad", ["", 5, None])
def test_malformed_token_on_an_orphan_mac_still_aborts(seeded, bad, key):
    _write(seeded.state_path,
           {"tokens": {seeded.mac: seeded.token, key: bad}})
    assert _run(seeded) == 2
    assert not os.path.exists(fleet_db.fleet_db_path(seeded.state_dir))


@pytest.mark.parametrize("key", [UPPER_MAC, "De:aD:be:EF:00:01"])
def test_upper_case_token_key_is_skipped_in_both_modes(seeded, capsys, key):
    _write(seeded.state_path,
           {"tokens": {seeded.mac: seeded.token, key: UPPER_TOKEN}})
    assert _run(seeded, "--dry-run") == 0
    dry = capsys.readouterr()
    assert SKIPPED_LINE in dry.out
    assert not os.path.exists(fleet_db.fleet_db_path(seeded.state_dir))

    assert _run(seeded) == 0
    real = capsys.readouterr()
    assert SKIPPED_LINE in real.out
    assert _device_tokens(seeded.state_dir) == {seeded.mac: seeded.token}
    for text in (dry.out, dry.err, real.out, real.err):
        assert UPPER_TOKEN not in text


def test_second_run_with_upper_case_token_key_is_a_noop(seeded, capsys):
    _write(seeded.state_path,
           {"tokens": {seeded.mac: seeded.token, UPPER_MAC: UPPER_TOKEN}})
    assert _run(seeded) == 0
    capsys.readouterr()
    legacy_before = {
        k: v for k, v in live.snapshot_dir(seeded.state_dir).items()
        if not k.startswith("fleet.db")
    }
    main_before = _db_main(seeded.state_dir)
    assert _run(seeded) == 0
    out = capsys.readouterr().out
    assert "nothing to do" in out
    assert SKIPPED_LINE in out
    assert _db_main(seeded.state_dir) == main_before
    assert _db_files(live.snapshot_dir(seeded.state_dir)) == legacy_before


def test_upper_case_key_of_a_registered_mac_loses_to_the_lowercase_token(
    seeded, capsys
):
    _write(seeded.state_path,
           {"tokens": {seeded.mac: seeded.token, seeded.mac.upper(): UPPER_TOKEN}})
    assert _run(seeded) == 0
    out = capsys.readouterr()
    assert SKIPPED_LINE in out.out
    assert _device_tokens(seeded.state_dir) == {seeded.mac: seeded.token}
    assert UPPER_TOKEN not in out.out + out.err


def test_upper_case_key_alone_leaves_the_registered_device_without_a_token(
    seeded, capsys
):
    _write(seeded.state_path, {"tokens": {seeded.mac.upper(): UPPER_TOKEN}})
    assert _run(seeded) == 0
    out = capsys.readouterr()
    assert SKIPPED_LINE in out.out
    assert UPPER_TOKEN not in out.out + out.err
    assert UPPER_TOKEN not in _device_tokens(seeded.state_dir).values()
    conn = fleet_db.connect_readonly(seeded.state_dir)
    try:
        assert conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] == 1
    finally:
        conn.close()


def test_absent_legacy_files_migrate_an_empty_fleet(tmp_path):
    assert fleet_migrate.main(["--state-dir", str(tmp_path), "--owner-email", OWNER]) == 0
    conn = fleet_db.connect_readonly(str(tmp_path))
    try:
        assert fleet_db.list_devices(conn) == []
        assert len(fleet_db.list_users(conn)) == 1
        assert fleet_db.meta_get(conn, fleet_db.META_MIGRATED) is not None
    finally:
        conn.close()


def test_reconcile_after_rollback_period_is_legacy_wins_without_deleting(seeded):
    assert _run(seeded) == 0
    new_mac = "aa:bb:cc:dd:ee:02"
    new_hash = live.secret_hash("b" * 64)
    changed_hash = live.secret_hash("c" * 64)
    _write(seeded.devices_path, {"devices": {
        seeded.mac: {"secret_sha256": changed_hash},
        new_mac: {"secret_sha256": new_hash},
    }})
    _write(seeded.state_path, {"tokens": {seeded.mac: "rotated-token", new_mac: "new-token"}})
    assert _run(seeded) == 0
    conn = fleet_db.connect_readonly(seeded.state_dir)
    try:
        old = fleet_db.get_device_by_mac(conn, seeded.mac)
        assert old["secret_sha256"] == changed_hash
        assert old["token"] == "rotated-token"
        new = fleet_db.get_device_by_mac(conn, new_mac)
        owner = fleet_db.meta_get(conn, fleet_db.META_BOOTSTRAP_OWNER)
        assert str(new["owner_user_id"]) == owner
        assert new["token"] == "new-token"
        assert len(fleet_db.list_devices(conn)) == 2
    finally:
        conn.close()


def test_reconcile_never_deletes_or_clears_a_token(seeded):
    assert _run(seeded) == 0
    _write(seeded.devices_path, {"devices": {}})
    _write(seeded.state_path, {"tokens": {}})
    assert _run(seeded) == 0
    conn = fleet_db.connect_readonly(seeded.state_dir)
    try:
        assert fleet_db.get_device_by_mac(conn, seeded.mac)["token"] == seeded.token
    finally:
        conn.close()


def test_device_removed_from_both_places_stays_removed(seeded):
    assert _run(seeded) == 0
    conn = fleet_db.connect(seeded.state_dir)
    fleet_db.remove_device(conn, seeded.mac)
    conn.close()
    _write(seeded.devices_path, {"devices": {}})
    _write(seeded.state_path, {"tokens": {}})
    assert _run(seeded) == 0
    conn = fleet_db.connect_readonly(seeded.state_dir)
    try:
        assert fleet_db.list_devices(conn) == []
    finally:
        conn.close()


def test_corrupt_fleet_db_aborts(seeded):
    with open(fleet_db.fleet_db_path(seeded.state_dir), "wb") as fh:
        fh.write(b"this is not a sqlite database" * 20)
    assert _run(seeded) == 2


def test_orly_constants_match_the_runway_config():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "adsb-test", "runway3.json"), encoding="utf-8") as fh:
        center = json.load(fh)["center"]
    assert fleet_migrate.ORLY_LATITUDE == center["lat"]
    assert fleet_migrate.ORLY_LONGITUDE == center["lon"]
    zoneinfo.ZoneInfo(fleet_migrate.ORLY_TIMEZONE)


def _downgrade_to_v1(state_dir):
    conn = fleet_db.connect(state_dir)
    conn.execute("DROP TRIGGER devices_owner_not_co_manager")
    conn.execute("DROP TABLE device_co_managers")
    conn.execute("DROP TRIGGER audit_log_no_update")
    conn.execute("DROP TRIGGER audit_log_no_delete")
    conn.execute("DROP TABLE audit_log")
    conn.execute("DROP TABLE pending_devices")
    conn.execute("ALTER TABLE locations DROP COLUMN owner_user_id")
    conn.execute("DROP TABLE sessions")
    conn.execute("PRAGMA user_version = 1")
    conn.close()


def test_pending_schema_is_previewed_applied_and_idempotent(seeded, capsys):
    assert _run(seeded) == 0
    _downgrade_to_v1(seeded.state_dir)
    capsys.readouterr()
    before = _without_wal_sides(live.snapshot_dir(seeded.state_dir))
    assert _run(seeded, "--dry-run") == 0
    assert "would upgrade fleet.db schema 1 -> %d" % fleet_db.SCHEMA_VERSION in capsys.readouterr().out
    assert _without_wal_sides(live.snapshot_dir(seeded.state_dir)) == before
    assert _run(seeded) == 0
    assert "upgrade fleet.db schema 1 -> %d" % fleet_db.SCHEMA_VERSION in capsys.readouterr().out
    conn = fleet_db.connect_readonly(seeded.state_dir)
    try:
        assert fleet_db.schema_version(conn) == fleet_db.SCHEMA_VERSION
    finally:
        conn.close()
    assert _run(seeded) == 0
    assert "nothing to do" in capsys.readouterr().out
