#!/usr/bin/env python3
"""Golden-image guard for the 1200x1600 panel render.

Every case renders a packed panel and compares its SHA-256 (and byte
count) to `fixtures/golden/legacy_render_baseline.json`. The manifest was
recorded from an unmodified renderer tree, so any later change to the
shipped frame shows up here as a named mismatch. Fixtures are synthetic
and resolve vendored illustrations only: no network, no clock.

Regenerate the manifest only when a change is proven renderer-neutral by
re-rendering at the pre-change commit:

    server/.venv/bin/python3 -c "import server.test_golden_render as g; g.print_manifest()" > manifest.json
"""
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
from unittest import mock

import PIL

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.plane.render as render  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402
from server import panel_format, themes  # noqa: E402
from server.plane.render import hold_screens  # noqa: E402

MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "golden", "legacy_render_baseline.json")
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
PANEL_BYTES = 960000

FLIGHT = {"hex": "3985a7", "callsign": "AF1380", "aircraft_type": "B738"}
PREVIOUS_FLIGHT = {"hex": "4a1b02", "callsign": "VLG6PD", "aircraft_type": "A320"}
ROUTE = {
    "airline_name": "Transavia France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "PMI",
    "destination_city": "Palma de Mallorca",
    "callsign_iata": "TO16VB",
}
PREVIOUS_ROUTE = {
    "airline_name": "Vueling Airlines",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "BCN",
    "destination_city": "Barcelona",
    "callsign_iata": "VY8163",
}
LONG_ROUTE = {
    "airline_name": "Compagnie Nationale Royale Air Maroc Express",
    "origin_iata": "SCQ",
    "origin_city": "Santiago de Compostela–Rosalía de Castro",
    "destination_iata": "ORY",
    "destination_city": "Paris",
    "callsign_iata": "AT9051",
}


def _panel(*args, **kwargs):
    return lambda: render.render_panel(*args, **kwargs)


def _flat(builder):
    return lambda: panel_format.pack_panel(builder(flat=True))


def _end_to_end_panel():
    """Hash input for one full poll cycle: the panel.bin run_once writes.

    Route resolution is stubbed so the cycle never reaches a provider, and the
    cycle's log line is swallowed so the generator output stays pure JSON.
    """
    with open(os.path.join(FIXTURES_DIR, "geofence_multi_aircraft.json")) as fh:
        snapshot = json.load(fh)
    with tempfile.TemporaryDirectory() as state_dir:
        with mock.patch.object(poll_cycle.enrich, "resolve_route", return_value=(dict(ROUTE), "fresh_hit")):
            with contextlib.redirect_stdout(io.StringIO()):
                poll_cycle.run_once(snapshot=snapshot, state_dir=state_dir, geofence=GEOFENCE_PATH)
        with open(os.path.join(state_dir, "panel.bin"), "rb") as fh:
            return fh.read()


def _theme_cases():
    for theme_id in themes.THEMES:
        yield "theme_%s_departing" % theme_id, _panel(FLIGHT, "departing", route=ROUTE, theme_id=theme_id)


def _arriving_cases():
    for theme_id in ("white", "band_blue", "red_light", "band_red_field"):
        yield "arriving_previous_%s" % theme_id, _panel(
            FLIGHT, "arriving", route=ROUTE, previous_flight=PREVIOUS_FLIGHT,
            previous_route=PREVIOUS_ROUTE, previous_state="departing", theme_id=theme_id)


def _overlay_cases():
    for state in ("departing", "arriving"):
        yield "%s_battery_low" % state, _panel(FLIGHT, state, route=ROUTE, battery_low=True)
        yield "%s_source_fault" % state, _panel(FLIGHT, state, route=ROUTE, source_fault=True)
        yield "%s_both_overlays" % state, _panel(
            FLIGHT, state, route=ROUTE, battery_low=True, source_fault=True)


def _hold_cases():
    yield "empty_default", _panel(None, "empty")
    yield "empty_runway_06_24", _panel(None, "empty", runway_id="06-24")
    yield "empty_battery_low", _panel(None, "empty", battery_low=True)
    yield "empty_source_fault", _panel(None, "empty", source_fault=True)
    yield "quiet_hours_0700", _panel(None, "quiet_hours", quiet_hours_until="07:00")
    yield "quiet_hours_none", _panel(None, "quiet_hours", quiet_hours_until=None)
    yield "quiet_hours_battery_low", _panel(
        None, "quiet_hours", quiet_hours_until="07:00", battery_low=True)
    yield "display_off", _panel(None, "display_off")
    yield "display_off_source_fault", _panel(None, "display_off", source_fault=True)
    yield "battery_empty", _panel(None, "battery_empty")


def golden_cases():
    """Yield (name, zero-argument callable returning packed panel bytes)."""
    yield from _theme_cases()
    yield from _arriving_cases()
    yield from _overlay_cases()
    yield from _hold_cases()
    yield "long_names_departing", _panel(FLIGHT, "departing", route=LONG_ROUTE)
    yield "long_names_arriving_previous", _panel(
        FLIGHT, "arriving", route=LONG_ROUTE, previous_flight=PREVIOUS_FLIGHT,
        previous_route=PREVIOUS_ROUTE, previous_state="departing")
    yield "flat_no_connection", _flat(hold_screens._build_no_connection_canvas)
    yield "flat_updating", _flat(hold_screens._build_updating_canvas)
    yield "run_once_panel_bin", _end_to_end_panel


def build_manifest():
    cases = {}
    for name, produce in golden_cases():
        packed = produce()
        cases[name] = {"sha256": hashlib.sha256(packed).hexdigest(), "bytes": len(packed)}
    return {"pillow_version": PIL.__version__, "cases": cases}


def print_manifest():
    json.dump(build_manifest(), sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")


def _load_manifest():
    with open(MANIFEST_PATH) as fh:
        return json.load(fh)


def test_manifest_records_the_installed_pillow_version():
    recorded = _load_manifest()["pillow_version"]
    assert recorded == PIL.__version__, (
        "Pillow is %s but the golden manifest was recorded with %s: this is a toolchain "
        "change, not a renderer change. Re-record the baseline from the pre-change commit "
        "with the new Pillow before trusting any hash." % (PIL.__version__, recorded))


def test_manifest_case_names_equal_generator_case_names():
    generated = [name for name, _ in golden_cases()]
    assert len(generated) == len(set(generated)), "duplicate golden case names"
    assert sorted(_load_manifest()["cases"]) == sorted(generated)


def test_case_matrix_is_broad_and_covers_every_theme():
    names = {name for name, _ in golden_cases()}
    assert len(names) >= 35
    for theme_id in themes.THEMES:
        assert "theme_%s_departing" % theme_id in names


def test_legacy_render_is_byte_identical_to_the_baseline():
    manifest = _load_manifest()
    mismatches = []
    for name, produce in golden_cases():
        expected = manifest["cases"].get(name)
        packed = produce()
        actual = {"sha256": hashlib.sha256(packed).hexdigest(), "bytes": len(packed)}
        if expected is None or actual != expected or actual["bytes"] != PANEL_BYTES:
            mismatches.append("%s: expected %s, got %s" % (name, expected, actual))
    assert not mismatches, (
        "the legacy 1200x1600 render changed for %d case(s):\n  %s\n"
        "Do not regenerate the manifest unless the change is proven renderer-neutral by "
        "re-rendering at the pre-change commit." % (len(mismatches), "\n  ".join(mismatches)))
