#!/usr/bin/env python3
"""The companion reconciles photo files and rows once at start and keeps
serving when that fails."""
import os
import sqlite3

import companion_app_server
import photo_samples
import pytest
from photo_fleet import OWNER_EMAIL, seed_photo_fleet
from server import fleet_db, photo_purge, photo_quota, photo_store

from companion import app

NOW = 1_700_000_000


@pytest.fixture(autouse=True)
def _no_disk_floor(monkeypatch):
    monkeypatch.setattr(photo_quota, "MIN_FREE_DISK_BYTES", 0)


def _seed_with_photo(state):
    fleet = seed_photo_fleet(state)
    conn = fleet_db.connect(state)
    try:
        mgr = photo_store.authorize_manager(conn, fleet.device_id, fleet.owner_id)
        photo_store.add(mgr, conn, state, photo_samples.jpeg_bytes(), NOW)
        gone = photo_store.add(mgr, conn, state, photo_samples.jpeg_bytes(), NOW)
    finally:
        conn.close()
    device_dir = os.path.join(state, "photos", fleet.device_id)
    os.unlink(os.path.join(device_dir, gone + ".jpg"))  # row left without a file
    os.makedirs(os.path.join(state, "photos", "dev_vanished"))
    return fleet


def _rows(state):
    conn = fleet_db.connect_readonly(state)
    try:
        return conn.execute("SELECT COUNT(*) FROM device_photos").fetchone()[0]
    finally:
        conn.close()


def test_start_removes_orphans_before_serving(tmp_path):
    state = str(tmp_path / "state")
    os.makedirs(state)
    _seed_with_photo(state)
    server = companion_app_server.AppServer(state)
    server.start()
    try:
        assert not os.path.exists(os.path.join(state, "photos", "dev_vanished"))
        assert _rows(state) == 1
    finally:
        server.stop()


@pytest.mark.parametrize("error", [OSError("/secret/path"), sqlite3.Error("secret")])
def test_a_failing_sweep_prints_one_fixed_line_and_does_not_raise(
        tmp_path, monkeypatch, capsys, error):
    def boom(*_a, **_k):
        raise error

    monkeypatch.setattr(photo_purge, "sweep", boom)
    app._sweep_photos_at_start(str(tmp_path))
    out = capsys.readouterr().out
    assert out.strip() == "companion: photo sweep at start did not finish"
    assert "secret" not in out


def test_an_unusable_state_dir_is_skipped(tmp_path, capsys):
    app._sweep_photos_at_start(str(tmp_path / "missing" / "deeper"))
    assert capsys.readouterr().out.count("\n") <= 1


def test_companion_serves_and_has_no_photo_routes(tmp_path):
    state = str(tmp_path / "state")
    os.makedirs(state)
    fleet = _seed_with_photo(state)
    server = companion_app_server.AppServer(state)
    server.start()
    try:
        admin = companion_app_server.login(server)
        owner = companion_app_server.session_cookie_for_state_dir(
            state, email=OWNER_EMAIL, role="user")
        for cookie in (admin, owner):
            for path in ("/photos", "/devices/%s/photos" % fleet.device_id):
                status, _h, _b = companion_app_server.http_request(
                    server.url(path), cookie=cookie)
                assert status == 404, (path, status)
    finally:
        server.stop()
