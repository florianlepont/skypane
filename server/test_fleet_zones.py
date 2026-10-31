"""Zone identity, serving order and device activity rules."""

import random

import pytest

from server.fleet_zones import (
    INACTIVE_AFTER_S,
    Zone,
    ZoneEntry,
    device_is_active,
    order_zones,
    zone_from_geofence,
)

NOW = 1_800_000_000.0
DAY = 86400.0


def test_identical_numbers_make_equal_zones_with_equal_keys():
    a, b = Zone(48.72, 2.38, 5.0), Zone(48.72, 2.38, 5.0)
    assert a == b and hash(a) == hash(b) and a.key == b.key
    assert len({a, b}) == 1


@pytest.mark.parametrize("field", ["lat", "lon", "radius_nm"])
def test_tiny_difference_gives_a_different_key(field):
    base = {"lat": 48.72, "lon": 2.38, "radius_nm": 5.0}
    other = dict(base, **{field: base[field] + 1e-6})
    assert Zone(**base).key != Zone(**other).key


def test_negative_zero_and_zero_share_a_key():
    assert Zone(0.0, 0.0, 1.0).key == Zone(-0.0, -0.0, 1.0).key


@pytest.mark.parametrize(
    "args",
    [
        (float("nan"), 2.0, 5.0),
        (48.0, float("inf"), 5.0),
        (48.0, 2.0, float("inf")),
        (90.5, 2.0, 5.0),
        (-90.5, 2.0, 5.0),
        (48.0, 180.5, 5.0),
        (48.0, -180.5, 5.0),
        (48.0, 2.0, 0.0),
        (48.0, 2.0, -3.0),
        ("48", 2.0, 5.0),
        (True, 2.0, 5.0),
    ],
)
def test_invalid_zone_is_rejected(args):
    with pytest.raises(ValueError):
        Zone(*args)


def test_zone_from_geofence_reads_centre_and_radius():
    zone = zone_from_geofence({"center": {"lat": 48.7, "lon": 2.4}, "radius_nm": 6})
    assert zone == Zone(48.7, 2.4, 6.0)


@pytest.mark.parametrize(
    "geofence",
    [None, {}, {"center": {"lat": 1}, "radius_nm": 3}, {"center": 5, "radius_nm": 3},
     {"center": {"lat": 1, "lon": 2}}, {"center": {"lat": 99, "lon": 2}, "radius_nm": 3}],
)
def test_malformed_geofence_raises_value_error(geofence):
    with pytest.raises(ValueError):
        zone_from_geofence(geofence)


def _entries():
    zones = [Zone(40.0 + i, 2.0, 5.0) for i in range(6)]
    return zones, [ZoneEntry(z, has_live=(i == 4)) for i, z in enumerate(zones)]


def test_live_zone_first_then_oldest_served_with_never_served_oldest():
    zones, entries = _entries()
    last_served = {zones[0].key: 300.0, zones[1].key: 100.0, zones[2].key: 200.0, zones[4].key: 999.0}
    ordered = order_zones(entries, last_served)
    assert ordered == [zones[4], zones[3], zones[5], zones[1], zones[2], zones[0]]


def test_order_is_deterministic_for_any_input_order():
    zones, entries = _entries()
    last_served = {zones[0].key: 50.0, zones[1].key: 50.0}
    expected = order_zones(entries, last_served)
    rng = random.Random(7)
    for _ in range(20):
        shuffled = entries[:]
        rng.shuffle(shuffled)
        assert order_zones(shuffled, last_served) == expected


def test_duplicate_zone_entries_collapse_and_keep_live_flag():
    a, b = Zone(48.0, 2.0, 5.0), Zone(49.0, 2.0, 5.0)
    ordered = order_zones([ZoneEntry(b), ZoneEntry(a), ZoneEntry(a, has_live=True)], {a.key: 10.0, b.key: 1.0})
    assert ordered == [a, b]


def test_inactive_threshold_is_seven_days():
    assert INACTIVE_AFTER_S == 7 * 86400


def test_live_frame_is_always_active():
    assert device_is_active(True, None, None, NOW)
    assert device_is_active(True, NOW - 30 * DAY, NOW - 30 * DAY, NOW)


def test_recent_check_in_is_active_and_old_check_in_is_not():
    assert device_is_active(False, NOW - 90 * DAY, NOW - 6 * DAY, NOW)
    assert not device_is_active(False, NOW - 90 * DAY, NOW - 8 * DAY, NOW)
    assert not device_is_active(False, NOW - 90 * DAY, NOW - 7 * DAY, NOW)


def test_new_check_in_makes_a_skipped_device_active_again():
    assert not device_is_active(False, NOW - 90 * DAY, NOW - 20 * DAY, NOW)
    assert device_is_active(False, NOW - 90 * DAY, NOW - 1.0, NOW)


def test_new_device_without_check_in_is_exempt_for_seven_days():
    assert device_is_active(False, NOW - 6 * DAY, None, NOW)
    assert not device_is_active(False, NOW - 7 * DAY, None, NOW)
    assert not device_is_active(False, NOW - 30 * DAY, None, NOW)


def test_no_timestamps_at_all_is_inactive():
    assert not device_is_active(False, None, None, NOW)


def test_future_timestamps_count_as_recent():
    assert device_is_active(False, NOW - 90 * DAY, NOW + 10 * DAY, NOW)
    assert device_is_active(False, NOW + 10 * DAY, None, NOW)
