#!/usr/bin/env python3
"""Tests for fleet_cli.py: users, locations and one-owner devices managed
through the CLI, with every device change mirrored into the legacy files."""
import hashlib
import importlib.util
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
CLI_PATH = os.path.join(HERE, "fleet_cli.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, HERE)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(HERE)
    return module


fleet_cli = _load("fleet_cli_under_test", CLI_PATH)
byos_server = fleet_cli.byos_server
fleet_db = fleet_cli.fleet_db

MAC = "aa:bb:cc:dd:ee:01"
OTHER_MAC = "aa:bb:cc:dd:ee:02"
SECRET = hashlib.sha256(b"s1").hexdigest()
SECRET2 = hashlib.sha256(b"s2").hexdigest()
TOKEN = "tok-very-secret-token"


@pytest.fixture(autouse=True)
def _no_sim(monkeypatch):
    monkeypatch.delenv("SKYPANE_SIM_HARDWARE", raising=False)


@pytest.fixture
def sd(tmp_path):
    return str(tmp_path)


def run(sd, *argv):
    return fleet_cli.main(["--state-dir", sd, *argv])


def add_owner(sd, email="owner@example.com", role="admin"):
    assert run(sd, "users", "add", "--email", email, "--role", role) == 0


def add_device(sd, mac=MAC, secret=SECRET, *extra):
    return run(sd, "devices", "add", "--mac", mac, "--secret-sha256", secret,
               "--owner-email", "owner@example.com", *extra)


def db_rows(sd):
    conn = fleet_db.connect_readonly(sd)
    try:
        return fleet_db.list_devices(conn)
    finally:
        conn.close()


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def test_users_add_and_list_prints_role(sd, capsys):
    add_owner(sd)
    capsys.readouterr()
    assert run(sd, "users", "list") == 0
    out = capsys.readouterr().out
    assert "owner@example.com admin enabled" in out


def test_users_add_rejects_bad_role_email_and_duplicates(sd):
    assert run(sd, "users", "add", "--email", "a@example.com", "--role", "superuser") == 2
    assert run(sd, "users", "add", "--email", "nope", "--role", "user") == 2
    add_owner(sd)
    assert run(sd, "users", "add", "--email", "OWNER@example.com", "--role", "user") == 2


def test_users_disable_enable_and_unknown(sd, capsys):
    add_owner(sd)
    assert add_device(sd) == 0
    assert run(sd, "users", "disable", "--email", "owner@example.com") == 0
    assert db_rows(sd)[0]["owner_email"] == "owner@example.com"
    capsys.readouterr()
    run(sd, "users", "list")
    assert "disabled" in capsys.readouterr().out
    assert run(sd, "users", "enable", "--email", "owner@example.com") == 0
    assert run(sd, "users", "disable", "--email", "ghost@example.com") == 1


def _user_row(sd, email):
    conn = fleet_db.connect_readonly(sd)
    try:
        return fleet_db.get_user_by_email(conn, email)
    finally:
        conn.close()


def _session_count(sd):
    conn = fleet_db.connect_readonly(sd)
    try:
        return conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    finally:
        conn.close()


def _link_and_session(sd, email="owner@example.com"):
    conn = fleet_db.connect(sd)
    try:
        out = fleet_cli.fleet_sessions.resolve_login(
            conn, "https://t.example/", "sub-1", email, True, 1000)
        fleet_cli.fleet_sessions.create_session(
            conn, "h" * 64, user_id=out.user_id, principal="user", now=1000)
    finally:
        conn.close()


def test_users_unlink_identity_clears_link_and_sessions(sd, capsys):
    add_owner(sd)
    _link_and_session(sd)
    assert _user_row(sd, "owner@example.com")["sub"] == "sub-1"
    assert run(sd, "users", "unlink-identity", "--email", "owner@example.com") == 0
    row = _user_row(sd, "owner@example.com")
    assert row["sub"] is None and row["iss"] is None
    assert _session_count(sd) == 0
    capsys.readouterr()
    assert run(sd, "users", "unlink-identity", "--email", "owner@example.com") == 0
    assert "already unlinked" in capsys.readouterr().out
    conn = fleet_db.connect(sd)
    try:
        out = fleet_cli.fleet_sessions.resolve_login(
            conn, "https://t.example/", "sub-2", "owner@example.com", True, 1000)
    finally:
        conn.close()
    assert out.reason == "linked"


def test_users_unlink_identity_unknown_email(sd, capsys):
    assert run(sd, "users", "unlink-identity", "--email", "ghost@example.com") == 1
    assert "no such user" in capsys.readouterr().err


def test_users_disable_drops_sessions_and_enable_does_not_restore(sd, capsys):
    add_owner(sd)
    _link_and_session(sd)
    assert _session_count(sd) == 1
    assert run(sd, "users", "disable", "--email", "owner@example.com") == 0
    assert _session_count(sd) == 0
    assert run(sd, "users", "enable", "--email", "owner@example.com") == 0
    assert _session_count(sd) == 0
    out = capsys.readouterr()
    assert "sub-1" not in out.out + out.err


def test_locations_add_list_and_validation(sd, capsys):
    assert run(sd, "locations", "add", "--name", "Home", "--latitude", "48.7",
               "--longitude", "2.3", "--timezone", "Europe/Paris") == 0
    capsys.readouterr()
    assert run(sd, "locations", "list") == 0
    assert "Home" in capsys.readouterr().out
    assert run(sd, "locations", "add", "--name", "X", "--latitude", "91",
               "--longitude", "2", "--timezone", "Europe/Paris") == 2
    assert run(sd, "locations", "add", "--name", "X", "--latitude", "1",
               "--longitude", "2", "--timezone", "Mars/Base") == 2


def test_devices_add_mirrors_to_legacy_and_remove_restores_bytes(sd):
    add_owner(sd)
    assert not os.path.exists(byos_server.registry_path(sd))
    assert add_device(sd) == 0
    assert byos_server.load_registry(sd)["devices"][MAC]["secret_sha256"] == SECRET
    assert add_device(sd, OTHER_MAC, SECRET2, "--state-path", "auto") == 0
    original = read(byos_server.registry_path(sd))
    assert add_device(sd, "aa:bb:cc:dd:ee:03", SECRET, "--state-path", "auto") == 0
    assert run(sd, "devices", "remove", "--mac", "aa:bb:cc:dd:ee:03") == 0
    assert read(byos_server.registry_path(sd)) == original


def test_devices_add_rolls_back_when_legacy_write_fails(sd, capsys):
    add_owner(sd)
    byos_server.register_device(sd, MAC, SECRET)
    assert add_device(sd) == 2
    assert fleet_db.list_devices(fleet_db.connect_readonly(sd)) == []
    assert "already registered" in capsys.readouterr().err


def test_devices_add_validation_and_unknown_owner(sd):
    add_owner(sd)
    assert add_device(sd, "not-a-mac") == 2
    assert add_device(sd, MAC, "zz") == 2
    assert run(sd, "devices", "add", "--mac", MAC, "--secret-sha256", SECRET,
               "--owner-email", "ghost@example.com") == 1
    assert not os.path.exists(byos_server.registry_path(sd))


def test_simulated_hardware_needs_the_environment_gate(sd, monkeypatch):
    add_owner(sd)
    assert add_device(sd, MAC, SECRET, "--hardware-type", "sim-ee02-clone") == 2
    monkeypatch.setenv("SKYPANE_SIM_HARDWARE", "1")
    assert add_device(sd, MAC, SECRET, "--hardware-type", "sim-ee02-clone") == 0


def test_devices_list_hides_tokens_and_full_hashes(sd, capsys):
    add_owner(sd)
    assert add_device(sd, MAC, SECRET, "--name", "Frame") == 0
    state = byos_server.load_state(sd)
    state["tokens"][MAC] = TOKEN
    byos_server.save_state(sd, state)
    capsys.readouterr()
    assert run(sd, "devices", "list") == 0
    out = capsys.readouterr().out
    assert MAC in out and "owner@example.com" in out
    assert SECRET[:12] + "…" in out
    assert TOKEN not in out
    assert not re.search(r"[0-9a-f]{64}", out)


def test_devices_assign_keeps_one_owner(sd):
    add_owner(sd)
    add_owner(sd, "second@example.com", "user")
    assert add_device(sd) == 0
    assert run(sd, "devices", "assign", "--mac", MAC, "--owner-email", "second@example.com") == 0
    rows = db_rows(sd)
    assert [r["owner_email"] for r in rows] == ["second@example.com"]
    assert run(sd, "devices", "assign", "--mac", OTHER_MAC, "--owner-email", "second@example.com") == 1
    assert run(sd, "devices", "assign", "--mac", MAC, "--owner-email", "ghost@example.com") == 1


def test_devices_set_location(sd):
    add_owner(sd)
    assert add_device(sd) == 0
    run(sd, "locations", "add", "--name", "Home", "--latitude", "1",
        "--longitude", "2", "--timezone", "Europe/Paris")
    assert run(sd, "devices", "set-location", "--mac", MAC, "--location-id", "1") == 0
    assert db_rows(sd)[0]["location_name"] == "Home"
    assert run(sd, "devices", "set-location", "--mac", MAC, "--location-id", "99") == 1
    assert run(sd, "devices", "set-location", "--mac", OTHER_MAC, "--location-id", "1") == 1


def test_devices_remove_clears_registry_and_token(sd, capsys):
    add_owner(sd)
    assert add_device(sd) == 0
    state = byos_server.load_state(sd)
    state["tokens"][MAC] = TOKEN
    byos_server.save_state(sd, state)
    capsys.readouterr()
    assert run(sd, "devices", "remove", "--mac", MAC) == 0
    assert "skypane-byos" in capsys.readouterr().out
    assert MAC not in byos_server.load_registry(sd)["devices"]
    assert MAC not in byos_server.load_state(sd)["tokens"]
    assert db_rows(sd) == []
    assert run(sd, "devices", "remove", "--mac", MAC) == 1


def test_devices_revoke_token(sd):
    add_owner(sd)
    assert add_device(sd) == 0
    assert run(sd, "devices", "revoke-token", "--mac", MAC) == 1
    state = byos_server.load_state(sd)
    state["tokens"][MAC] = TOKEN
    byos_server.save_state(sd, state)
    conn = fleet_db.connect(sd)
    fleet_db.set_device_token(conn, MAC, TOKEN)
    conn.close()
    assert run(sd, "devices", "revoke-token", "--mac", MAC) == 0
    assert MAC not in byos_server.load_state(sd)["tokens"]
    conn = fleet_db.connect_readonly(sd)
    try:
        assert fleet_db.get_device_by_mac(conn, MAC)["token"] is None
    finally:
        conn.close()


def test_hardware_list_marks_simulated(capsys, monkeypatch, sd):
    assert run(sd, "hardware", "list") == 0
    assert "simulated" not in capsys.readouterr().out
    monkeypatch.setenv("SKYPANE_SIM_HARDWARE", "1")
    assert run(sd, "hardware", "list") == 0
    assert "(simulated)" in capsys.readouterr().out


def test_cli_creates_db_mode_0600_but_never_marks_migrated(sd):
    add_owner(sd)
    path = fleet_db.fleet_db_path(sd)
    assert os.stat(path).st_mode & 0o777 == 0o600
    conn = fleet_db.connect_readonly(sd)
    try:
        assert fleet_db.meta_get(conn, fleet_db.META_MIGRATED) is None
    finally:
        conn.close()


def test_state_dir_is_required():
    with pytest.raises(SystemExit) as exc:
        fleet_cli.main(["users", "list"])
    assert exc.value.code == 2


def test_script_entry_contract(sd):
    helped = subprocess.run([sys.executable, CLI_PATH, "--help"],
                            capture_output=True, text=True)
    assert helped.returncode == 0 and "--state-dir" in helped.stdout
    failed = subprocess.run(
        [sys.executable, CLI_PATH, "--state-dir", sd, "users", "add",
         "--email", "a@example.com", "--role", "superuser"],
        capture_output=True, text=True)
    assert failed.returncode == 2
    assert "error:" in failed.stderr


def test_devices_add_state_path_auto_provisions_directory(sd, monkeypatch, capsys):
    monkeypatch.setenv("SKYPANE_SIM_HARDWARE", "1")
    add_owner(sd)
    capsys.readouterr()
    assert add_device(sd, MAC, SECRET, "--hardware-type", "sim-ee02-clone",
                      "--state-path", "auto") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "registered %s" % MAC
    device_id = lines[1].split()[-1]
    assert db_rows(sd)[0]["state_path"] == "devices/" + device_id
    directory = os.path.join(sd, "devices", device_id)
    profile = fleet_cli.hardware.get_profile("sim-ee02-clone", os.environ)
    assert len(read(os.path.join(directory, "panel.bin"))) == (profile.width // 2) * profile.height
    assert os.path.exists(os.path.join(directory, "device_config.json"))
    assert not os.path.exists(os.path.join(directory, "poll_state.json"))
    assert byos_server.load_registry(sd)["devices"][MAC]["secret_sha256"] == SECRET


def test_devices_add_without_flag_output_and_layout_unchanged(sd, capsys):
    add_owner(sd)
    capsys.readouterr()
    assert add_device(sd) == 0
    assert capsys.readouterr().out == "registered %s\n" % MAC
    assert db_rows(sd)[0]["state_path"] == "."
    assert not os.path.exists(os.path.join(sd, "devices"))


def test_devices_add_second_default_is_refused_with_a_clear_message(sd, capsys):
    add_owner(sd)
    assert add_device(sd) == 0
    capsys.readouterr()
    assert add_device(sd, OTHER_MAC, SECRET2) == 2
    err = capsys.readouterr().err
    assert "--state-path auto" in err
    assert [r["mac"] for r in db_rows(sd)] == [MAC]
    assert OTHER_MAC not in byos_server.load_registry(sd)["devices"]
    assert not os.path.exists(os.path.join(sd, "devices"))


def test_devices_add_second_explicit_dot_is_refused_too(sd):
    add_owner(sd)
    assert add_device(sd) == 0
    assert add_device(sd, OTHER_MAC, SECRET2, "--state-path", ".") == 2
    assert len(db_rows(sd)) == 1


def test_devices_add_auto_records_the_live_mac_before_devices_appear(sd, monkeypatch):
    monkeypatch.setenv("SKYPANE_SIM_HARDWARE", "1")
    add_owner(sd)
    assert add_device(sd) == 0
    assert fleet_cli.device_dirs.read_live_macs(sd) is None
    assert add_device(sd, OTHER_MAC, SECRET2, "--hardware-type", "sim-ee02-clone",
                      "--state-path", "auto") == 0
    assert fleet_cli.device_dirs.read_live_macs(sd) == frozenset({MAC})


def test_devices_add_auto_rollback_removes_directory(sd, monkeypatch):
    monkeypatch.setenv("SKYPANE_SIM_HARDWARE", "1")
    add_owner(sd)
    byos_server.register_device(sd, MAC, SECRET)
    assert add_device(sd, MAC, SECRET, "--hardware-type", "sim-ee02-clone",
                      "--state-path", "auto") == 2
    assert db_rows(sd) == []
    devices = os.path.join(sd, "devices")
    assert not os.path.isdir(devices) or os.listdir(devices) == []


# ---- pending and retired frames ----------------------------------------

PENDING_MAC = "aa:bb:cc:dd:ee:50"
LEGACY_FILES = ("devices.json", "byos_state.json")


def legacy_bytes(sd):
    out = {}
    for name in LEGACY_FILES:
        path = os.path.join(sd, name)
        out[name] = read(path) if os.path.exists(path) else None
    return out


def pending_rows(sd):
    conn = fleet_db.connect_readonly(sd)
    try:
        return fleet_db.list_pending(conn)
    finally:
        conn.close()


def register_pending(sd, mac=PENDING_MAC, secret=SECRET):
    return run(sd, "devices", "register-pending", "--mac", mac,
               "--secret-sha256", secret)


def test_register_pending_writes_fleet_db_only(sd, capsys):
    add_owner(sd)
    before = legacy_bytes(sd)
    capsys.readouterr()
    assert register_pending(sd) == 0
    out = capsys.readouterr().out
    rows = pending_rows(sd)
    assert [r["mac"] for r in rows] == [PENDING_MAC]
    assert "pending id %s" % rows[0]["id"] in out
    assert fleet_cli.RESTART_CAUTION not in out
    assert legacy_bytes(sd) == before
    assert run(sd, "devices", "register-pending", "--mac", "aa:bb:cc:dd:ee:51",
               "--secret-sha256", "not-hex") == 2
    assert run(sd, "devices", "register-pending", "--mac", "aa:bb:cc:dd:ee:51",
               "--secret-sha256", SECRET.upper()) == 2
    assert len(pending_rows(sd)) == 1
    assert legacy_bytes(sd) == before


def test_register_pending_has_no_raw_secret_flag(sd):
    for flag in ("--secret-hex", "--raw-secret", "--provision-secret"):
        with pytest.raises(SystemExit) as excinfo:
            run(sd, "devices", "register-pending", "--mac", PENDING_MAC,
                flag, "ab" * 32)
        assert excinfo.value.code == 2
    # argparse treats --secret as an abbreviation of --secret-sha256, whose
    # value must be a hash; a raw secret of any other shape is refused.
    assert run(sd, "devices", "register-pending", "--mac", PENDING_MAC,
               "--secret", "abcd") == 2
    assert pending_rows(sd) == []


def test_pending_list_never_prints_secrets(sd, capsys):
    add_owner(sd)
    assert register_pending(sd) == 0
    conn = fleet_db.connect(sd)
    try:
        row = pending_rows(sd)[0]
        with fleet_db.transaction(conn):
            fleet_db.set_pending_token(conn, PENDING_MAC, TOKEN)
            fleet_db.issue_pending_code(
                conn, row["id"], "00" * 8, "ab" * 32, 4102444800)
    finally:
        conn.close()
    capsys.readouterr()
    assert run(sd, "devices", "pending-list") == 0
    out = capsys.readouterr().out
    assert row["id"] in out and PENDING_MAC in out and "pending" in out
    assert "code:live" in out
    assert TOKEN not in out and "ab" * 32 not in out
    assert not re.search(r"[0-9a-f]{64}", out)


def test_retire_and_reactivate_use_shared_operations(sd, capsys):
    add_owner(sd)
    assert add_device(sd) == 0
    assert add_device(sd, OTHER_MAC, SECRET2, "--state-path", "auto") == 0
    rows = {r["mac"]: r for r in db_rows(sd)}
    live_id, auto_id = rows[MAC]["id"], rows[OTHER_MAC]["id"]
    assert run(sd, "devices", "retire", "--id", live_id) != 0
    assert len(db_rows(sd)) == 2
    assert run(sd, "devices", "retire", "--id", auto_id) == 0
    assert [r["mac"] for r in db_rows(sd)] == [MAC]
    retired = pending_rows(sd)
    assert [(r["mac"], r["status"]) for r in retired] == [(OTHER_MAC, "retired")]
    assert os.path.isdir(os.path.join(sd, "devices", auto_id))
    assert run(sd, "devices", "reactivate", "--id", retired[0]["id"]) == 0
    assert pending_rows(sd)[0]["status"] == "pending"
    assert run(sd, "devices", "reactivate", "--id", "p_00000000") == 1


def test_remove_pending_deletes_row_and_pairing_dir_only(sd, capsys):
    add_owner(sd)
    assert add_device(sd) == 0
    assert register_pending(sd) == 0
    pending_id = pending_rows(sd)[0]["id"]
    pairing = os.path.join(sd, "pairing", pending_id)
    os.makedirs(pairing)
    legacy_before = legacy_bytes(sd)
    capsys.readouterr()
    assert run(sd, "devices", "remove", "--mac", PENDING_MAC) == 0
    out = capsys.readouterr().out
    assert fleet_cli.RESTART_CAUTION not in out
    assert pending_rows(sd) == []
    assert not os.path.exists(pairing)
    assert [r["mac"] for r in db_rows(sd)] == [MAC]
    assert legacy_bytes(sd) == legacy_before
    assert run(sd, "devices", "remove", "--mac", PENDING_MAC) == 1


def test_remove_pending_mirrors_when_legacy_knows_the_mac(sd, capsys):
    add_owner(sd)
    assert register_pending(sd) == 0
    byos_server.register_device(sd, PENDING_MAC, SECRET)
    capsys.readouterr()
    assert run(sd, "devices", "remove", "--mac", PENDING_MAC) == 0
    assert fleet_cli.RESTART_CAUTION in capsys.readouterr().out
    assert PENDING_MAC not in byos_server.load_registry(sd)["devices"]


def test_assign_wipes_a_non_live_frame_and_keeps_the_live_one(sd):
    add_owner(sd)
    add_owner(sd, "second@example.com", "user")
    assert add_device(sd) == 0
    assert add_device(sd, OTHER_MAC, SECRET2, "--state-path", "auto") == 0
    auto = {r["mac"]: r for r in db_rows(sd)}[OTHER_MAC]
    marker = os.path.join(sd, "devices", auto["id"], "old_owner_note.txt")
    with open(marker, "w") as fh:
        fh.write("previous owner data")
    assert run(sd, "devices", "assign", "--mac", OTHER_MAC,
               "--owner-email", "second@example.com") == 0
    assert not os.path.exists(marker)
    assert os.path.exists(os.path.join(
        sd, "devices", auto["id"], "panel.bin"))
    live_panel = os.path.join(sd, "panel.bin")
    live_note = os.path.join(sd, "live_note.txt")
    with open(live_note, "w") as fh:
        fh.write("live data")
    assert run(sd, "devices", "assign", "--mac", MAC,
               "--owner-email", "second@example.com") == 0
    assert os.path.exists(live_note)
    assert not os.path.exists(live_panel) or os.path.getsize(live_panel) > 0
    owners = {r["mac"]: r["owner_email"] for r in db_rows(sd)}
    assert set(owners.values()) == {"second@example.com"}
    conn = fleet_db.connect_readonly(sd)
    try:
        rows = conn.execute(
            "SELECT actor_label, action FROM audit_log "
            "WHERE action = 'device.reassign'").fetchall()
    finally:
        conn.close()
    assert len(rows) == 2 and {r["actor_label"] for r in rows} == {"cli"}
