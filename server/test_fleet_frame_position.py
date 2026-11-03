#!/usr/bin/env python3
"""Tests for fleet_db.save_frame_position / frame_position: a private row per
frame, in-place updates, no-op saves and copy-on-write for shared rows."""
import pytest

import server.fleet_db as fleet_db
from server import hardware

SECRET = "0" * 64
MAC_A = "aa:bb:cc:dd:ee:01"
MAC_B = "aa:bb:cc:dd:ee:02"
PARIS = "Europe/Paris"


@pytest.fixture
def conn():
    c = fleet_db.connect_memory()
    yield c
    c.close()


def _frame(conn, owner, mac=MAC_A, **kw):
    return fleet_db.add_device(conn, mac, SECRET, hardware.LEGACY_KEY, owner, **kw)


def _save(conn, dev, uid, label="Home", lat=48.7262, lon=2.3652, tz=PARIS, admin=False):
    return fleet_db.save_frame_position(conn, dev, label, lat, lon, tz, uid, admin)


def _rows(conn):
    return [tuple(r) for r in conn.execute("SELECT * FROM locations ORDER BY id")]


def test_first_save_creates_private_row_linked_to_frame(conn):
    uid = fleet_db.add_user(conn, "a@b.c", "user")
    dev = _frame(conn, uid)
    assert fleet_db.frame_position(conn, dev) is None
    loc, changed = _save(conn, dev, uid, label="  Kitchen  ", lat=48.72619, lon=2.36524)
    assert changed is True
    row = fleet_db.get_location(conn, loc)
    assert (row["name"], row["latitude"], row["longitude"], row["timezone"]) == (
        "Kitchen", 48.7262, 2.3652, PARIS)
    assert row["owner_user_id"] == uid
    assert fleet_db.get_device(conn, dev)["location_id"] == loc
    pos = fleet_db.frame_position(conn, dev)
    assert pos == {"id": loc, "name": "Kitchen", "latitude": 48.7262,
                   "longitude": 2.3652, "timezone": PARIS, "shared": False}


def test_blank_label_uses_default_name(conn):
    uid = fleet_db.add_user(conn, "a@b.c", "user")
    dev = _frame(conn, uid)
    loc, _ = _save(conn, dev, uid, label="   ")
    assert fleet_db.get_location(conn, loc)["name"] == "Frame position"


def test_second_save_updates_in_place_and_same_values_write_nothing(conn):
    uid = fleet_db.add_user(conn, "a@b.c", "user")
    dev = _frame(conn, uid)
    loc, _ = _save(conn, dev, uid)
    again, changed = _save(conn, dev, uid, lat=48.8)
    assert (again, changed) == (loc, True)
    assert fleet_db.get_location(conn, loc)["latitude"] == 48.8
    before = _rows(conn)
    changes_before = conn.total_changes
    same, changed = _save(conn, dev, uid, lat=48.8)
    assert (same, changed) == (loc, False)
    assert _rows(conn) == before
    assert conn.total_changes == changes_before


def test_shared_row_is_copied_not_edited(conn):
    uid = fleet_db.add_user(conn, "a@b.c", "user")
    old = fleet_db.add_location(conn, "Shared", 48.0, 2.0, PARIS, owner_user_id=uid)
    a = _frame(conn, uid, MAC_A, location_id=old)
    b = _frame(conn, uid, MAC_B, location_id=old, state_path="auto")
    assert fleet_db.frame_position(conn, a)["shared"] is True
    loc, changed = _save(conn, a, uid, lat=49.0, lon=3.0)
    assert changed and loc != old
    assert fleet_db.get_device(conn, a)["location_id"] == loc
    assert fleet_db.get_device(conn, b)["location_id"] == old
    row = fleet_db.get_location(conn, old)
    assert (row["name"], row["latitude"], row["longitude"]) == ("Shared", 48.0, 2.0)
    assert fleet_db.frame_position(conn, a)["shared"] is False


@pytest.mark.parametrize("owner_kind", ["other", "none"])
def test_row_owned_by_someone_else_is_copied(conn, owner_kind):
    uid = fleet_db.add_user(conn, "a@b.c", "user")
    other = fleet_db.add_user(conn, "o@b.c", "user")
    owner = other if owner_kind == "other" else None
    old = fleet_db.add_location(conn, "Theirs", 48.0, 2.0, PARIS, owner_user_id=owner)
    dev = _frame(conn, uid, location_id=old)
    loc, changed = _save(conn, dev, uid)
    assert changed and loc != old
    assert fleet_db.get_location(conn, loc)["owner_user_id"] == uid
    assert fleet_db.get_location(conn, old)["name"] == "Theirs"
    assert fleet_db.get_device(conn, dev)["location_id"] == loc


@pytest.mark.parametrize(
    "label,lat,lon,tz",
    [
        ("x" * 61, 48.0, 2.0, PARIS),
        ("bad\x07", 48.0, 2.0, PARIS),
        ("new\nline", 48.0, 2.0, PARIS),
        ("ok", 91.0, 2.0, PARIS),
        ("ok", 48.0, 181.0, PARIS),
        ("ok", 48.0, 2.0, "Mars/Base"),
    ],
)
def test_invalid_input_writes_nothing(conn, label, lat, lon, tz):
    uid = fleet_db.add_user(conn, "a@b.c", "user")
    dev = _frame(conn, uid)
    with pytest.raises(ValueError):
        _save(conn, dev, uid, label=label, lat=lat, lon=lon, tz=tz)
    assert _rows(conn) == []
    assert fleet_db.get_device(conn, dev)["location_id"] is None


def test_label_of_exactly_60_characters_is_accepted(conn):
    uid = fleet_db.add_user(conn, "a@b.c", "user")
    dev = _frame(conn, uid)
    loc, _ = _save(conn, dev, uid, label="é" * 60)
    assert fleet_db.get_location(conn, loc)["name"] == "é" * 60


def test_unknown_device_raises_and_writes_nothing(conn):
    uid = fleet_db.add_user(conn, "a@b.c", "admin")
    with pytest.raises(ValueError):
        _save(conn, "d_nope", uid, admin=True)
    assert _rows(conn) == []


def test_stranger_is_refused_and_co_manager_and_admin_allowed(conn):
    owner = fleet_db.add_user(conn, "a@b.c", "user")
    stranger = fleet_db.add_user(conn, "s@b.c", "user")
    co = fleet_db.add_user(conn, "c@b.c", "user")
    admin = fleet_db.add_user(conn, "m@b.c", "admin")
    dev = _frame(conn, owner)
    fleet_db.add_co_manager(conn, dev, co, owner)
    with pytest.raises(PermissionError):
        _save(conn, dev, stranger)
    with pytest.raises(PermissionError):
        _save(conn, dev, None)
    assert _rows(conn) == []
    loc, _ = _save(conn, dev, co)
    assert fleet_db.get_location(conn, loc)["owner_user_id"] == owner
    _, changed = _save(conn, dev, admin, lat=47.0, admin=True)
    assert changed


def test_failed_link_rolls_back_the_new_row(conn, monkeypatch):
    uid = fleet_db.add_user(conn, "a@b.c", "user")
    dev = _frame(conn, uid)

    def boom(*a, **k):
        raise PermissionError("no")

    monkeypatch.setattr(fleet_db, "set_device_location_checked", boom)
    with pytest.raises(PermissionError):
        _save(conn, dev, uid)
    assert _rows(conn) == []
    assert not conn.in_transaction
