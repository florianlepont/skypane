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
    assert add_device(sd, OTHER_MAC, SECRET2) == 0
    original = read(byos_server.registry_path(sd))
    assert add_device(sd, "aa:bb:cc:dd:ee:03", SECRET) == 0
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


def test_devices_add_auto_rollback_removes_directory(sd, monkeypatch):
    monkeypatch.setenv("SKYPANE_SIM_HARDWARE", "1")
    add_owner(sd)
    byos_server.register_device(sd, MAC, SECRET)
    assert add_device(sd, MAC, SECRET, "--hardware-type", "sim-ee02-clone",
                      "--state-path", "auto") == 2
    assert db_rows(sd) == []
    devices = os.path.join(sd, "devices")
    assert not os.path.isdir(devices) or os.listdir(devices) == []
