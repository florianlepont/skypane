#!/usr/bin/env python3
"""Golden-image guard for the giant-lettering screens.

Every case renders a canvas and compares its SHA-256 (and byte count) to
`fixtures/golden/giant_render_baseline.json`. The classic picture has its own
manifest and suite (`test_golden_render.py`); this file never adds cases to
that one, so its exact-names check stays valid.

Hashes depend on the Pillow version, which the manifest records. When the
installed Pillow differs, the hash comparison is skipped with a message
rather than failed; regenerate the manifest under the production pin:

    server/.venv/bin/python3 -c "import server.test_golden_giant_render as g; g.print_manifest()" > server/fixtures/golden/giant_render_baseline.json
"""
import hashlib
import json
import os
import sys

import pytest
import PIL

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from server import hardware, panel_format as pf, screen_layouts  # noqa: E402
from server.pairings import PAIRINGS  # noqa: E402
from server.plane.render import giant, layout  # noqa: E402
from server.plane.render.giant import status  # noqa: E402
from server.plane.render.giant.field import ink_index  # noqa: E402
from server.plane.render.giant.palette_check import LEGAL_INDICES, assert_giant_palette  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(HERE, "fixtures", "golden", "giant_render_baseline.json")
LEGACY_MANIFEST_PATH = os.path.join(HERE, "fixtures", "golden", "legacy_render_baseline.json")

PORTRAIT = (pf.WIDTH, pf.HEIGHT)
LANDSCAPE_PROFILE = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY, {hardware.SIM_ENV_VAR: "1"})
LANDSCAPE = (LANDSCAPE_PROFILE.width, LANDSCAPE_PROFILE.height)
GIANT_LAYOUTS = ("a", "b", "c", "a_diagonal")

FLIGHT = {"hex": "3985a7", "callsign": "AF1380", "aircraft_type": "B738"}
ROUTE = {
    "airline_name": "Transavia France",
    "origin_iata": "ORY", "origin_city": "Paris",
    "destination_iata": "PMI", "destination_city": "Palma de Mallorca",
    "callsign_iata": "TO16VB",
}


def _route(destination_city, destination_iata="PMI"):
    return dict(ROUTE, destination_city=destination_city, destination_iata=destination_iata)


NAME_ROUTES = {
    "long": _route("Santiago de Compostela-Rosalia de Castro", "SCQ"),
    "short": _route("Pau", "PUF"),
    "accented": _route("Besançon", "QBQ"),
    "hyphenated": _route("Saint-Pierre-et-Miquelon", "FSP"),
    "airline_only": {"airline_name": "Transavia France", "callsign_iata": "TO16VB"},
}


def _flight(size, layout_id, pairing_id, state="departing", route=ROUTE):
    def produce():
        canvas = giant.build_canvas(
            size, layout_id, FLIGHT, state, route=route, pairing=PAIRINGS[pairing_id])
        assert_giant_palette(canvas, ink_index(PAIRINGS[pairing_id].field_ink))
        return canvas.tobytes()
    return produce


def _status(kind, size, flat=False):
    def produce():
        canvas = status.build_status(kind, size, quiet_hours_until="07:00", flat=flat)
        used = {value for _, value in canvas.getcolors(maxcolors=256)}
        assert used <= LEGAL_INDICES
        return canvas.tobytes()
    return produce


def golden_cases():
    """Yield (name, zero-argument callable returning canvas bytes)."""
    for layout_id in GIANT_LAYOUTS:
        for pairing_id in PAIRINGS:
            for state in ("departing", "arriving"):
                yield "%s_%s_%s" % (layout_id, pairing_id, state), _flight(
                    PORTRAIT, layout_id, pairing_id, state)
    for layout_id in GIANT_LAYOUTS:
        for label, route in NAME_ROUTES.items():
            yield "%s_names_%s" % (layout_id, label), _flight(PORTRAIT, layout_id, "blue_light", route=route)
    for layout_id in GIANT_LAYOUTS:
        yield "%s_landscape_blue_light" % layout_id, _flight(LANDSCAPE, layout_id, "blue_light")
        yield "%s_landscape_white" % layout_id, _flight(LANDSCAPE, layout_id, "white", "arriving")
    for kind in status.KINDS:
        yield "status_%s_portrait" % kind, _status(kind, PORTRAIT)
        yield "status_%s_landscape" % kind, _status(kind, LANDSCAPE)
    yield "giant_flat_no_connection", _status("no_connection", PORTRAIT, flat=True)
    yield "giant_flat_updating", _status("updating", PORTRAIT, flat=True)


def build_manifest():
    cases = {}
    for name, produce in golden_cases():
        data = produce()
        cases[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    return {"pillow_version": PIL.__version__, "cases": cases}


def print_manifest():
    json.dump(build_manifest(), sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")


def _load_manifest():
    with open(MANIFEST_PATH) as fh:
        return json.load(fh)


def test_manifest_case_names_equal_generator_case_names():
    generated = [name for name, _ in golden_cases()]
    assert len(generated) == len(set(generated)), "duplicate golden case names"
    assert sorted(_load_manifest()["cases"]) == sorted(generated)


def test_case_matrix_covers_layouts_pairings_states_and_status_screens():
    names = {name for name, _ in golden_cases()}
    for layout_id in GIANT_LAYOUTS:
        for pairing_id in PAIRINGS:
            for state in ("departing", "arriving"):
                assert "%s_%s_%s" % (layout_id, pairing_id, state) in names
    for kind in status.KINDS:
        assert "status_%s_portrait" % kind in names
        assert "status_%s_landscape" % kind in names
    assert len(status.KINDS) == 7
    assert len(names) >= 84


def test_every_case_is_legal_and_matches_the_manifest():
    manifest = _load_manifest()
    if manifest["pillow_version"] != PIL.__version__:
        pytest.skip(
            "giant golden hashes were recorded with Pillow %s but Pillow %s is installed; "
            "regenerate under the production pin before trusting hashes"
            % (manifest["pillow_version"], PIL.__version__))
    mismatches = []
    for name, produce in golden_cases():
        data = produce()
        actual = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        if actual != manifest["cases"].get(name):
            mismatches.append("%s: expected %s, got %s" % (name, manifest["cases"].get(name), actual))
    assert not mismatches, "giant render changed for %d case(s):\n  %s" % (
        len(mismatches), "\n  ".join(mismatches))


def test_legacy_manifest_is_not_a_giant_manifest():
    with open(LEGACY_MANIFEST_PATH) as fh:
        legacy = json.load(fh)
    assert not set(legacy["cases"]) & set(_load_manifest()["cases"])


@pytest.mark.parametrize("name", ["theme_white_departing", "arriving_previous_white", "departing_battery_low"])
def test_classic_unchanged(name):
    from server import test_golden_render as legacy_suite
    produce = dict(legacy_suite.golden_cases())[name]
    expected = produce()
    # Reproduce the same case through the layout dispatcher with layout None and "classic".
    cases = {
        "theme_white_departing": dict(state="departing", theme_id="white"),
        "departing_battery_low": dict(state="departing", battery_low=True),
        "arriving_previous_white": dict(
            state="arriving", theme_id="white", previous_flight=legacy_suite.PREVIOUS_FLIGHT,
            previous_route=legacy_suite.PREVIOUS_ROUTE, previous_state="departing"),
    }[name]
    state = cases.pop("state")
    for layout_id in (None, screen_layouts.CLASSIC_LAYOUT_ID):
        canvas = layout.build_canvas(
            legacy_suite.FLIGHT, state, route=legacy_suite.ROUTE, layout=layout_id, **cases)
        assert pf.pack_panel(canvas) == expected
