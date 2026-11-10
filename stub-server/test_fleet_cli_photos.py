#!/usr/bin/env python3
"""Photo cleanup through the fleet CLI and the byos mirror."""
import importlib.util
import os
import sys

import pytest

import photo_samples
from photo_fleet import PHOTO_DEVICE_MAC, seed_photo_fleet
from server import fleet_db, photo_purge, photo_quota, photo_store

HERE = os.path.dirname(os.path.abspath(__file__))
NOW = 1_700_000_000


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, HERE)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(HERE)
    return module


fleet_cli = _load("fleet_cli_photos_under_test", os.path.join(HERE, "fleet_cli.py"))
byos_server = fleet_cli.byos_server


@pytest.fixture(autouse=True)
def _no_disk_floor(monkeypatch):
    monkeypatch.delenv("SKYPANE_SIM_HARDWARE", raising=False)
    monkeypatch.setattr(photo_quota, "MIN_FREE_DISK_BYTES", 0)


@pytest.fixture
def fleet(tmp_path):
    state = str(tmp_path)
    seeded = seed_photo_fleet(state)
    conn = fleet_db.connect(state)
    try:
        mgr = photo_store.authorize_manager(conn, seeded.device_id, seeded.owner_id)
        for _ in range(2):
            photo_store.add(mgr, conn, state, photo_samples.jpeg_bytes(), NOW)
    finally:
        conn.close()
    return state, seeded


def _photo_dir(state, seeded):
    return os.path.join(state, "photos", seeded.device_id)


def _photo_rows(state):
    conn = fleet_db.connect_readonly(state)
    try:
        return conn.execute("SELECT COUNT(*) FROM device_photos").fetchone()[0]
    finally:
        conn.close()


def run(state, *argv):
    return fleet_cli.main(["--state-dir", state, *argv])


def test_devices_remove_leaves_no_photo_file_or_row(fleet, capsys):
    state, seeded = fleet
    assert os.path.isdir(_photo_dir(state, seeded))
    assert run(state, "devices", "remove", "--mac", PHOTO_DEVICE_MAC) == 0
    out = capsys.readouterr().out
    assert "removed %s" % PHOTO_DEVICE_MAC in out
    assert fleet_cli.RESTART_CAUTION in out
    assert not os.path.exists(_photo_dir(state, seeded))
    assert _photo_rows(state) == 0


def test_byos_mirror_remove_leaves_no_photo_file_or_row(fleet):
    state, seeded = fleet
    assert byos_server.mirror_to_fleet(state, "remove", PHOTO_DEVICE_MAC) is None
    assert not os.path.exists(_photo_dir(state, seeded))
    assert _photo_rows(state) == 0


def test_a_sweep_failure_does_not_fail_the_removal(fleet, monkeypatch, capsys):
    state, seeded = fleet

    def boom(*_a, **_k):
        raise OSError("disk gone")

    monkeypatch.setattr(photo_purge, "sweep", boom)
    assert run(state, "devices", "remove", "--mac", PHOTO_DEVICE_MAC) == 0
    assert "removed %s" % PHOTO_DEVICE_MAC in capsys.readouterr().out
    assert byos_server.mirror_to_fleet(state, "remove", PHOTO_DEVICE_MAC) is None


def test_photos_sweep_with_nothing_to_do_prints_zeros(tmp_path, capsys):
    assert run(str(tmp_path), "photos", "sweep") == 0
    assert capsys.readouterr().out.strip() == (
        "swept: dirs=0 files=0 temps=0 rows=0 links=0")


def test_photos_sweep_prints_counts_only(fleet, capsys):
    state, seeded = fleet
    orphan = os.path.join(state, "photos", "dev_orphanedname")
    os.makedirs(orphan)
    with open(os.path.join(orphan, "secret-name.jpg"), "wb") as fh:
        fh.write(b"x")
    assert run(state, "photos", "sweep") == 0
    out = capsys.readouterr().out
    assert out.strip() == "swept: dirs=1 files=0 temps=0 rows=0 links=0"
    for leaked in ("orphanedname", "secret-name", state, seeded.device_id):
        assert leaked not in out
    assert not os.path.exists(orphan)
    assert os.path.isdir(_photo_dir(state, seeded))
