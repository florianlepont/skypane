#!/usr/bin/env python3
"""What the live poll reads for a frame's position, pinned to literal values,
and proof that saving a frame's own position leaves every other frame's
reading, the schema and the poll's read path untouched."""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from server import detection, fleet_db, hardware  # noqa: E402

SECRET = "0" * 64
PARIS = "Europe/Paris"
RUNWAY_CFG = {"detection": {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}}
POSITION_CFG = {"detection": {"mode": "position", "radius_km": 10}}

# Literals captured from the read path before frame positions could be saved.
LEGACY_ORLY_ZONE_KEY = "48.7233|2.3794|5.0"
LFPG_ZONE_KEY = "49.009|2.5541|5.0"
OLD_POSITION = (48.7262, 2.3652)
OLD_POSITION_ZONE_KEY = "48.73|2.37|5.4"
NEW_POSITION = (43.2965, 5.3698)
NEW_POSITION_ZONE_KEY = "43.3|5.37|5.4"
NO_POSITION_ZONE_KEY = "46.6|2.5|1.0"


@pytest.fixture(autouse=True)
def _no_kill_switch(monkeypatch):
    monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path)


def _poll_view(state_dir, device_id, cfg):
    """The coordinates and spec the poll derives, through its read-only helpers."""
    conn = fleet_db.connect_readonly(state_dir)
    try:
        location = fleet_db.device_coordinates(conn).get(device_id)
    finally:
        conn.close()
    return location, detection.spec_for(cfg, location)


def _fleet(state_dir):
    conn = fleet_db.connect(state_dir)
    uid = fleet_db.add_user(conn, "a@b.c", "user")
    old = fleet_db.add_location(
        conn, "Shared", OLD_POSITION[0], OLD_POSITION[1], PARIS, owner_user_id=uid
    )
    a = fleet_db.add_device(
        conn, "aa:bb:cc:dd:ee:01", SECRET, hardware.LEGACY_KEY, uid, location_id=old
    )
    b = fleet_db.add_device(
        conn, "aa:bb:cc:dd:ee:02", SECRET, hardware.LEGACY_KEY, uid,
        location_id=old, state_path="auto",
    )
    c = fleet_db.add_device(
        conn, "aa:bb:cc:dd:ee:03", SECRET, hardware.LEGACY_KEY, uid, state_path="auto"
    )
    return conn, uid, a, b, c


def test_unsaved_frames_read_fixed_values(state_dir):
    conn, _uid, a, _b, c = _fleet(state_dir)
    conn.close()
    location, spec = _poll_view(state_dir, a, POSITION_CFG)
    assert location == OLD_POSITION
    assert (spec.mode, spec.display_id, spec.zone.key) == (
        "position", "position:10", OLD_POSITION_ZONE_KEY)
    assert spec.zone.radius_nm == 5.4
    location, spec = _poll_view(state_dir, c, POSITION_CFG)
    assert location is None and spec.no_location is True
    assert spec.zone.key == NO_POSITION_ZONE_KEY
    for cfg in ({}, {"tracked_runway": "3"}):
        location, spec = _poll_view(state_dir, c, cfg)
        assert location is None
        assert (spec.mode, spec.display_id, spec.zone.key) == (
            "runway", "3", LEGACY_ORLY_ZONE_KEY)
        assert spec.zone.radius_nm == 5.0
        assert spec.geofence["center"] == {"lat": 48.7233, "lon": 2.3794}
        assert spec.geofence["bbox"] == {
            "lat_min": 48.712, "lat_max": 48.734, "lon_min": 2.325, "lon_max": 2.435}
    _, spec = _poll_view(state_dir, c, RUNWAY_CFG)
    assert (spec.display_id, spec.zone.key) == ("LFPG:08L/26R", LFPG_ZONE_KEY)


def test_saving_one_frame_leaves_the_sharing_frame_unmoved(state_dir):
    conn, uid, a, b, _c = _fleet(state_dir)
    fleet_db.save_frame_position(
        conn, a, "Marseille", NEW_POSITION[0], NEW_POSITION[1], PARIS, uid, False)
    conn.close()
    location_a, spec_a = _poll_view(state_dir, a, POSITION_CFG)
    location_b, spec_b = _poll_view(state_dir, b, POSITION_CFG)
    assert location_a == NEW_POSITION
    assert spec_a.zone.key == NEW_POSITION_ZONE_KEY
    assert location_b == OLD_POSITION
    assert spec_b.zone.key == OLD_POSITION_ZONE_KEY


def test_runway_mode_ignores_a_saved_position(state_dir):
    conn, uid, a, _b, c = _fleet(state_dir)
    _, before = _poll_view(state_dir, c, RUNWAY_CFG)
    fleet_db.save_frame_position(
        conn, c, "Lyon", 45.76, 4.84, PARIS, uid, False)
    fleet_db.save_frame_position(
        conn, a, "Marseille", NEW_POSITION[0], NEW_POSITION[1], PARIS, uid, False)
    conn.close()
    for dev in (a, c):
        location, after = _poll_view(state_dir, dev, RUNWAY_CFG)
        assert location is not None
        assert (after.mode, after.display_id, after.zone.key) == (
            "runway", "LFPG:08L/26R", LFPG_ZONE_KEY)
        assert after.geofence == before.geofence
    for dev in (a, c):
        _, legacy = _poll_view(state_dir, dev, {})
        assert legacy.zone.key == LEGACY_ORLY_ZONE_KEY


def test_poll_read_only_connection_sees_a_saved_row(state_dir):
    conn, uid, _a, _b, c = _fleet(state_dir)
    fleet_db.save_frame_position(conn, c, "Lyon", 45.76, 4.84, PARIS, uid, False)
    ro = fleet_db.connect_readonly(state_dir)
    try:
        assert fleet_db.device_coordinates(ro)[c] == (45.76, 4.84)
        with pytest.raises(Exception, match="readonly"):
            ro.execute("DELETE FROM locations")
    finally:
        ro.close()
        conn.close()


def _schema(conn):
    rows = conn.execute(
        "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
    ).fetchall()
    return [tuple(r) for r in rows], conn.execute("PRAGMA user_version").fetchone()[0]


def test_schema_is_unchanged_by_saving_positions(state_dir):
    conn, uid, a, _b, c = _fleet(state_dir)
    before = _schema(conn)
    fleet_db.save_frame_position(conn, a, "One", 45.0, 4.0, PARIS, uid, False)
    fleet_db.save_frame_position(conn, a, "Two", 45.5, 4.5, PARIS, uid, False)
    fleet_db.save_frame_position(conn, c, "Three", 44.0, 3.0, PARIS, uid, False)
    assert _schema(conn) == before
    tables = {r[1] for r in before[0] if r[0] == "table"}
    assert "locations" in tables
    cols = {r[1] for r in conn.execute("PRAGMA table_info(devices)")}
    assert "location_id" in cols
    loc_cols = [r[1] for r in conn.execute("PRAGMA table_info(locations)")]
    assert loc_cols == ["id", "name", "latitude", "longitude", "timezone", "owner_user_id"]
    assert before[1] == fleet_db.SCHEMA_VERSION
    conn.close()
