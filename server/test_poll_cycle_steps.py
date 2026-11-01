"""Unit tests for the named steps run_once's split introduces in
server/poll_cycle.py - CycleContext and its step functions:

  * decide_hold() - the pure battery_empty > display_off > quiet_hours
    precedence, isolated from any I/O
  * publish_canvas() - the one render -> pack -> write -> gallery
    sequence every former "publish copy" now shares
  * the live path's own step call order (detect_flight,
    load_display_slots, update_battery_low, advance_display_queue,
    render_and_publish, record, persist, log_cycle), and the hold path's
    restricted call surface (never detects, publishes at most once)

Every assertion is a return value, a CycleContext field, a recorded call
order, or a gallery/panel.bin write - never source text.
"""
import dataclasses
import hashlib
import json
import os

import pytest

import server.device_config as device_config
import server.firmware_registry as firmware_registry
import server.plane.enrich as enrich
import server.plane.render as render
from server import hardware
import server.poll_cycle as poll_cycle
import server.zone_fetch as zone_fetch


# --- decide_hold(): pure precedence, no I/O ---------------------------------


@pytest.mark.parametrize(
    "battery_critical, display_enabled, quiet_remaining, expected",
    [
        (True, False, 100, "battery_empty"),
        (False, False, 100, "display_off"),
        (False, True, 100, "quiet_hours"),
        (False, True, None, None),
        # quiet_remaining=0 is a real, non-None value - `is not None`
        # reads it the same as any other in-progress countdown.
        (False, True, 0, "quiet_hours"),
    ],
)
def test_decide_hold_precedence(battery_critical, display_enabled, quiet_remaining, expected):
    assert poll_cycle.decide_hold(battery_critical, display_enabled, quiet_remaining) == expected


def test_decide_hold_battery_empty_outranks_display_off_and_quiet_hours():
    """battery_critical=True wins even when display_off/quiet_hours would
    also independently apply - the flat-pack priority the module's own
    docstring describes."""
    assert poll_cycle.decide_hold(True, False, 100) == "battery_empty"


def test_decide_hold_display_off_outranks_quiet_hours():
    assert poll_cycle.decide_hold(False, False, 100) == "display_off"


# --- publish_canvas(): the one render -> pack -> write -> gallery path -----


def _ctx(state_dir, now_iso="2026-09-27T12:00:00+00:00"):
    return poll_cycle.CycleContext(
        state_dir=state_dir, snapshot=None, geofence=None, caddy_log=None, now_iso=now_iso)


def _gallery_pngs(state_dir):
    gallery_dir = os.path.join(state_dir, poll_cycle.GALLERY_DIRNAME)
    if not os.path.isdir(gallery_dir):
        return []
    return [name for name in os.listdir(gallery_dir) if name.endswith(".png")]


def test_publish_canvas_first_write_returns_true_and_writes_one_gallery_entry_named_from_now_iso(tmp_path):
    state_dir = str(tmp_path)
    ctx = _ctx(state_dir, now_iso="2026-09-27T08:30:00+00:00")
    canvas = render.build_canvas(None, "empty")

    changed = poll_cycle.publish_canvas(ctx, canvas)

    assert changed is True
    assert ctx.panel_changed is True
    assert os.path.exists(os.path.join(state_dir, "panel.bin"))
    assert _gallery_pngs(state_dir) == ["2026-09-27T08-30-00+00-00.png"]


def test_publish_canvas_unchanged_panel_returns_false_and_writes_no_new_gallery_entry(tmp_path):
    state_dir = str(tmp_path)
    ctx = _ctx(state_dir)
    canvas = render.build_canvas(None, "empty")

    poll_cycle.publish_canvas(ctx, canvas)  # first write: changed
    before = _gallery_pngs(state_dir)

    changed = poll_cycle.publish_canvas(ctx, canvas)  # identical canvas: unchanged

    assert changed is False
    assert ctx.panel_changed is False
    assert _gallery_pngs(state_dir) == before
    assert len(before) == 1


def test_publish_canvas_a_later_changed_canvas_still_returns_true(tmp_path):
    state_dir = str(tmp_path)
    ctx = _ctx(state_dir, now_iso="2026-09-27T09:00:00+00:00")
    empty_canvas = render.build_canvas(None, "empty")
    battery_empty_canvas = render.build_canvas(None, "battery_empty")

    poll_cycle.publish_canvas(ctx, empty_canvas)
    ctx.now_iso = "2026-09-27T09:05:00+00:00"

    changed = poll_cycle.publish_canvas(ctx, battery_empty_canvas)

    assert changed is True
    assert ctx.panel_changed is True
    assert len(_gallery_pngs(state_dir)) == 2


# --- live-path step order, and the hold path's restricted call surface -----


_LIVE_STEP_NAMES = (
    "detect_flight", "load_display_slots", "update_battery_low",
    "advance_display_queue", "render_and_publish", "record", "persist", "log_cycle",
)


def test_live_path_calls_its_named_steps_in_order(tmp_path, monkeypatch):
    """Spies on every live-path step (wrapping, never replacing, so
    behaviour still runs for real) and asserts the exact call order the
    module's own run_once() docstring promises."""
    order = []

    def _wrap(name):
        real = getattr(poll_cycle, name)

        def spy(*args, **kwargs):
            order.append(name)
            return real(*args, **kwargs)

        monkeypatch.setattr(poll_cycle, name, spy)

    for name in _LIVE_STEP_NAMES:
        _wrap(name)

    # An empty-sky snapshot (no live network call - detect_flight takes
    # the injected-snapshot path) still runs every live step once, ending
    # in the empty-state render branch on a fresh state_dir.
    poll_cycle.run_once(snapshot={}, state_dir=str(tmp_path))

    assert order == list(_LIVE_STEP_NAMES)


def test_hold_path_never_detects_and_publishes_at_most_once(tmp_path, monkeypatch):
    """The hold path (display_off here) must never touch detect_flight -
    an off period with no scheduled end must not query the aggregators
    unbounded - and repaints at most once per cycle (once on entry, never
    again on an unchanged repeat)."""
    state_dir = str(tmp_path)
    device_config.save_device_config(state_dir, display_enabled=False)

    detect_calls = []
    monkeypatch.setattr(poll_cycle, "detect_flight", lambda ctx: detect_calls.append(ctx))

    publish_calls = []
    real_publish = poll_cycle.publish_canvas

    def _spy_publish(ctx, canvas):
        publish_calls.append(canvas)
        return real_publish(ctx, canvas)

    monkeypatch.setattr(poll_cycle, "publish_canvas", _spy_publish)

    poll_cycle.run_once(state_dir=state_dir)  # hold entry: repaints once
    poll_cycle.run_once(state_dir=state_dir)  # hold repeat: no boundary crossed

    assert detect_calls == []
    assert len(publish_calls) == 1


# --- the poll loop reconciles every hardware type ---------------------------

_RECONCILE_NOW = "2026-10-01T00:00:00+00:00"
_RECONCILE_VERSION = "fw-v1.1.0"


def _scheduled_document(hardware_type):
    sha = hashlib.sha256(b"image").hexdigest()
    doc = firmware_registry._default_registry(hardware_type)
    doc["releases"] = [{
        "version": _RECONCILE_VERSION, "sha256": sha, "size": 5, "released_at": "d",
        "published_at": _RECONCILE_NOW, "commit": "a" * 40, "notes": [], "bench": False,
        "installed_at": [],
    }]
    doc["schedule"] = {
        "id": "sid-" + hardware_type[:3], "version": _RECONCILE_VERSION, "sha256": sha,
        "scheduled_at": _RECONCILE_NOW, "state": "scheduled", "attempts": 0,
        "failed_at": None, "last_result": None,
    }
    return doc


def _installed_report(hardware_type):
    event = {"seq": 2, "at": _RECONCILE_NOW, "kind": "result",
             "schedule_id": "sid-" + hardware_type[:3], "token": "installed",
             "version": _RECONCILE_VERSION}
    return {"schema": 1, "next_seq": 3, "devices": {"aa:bb:cc:dd:ee:02": {
        "fw_version": _RECONCILE_VERSION, "reported_at": _RECONCILE_NOW,
        "hardware_type": hardware_type, "events": [event]}}}


def test_reconcile_step_closes_only_the_reporting_types_schedule(tmp_path, monkeypatch):
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")
    state = str(tmp_path)
    other = hardware.SIM_CLONE_KEY
    for key in (hardware.LEGACY_KEY, other):
        with firmware_registry.registry_lock(state):
            firmware_registry._save_registry(state, _scheduled_document(key), key)
    with open(firmware_registry.device_report_path(state), "w") as fh:
        json.dump(_installed_report(other), fh)
    legacy_path = firmware_registry.registry_path(state)
    with open(legacy_path, "rb") as fh:
        legacy_before = fh.read()

    poll_cycle._reconcile_firmware(state, _RECONCILE_NOW)

    assert firmware_registry.load_registry(state, other)["schedule"] is None
    with open(legacy_path, "rb") as fh:
        assert fh.read() == legacy_before


def test_reconcile_step_with_only_the_legacy_type_closes_its_schedule(tmp_path):
    state = str(tmp_path)
    with firmware_registry.registry_lock(state):
        firmware_registry._save_registry(state, _scheduled_document(hardware.LEGACY_KEY))
    with open(firmware_registry.device_report_path(state), "w") as fh:
        json.dump(_installed_report(hardware.LEGACY_KEY), fh)

    poll_cycle._reconcile_firmware(state, _RECONCILE_NOW)

    assert firmware_registry.load_registry(state)["schedule"] is None
    assert not [n for n in os.listdir(os.path.join(state, "firmware"))
                if n.startswith("registry.") and n.endswith(".json") and n != "registry.json"]


# --- detect_flight over a shared ZoneFetch ----------------------------------


def _aircraft(hex_code, callsign):
    """An aircraft climbing out inside the runway-3 box of
    adsb-test/runway3.json."""
    return {
        "hex": hex_code, "flight": callsign, "lat": 48.7233, "lon": 2.3794,
        "alt_baro": 450, "gs": 137.1, "baro_rate": 2400, "seen_pos": 1.0,
    }


_GEOFENCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "adsb-test", "runway3.json")


def _cycle(tmp_path, **kwargs):
    kwargs.setdefault("geofence", _GEOFENCE)
    return poll_cycle.run_once(state_dir=str(tmp_path), **kwargs)


@pytest.fixture(autouse=True)
def _no_real_route_lookup(monkeypatch):
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (404, None))


def test_zone_fetch_with_both_providers_agreeing_selects_the_corroborated_aircraft(tmp_path, monkeypatch):
    def _no_provider_call(*args, **kwargs):
        raise AssertionError("a shared zone result must not trigger a provider call")

    monkeypatch.setattr(poll_cycle.detect, "query_provider", _no_provider_call)
    fetched = zone_fetch.ZoneFetch(
        results=(("adsbfi", [_aircraft("aaaaaa", "AFR1234 ")]), ("adsblol", [_aircraft("aaaaaa", "AFR1234 ")])),
        queried=("adsbfi", "adsblol"))

    result = _cycle(tmp_path, zone_fetch=fetched)

    assert result["flight"]["hex"] == "aaaaaa"
    assert result["flight"]["corroborated"] is True
    assert result["source_fault"] is False
    assert not os.path.exists(os.path.join(str(tmp_path), "request_ledger.json"))


def _tree_bytes(directory):
    """Every regular file under a directory, by relative path."""
    found = {}
    for root, _dirs, names in os.walk(directory):
        for name in names:
            if name.endswith((".lock", "-wal", "-shm")):
                continue
            path = os.path.join(root, name)
            with open(path, "rb") as handle:
                found[os.path.relpath(path, directory)] = handle.read()
    return found


def test_zone_fetch_for_another_zone_is_refused_and_leaves_the_device_untouched(tmp_path):
    answered = zone_fetch.ZoneFetch(
        results=(("adsbfi", [_aircraft("aaaaaa", "AFR1234 ")]),
                 ("adsblol", [_aircraft("aaaaaa", "AFR1234 ")])),
        queried=("adsbfi", "adsblol"))
    _cycle(tmp_path, zone_fetch=answered)
    poll_state = os.path.join(str(tmp_path), "poll_state.json")
    with open(poll_state, "rb") as handle:
        state_before = handle.read()
    panel_before = _tree_bytes(str(tmp_path)).get("panel.bin")

    foreign = dataclasses.replace(answered, zone_key="49.0|2.5|20.0")
    with pytest.raises(poll_cycle.StaleZone):
        _cycle(tmp_path, zone_fetch=foreign)

    with open(poll_state, "rb") as handle:
        assert handle.read() == state_before
    assert _tree_bytes(str(tmp_path)).get("panel.bin") == panel_before


def test_zone_fetch_stamped_with_the_devices_own_zone_is_used(tmp_path):
    own = poll_cycle.detection.spec_for(
        {}, legacy_geofence_path=_GEOFENCE).zone.key
    fetched = zone_fetch.ZoneFetch(
        results=(("adsbfi", [_aircraft("aaaaaa", "AFR1234 ")]),
                 ("adsblol", [_aircraft("aaaaaa", "AFR1234 ")])),
        queried=("adsbfi", "adsblol"), zone_key=own)

    assert _cycle(tmp_path, zone_fetch=fetched)["flight"]["hex"] == "aaaaaa"


def test_zone_fetch_where_every_provider_failed_marks_a_source_fault(tmp_path):
    fetched = zone_fetch.ZoneFetch(queried=("adsbfi", "adsblol"), failed=("adsbfi", "adsblol"))

    result = _cycle(tmp_path, zone_fetch=fetched)

    assert result["flight"] is None
    assert result["source_fault"] is True


def test_zone_fetch_with_one_failed_provider_gives_a_single_source_pick(tmp_path):
    fetched = zone_fetch.ZoneFetch(
        results=(("adsblol", [_aircraft("bbbbbb", "AFR9999 ")]),),
        queried=("adsbfi", "adsblol"), failed=("adsbfi",))

    result = _cycle(tmp_path, zone_fetch=fetched)

    assert result["flight"]["hex"] == "bbbbbb"
    assert result["flight"]["corroborated"] is None
    assert result["source_fault"] is False


def test_a_not_fetched_zone_gives_no_flight_and_no_fault(tmp_path):
    result = _cycle(tmp_path, zone_fetch=zone_fetch.ZoneFetch.not_fetched())

    assert result["flight"] is None
    assert result["source_fault"] is False


@pytest.mark.parametrize(
    "state_dir_parts, ledger_parts",
    [(("state",), ("state",)), (("root", "devices", "frame-1"), ("root",))],
)
def test_ledger_root_is_derived_from_the_state_directory(tmp_path, state_dir_parts, ledger_parts):
    state_dir = os.path.join(str(tmp_path), *state_dir_parts)

    assert poll_cycle._ledger_root_for(state_dir) == os.path.join(str(tmp_path), *ledger_parts)


# --- peek_hold(): the read-only twin of decide_hold -------------------------

_NOON_UTC = 1_790_510_400.0  # 2026-09-27T12:00:00Z


def _hold_fixture(state_dir, kind):
    if kind == "battery_empty":
        with open(os.path.join(state_dir, "battery_state.json"), "w", encoding="utf-8") as fh:
            json.dump({"battery_mv": 3000}, fh)
    elif kind == "display_off":
        device_config.save_device_config(state_dir, display_enabled=False)
    elif kind == "quiet_hours":
        device_config.save_device_config(
            state_dir, quiet_hours_enabled=True, quiet_hours_start="00:00", quiet_hours_end="23:59")


@pytest.mark.parametrize("kind", ["battery_empty", "display_off", "quiet_hours", None])
def test_peek_hold_matches_the_hold_run_once_enters(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(poll_cycle, "now_s", lambda: _NOON_UTC)
    _hold_fixture(str(tmp_path), kind)

    peeked = poll_cycle.peek_hold(str(tmp_path))
    result = _cycle(tmp_path, snapshot={})

    assert peeked == kind
    if kind is not None:
        assert result["state"] == kind


def _tree_state(root):
    entries = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            entries[os.path.relpath(path, root)] = os.stat(path).st_mtime_ns
    return entries


def test_peek_hold_writes_nothing_and_takes_no_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(poll_cycle, "now_s", lambda: _NOON_UTC)
    _hold_fixture(str(tmp_path), "quiet_hours")
    _cycle(tmp_path, snapshot={})
    before = _tree_state(str(tmp_path))

    def _no_lock(*args, **kwargs):
        raise AssertionError("peek_hold must not take the poll lock")

    monkeypatch.setattr(poll_cycle, "poll_cycle_lock", _no_lock)
    assert poll_cycle.peek_hold(str(tmp_path)) == "quiet_hours"

    assert _tree_state(str(tmp_path)) == before


def test_peek_hold_on_a_missing_directory_returns_none_and_creates_nothing(tmp_path):
    missing = tmp_path / "nope"

    assert poll_cycle.peek_hold(str(missing)) is None
    assert not missing.exists()


def test_peek_hold_on_an_empty_directory_creates_nothing(tmp_path):
    assert poll_cycle.peek_hold(str(tmp_path)) is None
    assert os.listdir(str(tmp_path)) == []


def test_peek_hold_tolerates_malformed_config_and_state(tmp_path):
    for name in ("device_config.json", "poll_state.json", "battery_state.json"):
        with open(os.path.join(str(tmp_path), name), "w", encoding="utf-8") as fh:
            fh.write("{not json")

    assert poll_cycle.peek_hold(str(tmp_path)) is None


# --- run_once(route_transport=): the shared adsbdb transport ----------------


def test_route_transport_serves_the_adsbdb_lookup(tmp_path, monkeypatch):
    calls = []

    def _transport(callsign, timeout=None):
        calls.append(callsign)
        return 404, None

    def _default_must_stay_unused(callsign, timeout=None):
        raise AssertionError("the default transport must not be used")

    monkeypatch.setattr(enrich, "default_transport", _default_must_stay_unused)
    snapshot = {"ac": [_aircraft("cccccc", "AFR5555 ")]}

    _cycle(tmp_path, snapshot=snapshot, route_transport=_transport)

    assert calls == ["AFR5555"]


def test_without_a_route_transport_the_default_transport_is_used(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: calls.append(callsign) or (404, None))

    _cycle(tmp_path, snapshot={"ac": [_aircraft("cccccc", "AFR5555 ")]})

    assert calls == ["AFR5555"]
