#!/usr/bin/env python3
"""Contract tests for server/plane/detect.py's geofence filter, the
D-P2-01 multi-aircraft selection rule, and the runway-3 identification
gate added by the runway3-false-positive debug session (2026-08-27).

Several groups below are regression coverage built on real live captures
of actual bugs and their correct counter-examples (see
server/fixtures/README.md), plus the real published OurAirports
coordinates of Orly's other two runways, which the corridor/track gates
must never accept as runway 3.

NOT EVERY CHECK IN A GROUP IS SUPPOSED TO FAIL AGAINST THE OLD CODE, and
conflating the two kinds is how a suite starts lying about what it
proves. The regressions fail when the pre-fix implementation is
restored - that is what makes them evidence. The precondition checks
assert the OLD behaviour is genuinely reproducible, so they must hold in
BOTH directions or the fixture is not reproducing the bug at all. The
guards assert something that must be true both before and after a fix -
kept to a single question each so none can be mistaken for a regression
check and quietly relaxed.

Transport-level provider stubbing (adsb.fi/adsb.lol response-key
mapping, check 28 in the pre-migration harness) uses the shared
`fake_providers` fixture (conftest.py, installed on requests.get).
Checks that stub detect.query_provider() itself (the harness's own
_with_stubbed_providers() helper) use the local `stubbed_query_provider`
fixture below, which is the same translation applied through
monkeypatch rather than manual save/restore.
"""
import contextlib
import io
import json
import os
import random
import sys
import threading
import time

import pytest
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import efficiency_probe  # noqa: E402
import server.plane.detect as detect  # noqa: E402
from server import http_fetch  # noqa: E402


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        return json.load(fh)


def load_geofence():
    with open(GEOFENCE_PATH) as fh:
        return json.load(fh)


def _wrong_runway_record():
    return load_fixture("geofence_wrong_runway_39de4a.json")["aircraft"]


def _runway3_record():
    return load_fixture("geofence_runway3_arrival_347288.json")["aircraft"]


def _masking_snapshot():
    return load_fixture("geofence_taxiway_masking.json")["aircraft"]


def _pavement(provider):
    """The pavement-pair fixture's payload for one provider, in that
    provider's own response shape (adsb.fi's 'aircraft' key vs adsb.lol's
    'ac' key - see test_provider_keys_are_not_interchanged for why that
    distinction is never assumed anywhere in this file).
    """
    block = load_fixture("geofence_pavement_pair.json")[provider]
    return block["aircraft"] if provider == "adsbfi" else block["ac"]


def _prefix_sort_key(ac):
    """The PRE-FIX D-P2-01 key, written out here rather than imported, so
    this file still describes the old behaviour after detect.py stopped
    implementing it: (effective altitude, seen_pos, hex).
    """
    seen_pos = ac.get("seen_pos")
    seen_pos_key = seen_pos if isinstance(seen_pos, (int, float)) else float("inf")
    return (detect.effective_altitude_ft(ac), seen_pos_key, ac.get("hex") or "")


def _strip_volatile(record):
    return {k: v for k, v in record.items() if k != "seen_pos" and not k.startswith("_")}


def _on_axis_record(geofence, runway_id, fraction, hex_id):
    """A synthetic on-ground record sitting exactly `fraction` of the way
    along `runway_id`'s real centreline (0.0 = the first threshold, 1.0 =
    the second), with its track set to that runway's own bearing - i.e. a
    record that should positively track `runway_id` and no other runway.
    Built by walking detect.runway_axis()'s own local-metres frame in
    reverse; the underlying lat/lon numbers all trace back to
    runway3.json's published thresholds, not a literal pasted into this
    file.
    """
    axis = detect.runway_axis(geofence, runway_id=runway_id)
    along_m = axis["length_m"] * fraction
    dx = along_m * axis["ux"]
    dy = along_m * axis["uy"]
    lat = axis["lat0"] + dy / detect._M_PER_DEG_LAT
    lon = axis["lon0"] + dx / axis["lon_scale"]
    return {
        "hex": hex_id,
        "flight": "TEST001 ",
        "lat": lat,
        "lon": lon,
        "alt_baro": "ground",
        "track": axis["bearing_deg"],
    }


@pytest.fixture(scope="module")
def geofence():
    return load_geofence()


@pytest.fixture
def stubbed_query_provider(monkeypatch):
    """Replace detect.query_provider with a lookup into a dict handed at
    call time (name -> aircraft_list, or an Exception instance to raise),
    and zero the inter-call sleep - the monkeypatch translation of the
    pre-migration harness's _with_stubbed_providers() helper.
    """
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0)

    def _install(responses):
        def fake_query(name, lat, lon, radius_nm, timeout=10.0):
            value = responses[name]
            if isinstance(value, Exception):
                raise value
            return value
        monkeypatch.setattr(detect, "query_provider", fake_query)

    return _install


# ---------------------------------------------------------------
# Geofence filter / D-P2-01 multi-aircraft selection
# ---------------------------------------------------------------

def test_filter_in_geofence_drops_out_of_bbox_and_positionless(geofence):
    """filter_in_geofence drops out-of-bbox and position-less records"""
    fixture = load_fixture("geofence_multi_aircraft.json")
    matched = detect.filter_in_geofence(fixture["ac"], geofence)
    matched_hexes = {ac["hex"] for ac in matched}
    assert "000001" not in matched_hexes, "out-of-bbox synthetic hex 000001 was not dropped"
    assert "000002" not in matched_hexes, "position-less synthetic hex 000002 was not dropped"
    assert {"39d300", "39dd01"} <= matched_hexes, "real in-bbox hexes missing from filtered result: %r" % matched_hexes


def test_select_runway3_aircraft_picks_lowest_altitude(geofence):
    """select_runway3_aircraft picks 39d300 (450ft beats 800ft)"""
    fixture = load_fixture("geofence_multi_aircraft.json")
    winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
    assert winner is not None, "expected a winner, got None"
    assert winner["hex"] == "39d300", "expected hex 39d300 (450ft), got %r" % (winner["hex"],)


def test_select_runway3_aircraft_on_ground_beats_airborne(geofence):
    """select_runway3_aircraft: on-ground beats 800ft airborne"""
    fixture = load_fixture("geofence_on_ground.json")
    winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
    assert winner is not None, "expected a winner, got None"
    assert winner["hex"] == "3985a7", "expected hex 3985a7 (on-ground), got %r" % (winner["hex"],)


def test_select_runway3_aircraft_empty_returns_none(geofence):
    """select_runway3_aircraft returns None for an empty snapshot"""
    fixture = load_fixture("geofence_empty.json")
    winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
    assert winner is None, "expected None for an empty geofence snapshot, got %r" % (winner,)


def test_selected_record_callsign_is_stripped(geofence):
    """selected record's callsign is stripped of trailing padding"""
    fixture = load_fixture("geofence_multi_aircraft.json")
    winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
    assert winner is not None, "expected a winner"
    assert winner.get("callsign") == "TVF23WV", "expected stripped callsign 'TVF23WV', got %r" % (winner.get("callsign"),)


def test_select_runway3_aircraft_deterministic_under_shuffle(geofence):
    """select_runway3_aircraft is deterministic under input reordering"""
    fixture = load_fixture("geofence_multi_aircraft.json")
    aircraft = list(fixture["ac"])
    first = detect.select_runway3_aircraft(aircraft, geofence)
    shuffled = list(aircraft)
    random.Random(1234).shuffle(shuffled)
    second = detect.select_runway3_aircraft(shuffled, geofence)
    assert first is not None and second is not None, "expected both selections to return a winner"
    assert first["hex"] == second["hex"], "selection changed under shuffled input ordering: %r vs %r" % (
        first["hex"], second["hex"],
    )


def test_multi_aircraft_winner_has_aircraft_type(geofence):
    """select_runway3_aircraft: multi-aircraft winner's aircraft_type is B738"""
    fixture = load_fixture("geofence_multi_aircraft.json")
    winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
    assert winner is not None, "expected a winner"
    assert winner.get("aircraft_type") == "B738", "expected aircraft_type 'B738', got %r" % (winner.get("aircraft_type"),)


def test_on_ground_winner_has_aircraft_type(geofence):
    """select_runway3_aircraft: on-ground winner's aircraft_type is A320"""
    fixture = load_fixture("geofence_on_ground.json")
    winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
    assert winner is not None, "expected a winner"
    assert winner.get("aircraft_type") == "A320", "expected aircraft_type 'A320', got %r" % (winner.get("aircraft_type"),)


def test_no_type_key_yields_none(geofence):
    """select_runway3_aircraft: a record with no t key yields aircraft_type None"""
    fixture = load_fixture("geofence_multi_aircraft.json")
    winner_record = next(ac for ac in fixture["ac"] if ac["hex"] == "39d300")
    no_type_record = dict(winner_record)
    no_type_record.pop("t", None)
    winner = detect.select_runway3_aircraft([no_type_record], geofence)
    assert winner is not None, "expected a winner"
    assert winner.get("aircraft_type") is None, (
        "expected aircraft_type None for a record with no t key, got %r" % (winner.get("aircraft_type"),)
    )


def test_malformed_type_values_never_raise(geofence):
    """select_runway3_aircraft: malformed type values all yield aircraft_type None without raising (T-03.1-02-01 / ASVS V5)"""
    fixture = load_fixture("geofence_multi_aircraft.json")
    winner_record = next(ac for ac in fixture["ac"] if ac["hex"] == "39d300")
    malformed_values = ["", "   ", 738, ["A320"], "../../etc/passwd"]
    for bad_value in malformed_values:
        record = dict(winner_record)
        record["t"] = bad_value
        winner = detect.select_runway3_aircraft([record], geofence)
        assert winner is not None, "expected a winner for malformed t=%r" % (bad_value,)
        assert winner.get("aircraft_type") is None, (
            "expected aircraft_type None for malformed t=%r, got %r" % (bad_value, winner.get("aircraft_type"))
        )


# ---------------------------------------------------------------
# runway3-false-positive (2026-08-27): runway-3 identification gate
# ---------------------------------------------------------------

def test_wrong_runway_fixture_reproduces_the_precondition(geofence):
    """real wrong-runway record 39de4a is in-bbox and below-ceiling (the pre-fix accept condition)"""
    # The real false-positive record genuinely reproduces the bug's
    # precondition: it IS inside the bbox and IS below the ceiling, so the
    # pre-fix code (which gated on exactly those two things) had no reason
    # to reject it. Without this, test_wrong_runway_is_rejected could pass
    # for the wrong reason - e.g. if the fixture were simply out of bbox.
    matched = detect.filter_in_geofence(_wrong_runway_record(), geofence)
    assert len(matched) == 1 and matched[0]["hex"] == "39de4a", (
        "expected the real 39de4a record to be in-bbox, got %r" % ([m.get("hex") for m in matched],)
    )
    assert matched[0].get("in_bbox") and matched[0].get("below_ceiling"), (
        "expected in_bbox and below_ceiling True (the pre-fix accept condition), got %r" % (
            {k: matched[0].get(k) for k in ("in_bbox", "below_ceiling")},
        )
    )


def test_wrong_runway_is_rejected(geofence):
    """select_runway3_aircraft rejects the real runway-20 departure 39de4a (the reported false positive)"""
    # THE REGRESSION. hex 39de4a (TVF12ZW) was captured live on
    # 2026-08-27 being selected as "the aircraft using runway 3" while it
    # was actually departing runway 20 - climbing +2304 ft/min on track
    # 197.67, 750m off runway 3's centreline. It must now be rejected,
    # leaving nothing selected for that snapshot.
    winner = detect.select_runway3_aircraft(_wrong_runway_record(), geofence)
    assert winner is None, "the real runway-20 departure 39de4a was still selected as runway 3: %r" % (winner,)


def test_real_runway3_arrival_is_still_selected(geofence):
    """select_runway3_aircraft still selects the real runway-25 arrival 347288 (no over-tightening)"""
    # The counter-example: the gate must not have been tightened into
    # rejecting genuine runway-3 traffic. hex 347288 (IBE05DP) was
    # captured in the same live window on final to runway 25.
    winner = detect.select_runway3_aircraft(_runway3_record(), geofence)
    assert winner is not None, "the real runway-25 arrival 347288 is no longer selected"
    assert winner["hex"] == "347288" and winner["callsign"] == "IBE05DP", (
        "expected 347288/IBE05DP, got %r/%r" % (winner["hex"], winner.get("callsign"))
    )


def test_wrong_runway_loses_to_real_one(geofence):
    """with both real aircraft present, only the genuine runway-3 arrival is a candidate"""
    combined = _wrong_runway_record() + _runway3_record()
    tagged = {ac["hex"]: ac for ac in detect.filter_in_geofence(combined, geofence)}
    assert not tagged["39de4a"].get("on_runway3"), "39de4a was still tagged on_runway3"
    assert tagged["347288"].get("on_runway3"), "347288 was not tagged on_runway3"
    winner = detect.select_runway3_aircraft(combined, geofence)
    assert winner is not None and winner["hex"] == "347288", "expected 347288 to win, got %r" % (winner and winner["hex"],)


def test_axis_is_derived_from_published_thresholds(geofence):
    """runway_axis/along_cross_track_m are derived from the published thresholds"""
    axis = detect.runway_axis(geofence)
    assert axis is not None, "runway_axis() returned None for the project geofence"
    assert 74.0 <= axis["bearing_deg"] <= 75.0, "expected a ~74.4 deg TRUE bearing, got %r" % (axis["bearing_deg"],)
    assert 3300.0 <= axis["length_m"] <= 3330.0, "expected a ~3320m centreline, got %r" % (axis["length_m"],)
    runway = geofence["runway"]
    a0, c0 = detect.along_cross_track_m(runway["threshold_07"]["lat"], runway["threshold_07"]["lon"], geofence)
    a1, c1 = detect.along_cross_track_m(runway["threshold_25"]["lat"], runway["threshold_25"]["lon"], geofence)
    assert abs(a0) <= 1.0 and abs(c0) <= 1.0, "threshold 07 should be the axis origin, got along=%r cross=%r" % (a0, c0)
    assert abs(a1 - axis["length_m"]) <= 1.0 and abs(c1) <= 1.0, (
        "threshold 25 should sit at (length, 0), got along=%r cross=%r" % (a1, c1)
    )


def test_track_deviation_is_bidirectional_and_type_safe(geofence):
    """track_axis_deviation_deg is bidirectional and rejects bools/non-numerics"""
    # Alignment is measured against TRUE track and is direction-agnostic
    # (runway 3 is used both ways). Bools are rejected before the numeric
    # check - Python's bool is an int subclass, so an unguarded True would
    # read as a 1-degree track.
    cases = [
        (254.9, 1.0),    # the real IBE05DP arrival on final to 25
        (74.41, 0.2),    # the reciprocal - rolling out on 07
        (197.67, 57.5),  # the real runway-20 departure
    ]
    for track, ceiling in cases:
        dev = detect.track_axis_deviation_deg(track, geofence)
        assert dev is not None and dev <= ceiling, "track %r: expected deviation <= %r, got %r" % (track, ceiling, dev)
    assert detect.track_axis_deviation_deg(197.67, geofence) >= 55.0, (
        "the runway-20 track should be ~56 deg off runway 3's axis"
    )
    for bad in (None, "254", True, False, [254]):
        assert detect.track_axis_deviation_deg(bad, geofence) is None, "expected None for a non-numeric track %r" % (bad,)


def test_corridor_is_what_rejects_runway_06_24(geofence):
    """runway 06/24's published thresholds are rejected by the corridor gate, not the track gate"""
    # Runway 06/24 is only ~12 deg off runway 3's heading, so the track
    # gate CANNOT separate it - this asserts the corridor is what rejects
    # it, i.e. that the corridor gate is load-bearing rather than
    # redundant. Coordinates are the real published OurAirports LFPO
    # thresholds carried in runway3.json.
    neighbour = geofence["runway"]["neighbouring_runways"]["06/24"]
    for key, track in (("threshold_06", 62.0), ("threshold_24", 242.0)):
        point = neighbour[key]
        record = {"hex": "060024", "lat": point["lat"], "lon": point["lon"], "alt_baro": "ground", "track": track}
        tagged = detect.filter_in_geofence([record], geofence)
        if not tagged:
            continue  # outside the coarse bbox is also a valid rejection
        assert tagged[0]["track_aligned"], (
            "%s: the track gate rejected it, so this check no longer proves the corridor is load-bearing "
            "(06/24 is only ~12 deg off axis)" % key
        )
        assert not tagged[0]["in_corridor"], "%s: runway 06/24 was accepted into the runway-3 corridor" % key
        assert not tagged[0]["on_runway3"], "%s: runway 06/24 was tagged on_runway3" % key


def test_track_gate_is_what_rejects_runway_02_20(geofence):
    """runway 02/20's centreline crossing is rejected by the track gate, not the corridor gate"""
    # The mirror image: runway 02/20 physically CROSSES runway 3's
    # centreline, so the corridor gate cannot separate it - this asserts
    # the track gate is what rejects it. The test point is the real
    # crossing point of the two published centrelines.
    neighbour = geofence["runway"]["neighbouring_runways"]["02/20"]
    start, end = neighbour["threshold_02"], neighbour["threshold_20"]
    best = None
    for i in range(1001):
        f = i / 1000.0
        lat = start["lat"] + f * (end["lat"] - start["lat"])
        lon = start["lon"] + f * (end["lon"] - start["lon"])
        _, cross = detect.along_cross_track_m(lat, lon, geofence)
        if best is None or abs(cross) < abs(best[2]):
            best = (lat, lon, cross)
    lat, lon, cross = best
    assert abs(cross) <= 25.0, (
        "expected runway 02/20 to cross runway 3's centreline (|cross| ~0), got %r - the premise of this "
        "check no longer holds" % cross
    )
    record = {"hex": "020020", "lat": lat, "lon": lon, "alt_baro": "ground", "track": 198.0}
    tagged = detect.filter_in_geofence([record], geofence)
    assert tagged, "the 02/20 crossing point fell outside the bbox; check premise broken"
    assert tagged[0]["in_corridor"], (
        "the corridor rejected the crossing point, so this check no longer proves the track gate is load-bearing"
    )
    assert not tagged[0]["track_aligned"], "a runway-20-aligned track (198 deg) was accepted as runway-3-aligned"
    assert not tagged[0]["on_runway3"], "an aircraft on runway 02/20's centreline was tagged on_runway3"


def test_missing_track_does_not_disqualify(geofence):
    """a record with no track is corridor-gated rather than rejected outright"""
    # A record with no `track` is not disqualified - it still has to pass
    # the corridor. This is the documented asymmetry with below_ceiling's
    # "unknown never claims" rule, and it is what keeps the pre-existing
    # real fixtures (which carry no track) selectable.
    fixture = load_fixture("geofence_on_ground.json")
    tagged = {ac["hex"]: ac for ac in detect.filter_in_geofence(fixture["ac"], geofence)}
    assert tagged["3985a7"].get("track_deg") is None, "premise broken: fixture 3985a7 now carries a track"
    assert tagged["3985a7"].get("track_aligned"), "a record with no track was treated as misaligned"
    assert tagged["3985a7"].get("on_runway3"), "the real on-ground runway-3 record stopped qualifying"
    # ...but the corridor still applies to it: move it 900m off the
    # centreline (roughly where runway 06/24 sits) and it must fail.
    off_corridor = dict(next(ac for ac in fixture["ac"] if ac["hex"] == "3985a7"))
    off_corridor["lat"] = 48.7355   # real runway 24 threshold, no track field
    off_corridor["lon"] = 2.36068
    off_corridor.pop("track", None)
    moved = detect.filter_in_geofence([off_corridor], geofence)
    assert not (moved and moved[0].get("on_runway3")), (
        "an untracked record 1600m off the centreline still qualified as runway 3"
    )


# ---------------------------------------------------------------
# Provider default order (2026-08-27 airplanes.live free-tier withdrawal)
# ---------------------------------------------------------------

def test_default_poll_queries_adsbfi_then_adsblol(geofence, monkeypatch):
    """default poll (no providers arg) queries both adsb.fi and adsb.lol, diagnostics['queried'] keeps provider order"""
    # Default poll (no providers argument - exactly how
    # server/poll_loop.py's run_once() calls it in production) queries
    # both adsb.fi and adsb.lol. Pins the 2026-08-27 default-provider-order
    # change (adsb.lol added as the second entry) so this regression
    # cannot silently reopen - but since the two are now queried in
    # parallel (concurrent.futures.ThreadPoolExecutor), which one actually
    # answers first is no longer deterministic, so this asserts the call
    # SET and diagnostics['queried']'s provider order, not call order.
    recorded = set()

    def recording_query_provider(name, lat, lon, radius_nm, timeout=10.0):
        recorded.add(name)
        return []

    monkeypatch.setattr(detect, "query_provider", recording_query_provider)
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0)
    diagnostics = {}
    detect.poll_current_aircraft(geofence, diagnostics=diagnostics)

    assert recorded == {"adsbfi", "adsblol"}, (
        "expected default poll to query exactly {'adsbfi', 'adsblol'}, got %r" % (recorded,)
    )
    assert diagnostics["queried"] == ["adsbfi", "adsblol"], (
        "expected diagnostics['queried'] to keep DEFAULT_PROVIDER_ORDER, got %r" % (diagnostics["queried"],)
    )


def test_diagnostics_queried_order_is_stable_even_when_adsblol_answers_first(geofence, monkeypatch):
    """poll_current_aircraft: diagnostics['queried'] stays ['adsbfi', 'adsblol'] even when adsblol's fake returns first"""
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0)
    called = set()

    def fake_query_provider(name, lat, lon, radius_nm, timeout=10.0):
        called.add(name)
        if name == "adsbfi":
            time.sleep(0.05)  # the real sleep, not the injected `sleep` param - adsblol answers first
        return []

    monkeypatch.setattr(detect, "query_provider", fake_query_provider)
    diagnostics = {}
    detect.poll_current_aircraft(geofence, diagnostics=diagnostics)

    assert called == {"adsbfi", "adsblol"}, "expected both providers to have been called, got %r" % (called,)
    assert diagnostics["queried"] == ["adsbfi", "adsblol"], (
        "expected diagnostics['queried'] to keep provider order regardless of answer order, got %r" % (
            diagnostics["queried"],
        )
    )


def test_providers_are_queried_concurrently(geofence, monkeypatch):
    """poll_current_aircraft queries adsbfi and adsblol concurrently, not one after another"""
    # A sequential loop can never observe this: adsbfi's fake blocks on an
    # Event that adsblol's fake sets on entry, so adsbfi only returns if
    # adsblol was already running at the same time.
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0)
    adsblol_started = threading.Event()
    observed = {}

    def fake_query_provider(name, lat, lon, radius_nm, timeout=10.0):
        if name == "adsblol":
            adsblol_started.set()
            return []
        if name == "adsbfi":
            observed["adsblol_was_running"] = adsblol_started.wait(timeout=5.0)
            return []
        raise AssertionError("unexpected provider %r" % (name,))

    monkeypatch.setattr(detect, "query_provider", fake_query_provider)
    detect.poll_current_aircraft(geofence)

    assert observed.get("adsblol_was_running") is True, (
        "adsbfi never observed adsblol's event - the two providers were not queried concurrently"
    )


def test_default_last_call_at_uses_local_dict_and_no_sleep(geofence, monkeypatch):
    """poll_current_aircraft: with MIN_SECONDS_BETWEEN_CALLS at 1.1 and no last_call_at, one poll records zero sleeps and does not raise"""
    # Within one cycle, each provider is called exactly once, so no
    # previous call for it can exist yet - the fixed inter-provider sleep
    # this removes used to cost ~90% of a no-network poll cycle.
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 1.1)
    monkeypatch.setattr(detect, "query_provider", lambda name, lat, lon, radius_nm, timeout=10.0: [])

    with efficiency_probe.count_sleeps() as sleeps:
        result = detect.poll_current_aircraft(geofence)

    assert sleeps == [], "expected zero sleep calls on a poll with no prior last_call_at, got %r" % (sleeps,)
    assert result is None


def test_first_provider_wins_on_agreement_even_if_it_answers_last(geofence, stubbed_query_provider):
    """poll_current_aircraft: on agreement, adsbfi's own record wins even though adsblol's fake answers first"""
    winner = dict(_runway3_record()[0])
    adsblol_copy = dict(winner)
    adsblol_copy["alt_baro"] = 999  # same hex, different altitude - proves whose record actually won
    stubbed_query_provider({"adsbfi": [winner], "adsblol": [adsblol_copy]})

    result = detect.poll_current_aircraft(geofence)

    assert result is not None, "expected a selection on agreement"
    assert result["hex"] == winner["hex"], "expected %r, got %r" % (winner["hex"], result["hex"])
    assert result.get("corroborated") is True, "expected corroborated True, got %r" % (result.get("corroborated"),)
    assert sorted(result.get("sources") or []) == ["adsbfi", "adsblol"], (
        "expected both providers in sources, got %r" % (result.get("sources"),)
    )
    assert result.get("altitude_ft") == winner["alt_baro"], (
        "expected adsbfi's own altitude (the first-listed provider) to win, got %r" % (result.get("altitude_ft"),)
    )


def test_failing_provider_is_caught_and_recorded_per_provider(geofence, stubbed_query_provider):
    """poll_current_aircraft: a provider raising requests.ConnectionError is caught per-provider, the other's selection still comes back"""
    stubbed_query_provider({
        "adsbfi": requests.ConnectionError("simulated adsb.fi outage"),
        "adsblol": _runway3_record(),
    })
    diagnostics = {}

    result = detect.poll_current_aircraft(geofence, diagnostics=diagnostics)

    assert result is not None, "expected adsblol's own selection despite adsbfi raising ConnectionError"
    assert result["hex"] == "347288", "expected 347288, got %r" % (result["hex"],)
    assert diagnostics["failed"] == ["adsbfi"], "expected adsbfi recorded as failed, got %r" % (diagnostics["failed"],)


def test_spacing_uses_injected_clock_and_sleep_per_provider(geofence, monkeypatch):
    """poll_current_aircraft: an injected clock/sleep spaces only the provider whose last_call_at is due, never the other"""
    monkeypatch.setattr(detect, "query_provider", lambda name, lat, lon, radius_nm, timeout=10.0: [])
    last_call_at = {"adsbfi": 100.0}
    sleeps = []

    detect.poll_current_aircraft(
        geofence,
        last_call_at=last_call_at,
        clock=lambda: 100.4,
        sleep=lambda seconds: sleeps.append(seconds),
    )

    assert len(sleeps) == 1, "expected exactly one injected sleep call (for adsbfi only), got %r" % (sleeps,)
    assert abs(sleeps[0] - 0.7) < 1e-9, "expected a ~0.7s wait for adsbfi, got %r" % (sleeps[0],)
    assert last_call_at["adsbfi"] == 100.4 and last_call_at["adsblol"] == 100.4, (
        "expected both providers' last_call_at updated to the clock value at call time, got %r" % (last_call_at,)
    )


def test_airplaneslive_still_opt_in():
    """airplaneslive remains a selectable opt-in, absent from the default order"""
    # The airplanes.live opt-in path survives the demotion: still
    # selectable via --provider, but no longer in the default order.
    assert "airplaneslive" in detect.PROVIDERS, "airplaneslive was removed from PROVIDERS - the opt-in path must be retained"
    assert "airplaneslive" not in detect.DEFAULT_PROVIDER_ORDER, (
        "airplaneslive is still in DEFAULT_PROVIDER_ORDER - it must be opt-in only"
    )


# ---------------------------------------------------------------
# Per-poll cross-source validation (fix 2)
# ---------------------------------------------------------------

def test_agreeing_providers_are_corroborated(geofence, stubbed_query_provider):
    """poll_current_aircraft: two agreeing providers yield corroborated=True"""
    # Both providers independently select the same aircraft -> the
    # selection is returned and marked corroborated by both. Uses an
    # explicit multi-provider call - the default order only has adsb.fi,
    # so this exercises the cross-validation path a production poll
    # cannot reach until a second default source exists.
    stubbed_query_provider({"airplaneslive": _runway3_record(), "adsbfi": _runway3_record()})
    result = detect.poll_current_aircraft(geofence, providers=["airplaneslive", "adsbfi"])
    assert result is not None, "two agreeing providers produced no selection"
    assert result["hex"] == "347288", "expected 347288, got %r" % (result["hex"],)
    assert result.get("corroborated") is True, "expected corroborated True, got %r" % (result.get("corroborated"),)
    assert sorted(result.get("sources") or []) == ["adsbfi", "airplaneslive"], (
        "expected both providers in sources, got %r" % (result.get("sources"),)
    )


def test_disagreeing_providers_yield_nothing(geofence, stubbed_query_provider):
    """poll_current_aircraft: disagreeing providers select nothing (doubt -> hold)"""
    # The providers name two different aircraft as "the one on runway 3" -
    # at most one can be right, so the poll selects nothing and the panel
    # stays on hold. Built from the real arrival record plus a
    # copy relocated to the other end of the real runway, so both are
    # legitimately on runway 3 and the disagreement is about which
    # aircraft, not about the gate.
    other = dict(_runway3_record()[0])
    other["hex"] = "3985a7"
    other["flight"] = "AFR56XX "
    other["lat"] = 48.719398   # real threshold 07, the far end of runway 3
    other["lon"] = 2.358590
    other["track"] = 74.41
    assert detect.select_runway3_aircraft([other], geofence) is not None, (
        "premise broken: the stand-in aircraft is not itself on runway 3"
    )
    stubbed_query_provider({"airplaneslive": _runway3_record(), "adsbfi": [other]})
    result = detect.poll_current_aircraft(geofence, providers=["airplaneslive", "adsbfi"])
    assert result is None, "expected None on provider disagreement, got %r" % (result and result["hex"],)


def test_single_reachable_provider_is_uncorroborated_not_suppressed(geofence, stubbed_query_provider):
    """poll_current_aircraft: an unreachable provider is not scored as disagreement"""
    # One provider unreachable (the live 2026-08-27 reality:
    # api.airplanes.live answers 403) must NOT be scored as disagreement -
    # the reachable provider's selection is returned, flagged as
    # uncorroborated rather than suppressed.
    import requests
    stubbed_query_provider({
        "airplaneslive": requests.RequestException("403 Client Error: Forbidden"),
        "adsbfi": _runway3_record(),
    })
    result = detect.poll_current_aircraft(geofence, providers=["airplaneslive", "adsbfi"])
    assert result is not None, "a single reachable provider was suppressed as if it were a disagreement"
    assert result["hex"] == "347288", "expected 347288, got %r" % (result["hex"],)
    assert result.get("corroborated") is None, (
        "expected corroborated None (no corroboration available), got %r" % (result.get("corroborated"),)
    )
    assert result.get("sources") == ["adsbfi"], "expected sources ['adsbfi'], got %r" % (result.get("sources"),)


# ---------------------------------------------------------------
# adsb.lol as the second default provider (2026-08-27, later)
# ---------------------------------------------------------------

def test_default_order_corroborates(geofence, stubbed_query_provider):
    """poll_current_aircraft (default order): adsb.fi and adsb.lol agreeing yields corroborated=True with adsb.fi's record"""
    # The default order (adsb.fi then adsb.lol, no explicit providers
    # argument) corroborates when both feeds agree - proving the
    # cross-validation actually runs through the path production uses,
    # not only through an explicit providers argument.
    adsblol_copy = dict(_runway3_record()[0])
    adsblol_copy["alt_baro"] = 600  # still on the runway, still below the
                                    # ceiling - a different but still-
                                    # legitimate altitude reading
    stubbed_query_provider({"adsbfi": _runway3_record(), "adsblol": [adsblol_copy]})
    result = detect.poll_current_aircraft(geofence)
    assert result is not None, "two agreeing default-order providers produced no selection"
    assert result["hex"] == "347288", "expected 347288, got %r" % (result["hex"],)
    assert result.get("corroborated") is True, "expected corroborated True, got %r" % (result.get("corroborated"),)
    assert sorted(result.get("sources") or []) == ["adsbfi", "adsblol"], (
        "expected both default providers in sources, got %r" % (result.get("sources"),)
    )
    assert result.get("altitude_ft") == 775.0, (
        "expected the returned altitude to be adsb.fi's (the first-listed provider), got %r" % (result.get("altitude_ft"),)
    )


def test_default_order_disagreement_yields_nothing(geofence, stubbed_query_provider):
    """poll_current_aircraft (default order): adsb.fi and adsb.lol disagreeing select nothing"""
    # Mirrors test_disagreeing_providers_yield_nothing but reached through
    # the production default order (no providers argument) rather than an
    # explicit providers list - adsb.fi and adsb.lol naming two different
    # aircraft as "the one on runway 3" is doubt, not information, so the
    # panel is left alone.
    other = dict(_runway3_record()[0])
    other["hex"] = "3985a7"
    other["flight"] = "AFR56XX "
    other["lat"] = 48.719398   # real threshold 07, the far end of runway 3
    other["lon"] = 2.358590
    other["track"] = 74.41
    assert detect.select_runway3_aircraft([other], geofence) is not None, (
        "premise broken: the stand-in aircraft is not itself on runway 3"
    )
    stubbed_query_provider({"adsbfi": _runway3_record(), "adsblol": [other]})
    result = detect.poll_current_aircraft(geofence)
    assert result is None, "expected None on default-order provider disagreement, got %r" % (result and result["hex"],)


def test_default_order_degrades_to_single_source(geofence, stubbed_query_provider):
    """poll_current_aircraft (default order): adsb.lol unreachable degrades to single-source, not suppressed"""
    # adsb.lol unreachable (an outage, a block, or the future
    # feeder-contributed API key its own upstream documentation
    # pre-announces) must not take the display down - the default order
    # degrades to single-source, uncorroborated, exactly like the
    # explicit-provider equivalent.
    import requests
    stubbed_query_provider({
        "adsbfi": _runway3_record(),
        "adsblol": requests.RequestException("simulated adsb.lol outage"),
    })
    result = detect.poll_current_aircraft(geofence)
    assert result is not None, "a single reachable default provider was suppressed as if it were a disagreement"
    assert result["hex"] == "347288", "expected 347288, got %r" % (result["hex"],)
    assert result.get("corroborated") is None, (
        "expected corroborated None (no corroboration available), got %r" % (result.get("corroborated"),)
    )
    assert result.get("sources") == ["adsbfi"], "expected sources ['adsbfi'], got %r" % (result.get("sources"),)


def test_provider_keys_are_not_interchanged(fake_providers):
    """query_provider: adsb.fi and adsb.lol response keys are never interchanged (proven through the transport)"""
    # THE HIGHEST-CONSEQUENCE CHECK IN THIS FILE. adsb.fi and adsb.lol do
    # not share a response key ("aircraft" vs "ac"); query_provider()
    # reads `data.get(key) or []`, so a wrong key returns an empty list
    # with no exception, no log line, and no other failing test - the
    # provider would be silently scored as "saw nothing on runway 3"
    # forever, and corroboration would never occur. This proves the
    # mapping through the actual transport call (fake_providers, which
    # patches requests.get), against a payload carrying BOTH keys, rather
    # than trusting a dict literal in detect.PROVIDERS.
    aircraft_record = {"hex": "AAAAAA", "flight": "FROM_AIRCRAFT_KEY"}
    ac_record = {"hex": "BBBBBB", "flight": "FROM_AC_KEY"}
    payload = {"aircraft": [aircraft_record], "ac": [ac_record]}
    fake_providers.respond("adsblol", payload)
    fake_providers.respond("adsbfi", payload)

    lol_result = detect.query_provider("adsblol", 48.1, 2.2, 5)
    fi_result = detect.query_provider("adsbfi", 48.1, 2.2, 5)

    assert lol_result == [ac_record], "adsb.lol should read the 'ac' key, got %r" % (lol_result,)
    assert fi_result == [aircraft_record], "adsb.fi should read the 'aircraft' key, got %r" % (fi_result,)
    first_url = fake_providers.calls[0]["url"]
    assert first_url.startswith("https://api.adsb.lol/v2/point/"), (
        "expected the adsb.lol host to be requested first, got %r" % (first_url,)
    )
    assert first_url.endswith("/48.1/2.2/5"), "expected lat/lon/dist substituted into the URL, got %r" % (first_url,)


# ---------------------------------------------------------------
# Bounded provider GET and type-checked body
# ---------------------------------------------------------------

@pytest.mark.parametrize("body", [[], "x", {"aircraft": "x"}, {"aircraft": {"a": 1}}])
def test_query_provider_malformed_body_raises_value_error(fake_providers, body):
    """query_provider raises ValueError when the body is not a dict, or the aircraft value is neither None nor a list"""
    fake_providers.respond("adsbfi", body)
    with pytest.raises(ValueError):
        detect.query_provider("adsbfi", 48.1, 2.2, 5)


def test_query_provider_drops_non_dict_aircraft_records(fake_providers):
    """query_provider drops non-dict aircraft records before filter_in_geofence ever sees them"""
    valid_record = {"hex": "AAAAAA", "flight": "VALID001"}
    fake_providers.respond("adsblol", {"ac": [1, None, "x", valid_record]})
    result = detect.query_provider("adsblol", 48.1, 2.2, 5)
    assert result == [valid_record], "expected only the valid dict record to survive, got %r" % (result,)


def test_query_provider_null_or_missing_aircraft_key_is_empty(fake_providers):
    """query_provider returns [] (unchanged) for a null aircraft value or a missing key"""
    fake_providers.respond("adsblol", {"ac": None})
    assert detect.query_provider("adsblol", 48.1, 2.2, 5) == []
    fake_providers.respond("adsblol", {"unrelated": True})
    assert detect.query_provider("adsblol", 48.1, 2.2, 5) == []


def test_query_provider_non_2xx_raises_http_error_naming_no_url(fake_providers):
    """a 503 from a provider raises requests.HTTPError (a RequestException) naming the provider and status, not the URL"""
    fake_providers.respond("adsbfi", {"error": "unavailable"}, status=503)
    with pytest.raises(requests.HTTPError) as excinfo:
        detect.query_provider("adsbfi", 48.1, 2.2, 5)
    message = str(excinfo.value)
    assert "503" in message and "adsbfi" in message
    assert "opendata.adsb.fi" not in message, "the provider's URL must never appear in the error message"


def test_poll_current_aircraft_survives_one_malformed_provider(geofence, fake_providers):
    """poll_current_aircraft: a malformed adsbfi body fails only that provider, adsblol's own selection still comes back"""
    fixture = load_fixture("geofence_on_ground.json")
    fake_providers.respond("adsbfi", {"aircraft": "not-a-list"})
    fake_providers.respond("adsblol", {"ac": fixture["ac"]})
    diagnostics = {}
    result = detect.poll_current_aircraft(geofence, diagnostics=diagnostics)
    assert result is not None, "expected adsblol's own selection despite adsbfi's malformed body"
    assert result["hex"] == "3985a7", "expected the real on-ground runway-3 record, got %r" % (result["hex"],)
    assert diagnostics["failed"] == ["adsbfi"], "expected adsbfi recorded as failed, got %r" % (diagnostics["failed"],)
    assert diagnostics["selected"] == ["adsblol"], "expected adsblol recorded as selected, got %r" % (diagnostics["selected"],)


def test_poll_current_aircraft_survives_a_provider_deadline_exceeded(geofence, fake_providers, monkeypatch):
    """a DeadlineExceeded from bounded_get counts as that provider failing; the cycle still completes"""
    fixture = load_fixture("geofence_on_ground.json")
    fake_providers.respond("adsblol", {"ac": fixture["ac"]})
    real_bounded_get = http_fetch.bounded_get

    def fake_bounded_get(url, **kwargs):
        if "adsb.fi" in url:
            raise http_fetch.DeadlineExceeded("simulated deadline")
        return real_bounded_get(url, **kwargs)

    monkeypatch.setattr(detect.http_fetch, "bounded_get", fake_bounded_get)
    diagnostics = {}
    result = detect.poll_current_aircraft(geofence, diagnostics=diagnostics)
    assert result is not None, "expected adsblol's own selection despite adsbfi timing out"
    assert diagnostics["failed"] == ["adsbfi"], "expected adsbfi recorded as failed, got %r" % (diagnostics["failed"],)


def test_query_provider_passes_bounded_get_deadline_and_cap(monkeypatch):
    """query_provider passes PROVIDER_DEADLINE_S / PROVIDER_MAX_BYTES and the timeout 5.0 default through to bounded_get"""
    captured = {}

    def fake_bounded_get(url, *, headers, timeout, deadline_s, max_bytes):
        captured["timeout"] = timeout
        captured["deadline_s"] = deadline_s
        captured["max_bytes"] = max_bytes
        return http_fetch.FetchResult(200, b'{"aircraft": []}', {})

    monkeypatch.setattr(detect.http_fetch, "bounded_get", fake_bounded_get)
    detect.query_provider("adsbfi", 48.1, 2.2, 5)
    assert captured["timeout"] == detect.PROVIDER_TIMEOUT_S == 5.0
    assert captured["deadline_s"] == detect.PROVIDER_DEADLINE_S == 8.0
    assert captured["max_bytes"] == detect.PROVIDER_MAX_BYTES == 4 * 1024 * 1024


# ---------------------------------------------------------------
# On-ground pavement gate (missed-flights-not-displayed, 2026-08-27)
# ---------------------------------------------------------------

def test_masking_fixture_reproduces_the_precondition(geofence):
    """the taxiing masking record is in-bbox, track-aligned, inside the airborne corridor and outranks the real arrival (the pre-fix accept condition)"""
    # The masking fixture must genuinely reproduce the pre-fix
    # precondition, and - critically - must not be rejectable by any gate
    # that already existed. At +180m cross-track the taxiing record is
    # INSIDE the airborne corridor (half_width_m 500, deliberately
    # unchanged by this fix) and passes the track gate outright, and its
    # effective altitude 0.0 outranks the real arrival's 775ft. Without
    # this, test_taxiing_aircraft_no_longer_masks_real_runway3_traffic
    # could pass for a reason that has nothing to do with the bug.
    tagged = {ac["hex"]: ac for ac in detect.filter_in_geofence(_masking_snapshot(), geofence)}
    assert set(tagged) == {"3985a7", "347288"}, "expected both records in-bbox, got %r" % (sorted(tagged),)
    masker = tagged["3985a7"]
    assert masker.get("on_ground") and masker.get("in_bbox") and masker.get("below_ceiling"), (
        "the masking record must be on-ground, in-bbox and below-ceiling, got %r" % (
            {k: masker.get(k) for k in ("on_ground", "in_bbox", "below_ceiling")},
        )
    )
    assert masker.get("track_aligned"), (
        "the track gate rejected the masking record, so the regression check would no longer prove the "
        "lateral ground gate is what catches it"
    )
    half_width_m, _, _, ground_half_width_m = detect.corridor_params(geofence)
    cross = abs(masker["cross_track_m"])
    assert ground_half_width_m < cross <= half_width_m, (
        "the masking record must sit inside the AIRBORNE corridor but outside the ground gate to isolate the "
        "fix; got |cross|=%.1f with ground=%r air=%r" % (cross, ground_half_width_m, half_width_m)
    )
    assert detect.effective_altitude_ft(masker) < detect.effective_altitude_ft(tagged["347288"]), (
        "premise broken: the masking record no longer outranks the real arrival on the D-P2-01 sort key, "
        "so there is nothing left to mask"
    )


def test_taxiing_aircraft_no_longer_masks_real_runway3_traffic(geofence):
    """select_runway3_aircraft: a taxiing aircraft off the pavement no longer masks a real runway-3 movement"""
    # THE REGRESSION. A stationary/taxiing aircraft 180m off runway 3's
    # centreline used to win selection over a real runway-3 arrival,
    # purely because effective_altitude_ft() scores every on-ground
    # record at exactly 0.0. Its hex never changed, so the rendered panel
    # bytes never changed either and the display froze while real traffic
    # passed unseen. It must now fail the ground gate and the genuine
    # arrival must win.
    snapshot = _masking_snapshot()
    tagged = {ac["hex"]: ac for ac in detect.filter_in_geofence(snapshot, geofence)}
    assert not tagged["3985a7"].get("in_corridor"), (
        "the taxiing aircraft at 180m offset is still inside the corridor that applies to an on-ground record"
    )
    assert not tagged["3985a7"].get("on_runway3"), "the taxiing aircraft at 180m offset was still tagged on_runway3"
    assert tagged["347288"].get("on_runway3"), "the real runway-3 arrival stopped being tagged on_runway3"
    winner = detect.select_runway3_aircraft(snapshot, geofence)
    assert winner is not None, "expected the real runway-3 arrival to be selected, got None"
    assert winner["hex"] == "347288", (
        "the taxiing aircraft still masked the real runway-3 arrival: selected %r (alt %r) instead of 347288" % (
            winner["hex"], winner.get("altitude_ft"),
        )
    )


def test_ground_gate_keeps_real_runway3_ground_traffic(geofence):
    """the on-ground gate keeps the real runway-3 ground record (+31m) and rejects the documented 150m residual"""
    # The ground gate must not have been tightened into rejecting genuine
    # runway-3 ground traffic. This pins the empty measured band the
    # threshold sits in: the real on-ground runway-3 capture measures
    # +31.1m and must qualify, while the near edge of the documented
    # off-runway residual band (150m) must not. Runway 3's own published
    # paved half-width is 22.6m (OurAirports width_ft=148), so the
    # accepted record is ~8.5m of position error beyond the pavement edge.
    fixture = load_fixture("geofence_on_ground.json")
    tagged = {ac["hex"]: ac for ac in detect.filter_in_geofence(fixture["ac"], geofence)}
    real_ground = tagged["3985a7"]
    assert real_ground.get("on_ground"), "premise broken: fixture 3985a7 is no longer an on-ground record"
    cross = abs(real_ground["cross_track_m"])
    assert 30.0 <= cross <= 32.0, (
        "premise broken: the real on-ground runway-3 record no longer measures ~31m cross-track, got %.1f" % cross
    )
    assert real_ground.get("on_runway3"), (
        "the ground gate rejected the real on-ground runway-3 record at %.1fm - over-tightened" % cross
    )
    # ...and the near edge of the documented ~150-200m residual band must
    # be rejected, so the empty band between them stays empty.
    axis = detect.runway_axis(geofence)
    residual = dict(next(ac for ac in fixture["ac"] if ac["hex"] == "3985a7"))
    along, _ = detect.along_cross_track_m(residual["lat"], residual["lon"], geofence)
    dx = along * axis["ux"] - 150.0 * axis["uy"]
    dy = along * axis["uy"] + 150.0 * axis["ux"]
    residual["lat"] = axis["lat0"] + dy / detect._M_PER_DEG_LAT
    residual["lon"] = axis["lon0"] + dx / axis["lon_scale"]
    moved = detect.filter_in_geofence([residual], geofence)
    assert moved, "the 150m test point fell outside the bbox; check premise broken"
    assert not moved[0].get("on_runway3"), (
        "an on-ground aircraft 150m off the centreline - the near edge of the documented residual band - "
        "still qualified as runway 3"
    )


# ---------------------------------------------------------------
# Cross-source corroboration (missed-flights-not-displayed,
# mechanism B, 2026-08-28)
# ---------------------------------------------------------------

def test_pavement_pair_reproduces_the_precondition(geofence):
    """the pavement pair ties at effective altitude 0.0, is identical across both feeds except seen_pos, and the pre-fix key still splits them (the manufactured-disagreement precondition)"""
    # PRECONDITION - meant to hold BOTH before and after the fix. It
    # proves the fixture reproduces the bug's setup rather than proving
    # the fix: two aircraft both genuinely on runway 3's pavement, tied at
    # effective altitude exactly 0.0, present in both feeds at identical
    # positions, with the payloads differing in NOTHING but seen_pos - and
    # the pre-fix sort key nevertheless ordering them differently for each
    # feed. Without this, the regression checks below could pass for
    # reasons unrelated to the tie-break.
    picks = {}
    for provider in ("adsbfi", "adsblol"):
        records = _pavement(provider)
        tagged = {ac["hex"]: ac for ac in detect.filter_in_geofence(records, geofence)}
        assert set(tagged) == {"000003", "3985a7"}, "%s: expected both records in-bbox, got %r" % (provider, sorted(tagged))
        for h, ac in tagged.items():
            assert ac.get("on_ground") and ac.get("below_ceiling") and ac.get("on_runway3"), (
                "%s/%s must be an on-ground, below-ceiling, on-runway-3 record (runway3.json known_residuals "
                "item 3), got %r" % (provider, h, {
                    k: ac.get(k) for k in ("on_ground", "below_ceiling", "on_runway3", "cross_track_m")
                })
            )
            assert detect.effective_altitude_ft(ac) == 0.0, "%s/%s should score effective altitude exactly 0.0" % (provider, h)
        picks[provider] = min(tagged.values(), key=_prefix_sort_key)["hex"]

    fi = sorted((_strip_volatile(r) for r in _pavement("adsbfi")), key=lambda r: r["hex"])
    lol = sorted((_strip_volatile(r) for r in _pavement("adsblol")), key=lambda r: r["hex"])
    assert fi == lol, (
        "the two payloads must describe an IDENTICAL reality and differ only in seen_pos, otherwise the "
        "disagreement is not manufactured; they differ in more than that"
    )
    assert picks["adsbfi"] != picks["adsblol"], (
        "premise broken: the pre-fix (altitude, seen_pos, hex) key no longer orders these two feeds "
        "differently, so there is no manufactured disagreement left to reproduce (both picked %r)" % (picks["adsbfi"],)
    )


def test_selection_is_provider_independent(geofence):
    """select_runway3_aircraft: two feeds differing only in seen_pos select the SAME aircraft"""
    # THE REGRESSION, part 1 - the tie-break itself. Two feeds handed the
    # same two real aircraft at the same positions must select the same
    # one. Pre-fix the arbiter was `seen_pos`, a per-provider staleness
    # value whose spread between these two feeds is measured in
    # adsb-test/RESULTS.md at tens of seconds - so the feeds picked
    # different hexes purely from staleness noise.
    fi = detect.select_runway3_aircraft(_pavement("adsbfi"), geofence)
    lol = detect.select_runway3_aircraft(_pavement("adsblol"), geofence)
    assert fi is not None and lol is not None, "expected both feeds to select an aircraft, got %r / %r" % (fi, lol)
    assert fi["hex"] == lol["hex"], (
        "the same two aircraft at the same positions selected differently per feed (%s vs %s) - the sort key "
        "is still reading a provider-local field" % (fi["hex"], lol["hex"])
    )
    assert fi["hex"] == "000003", "expected the lexicographically smallest hex 000003 to win the altitude tie, got %r" % (fi["hex"],)


def test_identical_sets_are_not_manufactured_into_disagreement(geofence, stubbed_query_provider):
    """poll_current_aircraft (default order): two feeds differing only in seen_pos are corroborated, not suppressed"""
    # THE REGRESSION, part 2 - the cycle must no longer be thrown away.
    # Reached through the production default order (no providers
    # argument). Pre-fix this returned None and poll_loop took the
    # "leave the panel alone" branch, which is indistinguishable from an
    # empty sky: the panel froze while real runway-3 traffic passed.
    stubbed_query_provider({"adsbfi": _pavement("adsbfi"), "adsblol": _pavement("adsblol")})
    result = detect.poll_current_aircraft(geofence)
    assert result is not None, (
        "two feeds that agree completely about which aircraft are on runway 3 were still scored as a "
        "disagreement and the whole cycle was suppressed"
    )
    assert result["hex"] == "000003", "expected 000003, got %r" % (result["hex"],)
    assert result.get("corroborated") is True, "expected corroborated True, got %r" % (result.get("corroborated"),)
    assert sorted(result.get("sources") or []) == ["adsbfi", "adsblol"], (
        "expected both default providers in sources, got %r" % (result.get("sources"),)
    )


def test_asymmetric_sets_corroborate_the_common_aircraft(geofence, stubbed_query_provider):
    """poll_current_aircraft (default order): unequal candidate sets corroborate the common aircraft instead of suppressing (a stable tie-break alone would not have)"""
    # THE REGRESSION, part 3 - and the check that proves a stable
    # tie-break ALONE would not have been enough, which is the whole
    # reason this fix also changed what corroboration compares. adsb.lol
    # has not received the second aircraft yet: the feeds hold
    # overlapping-but-unequal candidate SETS, which no amount of
    # determinism can reconcile (adsb-test/RESULTS.md measures exactly
    # this asymmetry). Assertion (a) below pins that explicitly: even
    # under detect.py's own CURRENT deterministic key, the two feeds' per-
    # provider picks still differ, so a pick-only comparison would still
    # have suppressed this cycle. Neither feed ever claimed the other's
    # extra aircraft was absent.
    fi_records = _pavement("adsbfi")
    lol_records = [r for r in _pavement("adsblol") if r["hex"] != "000003"]

    # (a) determinism alone is provably insufficient here.
    fi_pick = detect.select_runway3_aircraft(fi_records, geofence)
    lol_pick = detect.select_runway3_aircraft(lol_records, geofence)
    assert fi_pick is not None and lol_pick is not None, "premise broken: both feeds must still select something"
    assert fi_pick["hex"] != lol_pick["hex"], (
        "premise broken: the two feeds' own deterministic picks now agree, so this check no longer proves "
        "that a stable tie-break alone would have left the cycle suppressed"
    )

    stubbed_query_provider({"adsbfi": fi_records, "adsblol": lol_records})
    result = detect.poll_current_aircraft(geofence)
    assert result is not None, (
        "one feed simply not having received an aircraft yet was scored as a disagreement and suppressed "
        "the whole cycle"
    )
    assert result["hex"] == "3985a7", (
        "expected the aircraft BOTH feeds saw (3985a7) to be selected, got %r - an aircraft only one feed "
        "carries must never be displayed as corroborated" % (result["hex"],)
    )
    assert result.get("corroborated") is True, "expected corroborated True, got %r" % (result.get("corroborated"),)
    assert sorted(result.get("sources") or []) == ["adsbfi", "adsblol"], (
        "expected both providers in sources, got %r" % (result.get("sources"),)
    )
    # Ordering stays load-bearing: the record returned must be the
    # FIRST-listed provider's (ARCHITECTURE.md), which for 3985a7 is
    # adsb.fi's seen_pos 56.972 - not adsb.lol's 3.4.
    assert result.get("seen_pos") == 56.972, (
        "expected adsb.fi's own record for the corroborated aircraft (seen_pos 56.972), got %r" % (result.get("seen_pos"),)
    )


def _disjoint_snapshot():
    """Two feeds whose runway-3 candidate sets have NOTHING in common,
    each holding more than one candidate. adsb.fi gets the pavement pair;
    adsb.lol gets two real captured aircraft (the runway-25 arrival and
    the multi-aircraft fixture's winner).
    """
    return (
        _pavement("adsbfi"),
        _runway3_record() + [
            ac for ac in load_fixture("geofence_multi_aircraft.json")["ac"] if ac["hex"] == "39d300"
        ],
    )


def _disjoint_poll(geofence, stubbed_query_provider):
    fi_records, lol_records = _disjoint_snapshot()
    fi_hexes = {ac.get("hex") for ac in detect.runway3_candidates(fi_records, geofence)}
    lol_hexes = {ac.get("hex") for ac in detect.runway3_candidates(lol_records, geofence)}
    stubbed_query_provider({"adsbfi": fi_records, "adsblol": lol_records})
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        result = detect.poll_current_aircraft(geofence)
    return fi_hexes, lol_hexes, result, captured.getvalue()


def test_genuinely_disjoint_sets_still_suppress(geofence, stubbed_query_provider):
    """poll_current_aircraft: genuinely disjoint candidate sets still suppress the cycle (the hold behaviour stays intact)"""
    # This hold behaviour MUST SURVIVE - meant to hold both BEFORE and
    # AFTER the fix. Its job is to fail if the fix ever guts the
    # cross-source safety net, not to fail pre-fix. The
    # disagreeing-providers checks above already
    # cover disjoint SINGLE-candidate sets; this covers the multi-
    # candidate case, which is precisely where comparing SETS could have
    # diverged from comparing PICKS. Two feeds naming entirely different
    # aircraft still means at most one is right, so nothing is selected
    # and the panel is left alone.
    fi_hexes, lol_hexes, result, logged = _disjoint_poll(geofence, stubbed_query_provider)
    assert len(fi_hexes) >= 2 and len(lol_hexes) >= 2, (
        "premise broken: this check must exercise the MULTI-candidate disjoint case, got %r / %r" % (
            sorted(fi_hexes), sorted(lol_hexes),
        )
    )
    assert not (fi_hexes & lol_hexes), "premise broken: the two candidate sets must be disjoint, got overlap %r" % (
        fi_hexes & lol_hexes,
    )
    assert result is None, "D-04 was gutted: two feeds with no aircraft in common still produced a selection (%r)" % (
        result and result["hex"],
    )
    assert "providers disagree" in logged, (
        "the suppression is now silent to the documented triage recipe - `journalctl -u skypane-poll | grep "
        "\"providers disagree\"` no longer matches; got %r" % (logged,)
    )


def test_disagreement_line_names_every_candidate(geofence, stubbed_query_provider):
    """poll_current_aircraft: the disagreement line names every candidate each feed saw, not just the winners"""
    # The disagreement line must name every CANDIDATE, not just each
    # feed's winner. This is not cosmetic: corroboration now compares
    # candidate sets, so a log line that still printed only the two
    # winners would be describing something the code no longer does - and
    # the debug session's whole triage recipe for telling mechanism B
    # apart from an empty sky rests on this one stderr line. Pre-fix the
    # line named only the winners, so this check fails against the old
    # implementation.
    fi_hexes, lol_hexes, result, logged = _disjoint_poll(geofence, stubbed_query_provider)
    assert result is None, "premise broken: this snapshot must suppress"
    for expected in sorted(fi_hexes | lol_hexes):
        assert expected in logged, (
            "the disagreement line must name every candidate both feeds saw, not just the two winners; %r "
            "missing from %r" % (expected, logged)
        )


# ---------------------------------------------------------------
# Runway-parameterised detection, positive tracking on all three Orly
# runways
# ---------------------------------------------------------------
#
# Every synthetic coordinate below is derived arithmetically from
# coordinates already present in adsb-test/runway3.json - either read
# straight off the file or produced by walking one of detect.py's own
# runway axes (_on_axis_record()) - never a hand-guessed latitude/
# longitude literal.

def test_runways_3_matches_legacy_blocks(geofence):
    """runways['3'] duplicates the legacy runway/corridor blocks exactly (drift guard)"""
    # Task 1's deliberate duplication drift guard: runways["3"]'s
    # runway/corridor sub-blocks must equal the legacy flat
    # runway/corridor pair exactly.
    #
    # `ground_half_width_m` is deliberately NOT in the compared set: the
    # measured derivation for the on-ground pavement gate lives on the
    # legacy top-level corridor block, and the per-runway blocks omit it.
    # That is only safe while both paths resolve to the SAME number,
    # which the second half of this check pins directly through
    # corridor_params() rather than by comparing dict literals - if the
    # file's figure is ever changed without adding it to runways["3"],
    # runway 3's ground gate would silently revert to the module default
    # and this check fails.
    entry = geofence["runways"]["3"]
    expected_thresholds = [geofence["runway"]["threshold_07"], geofence["runway"]["threshold_25"]]
    assert entry["runway"]["thresholds"] == expected_thresholds, (
        "runways['3'].runway.thresholds does not match [threshold_07, threshold_25]"
    )
    expected_corridor = {k: geofence["corridor"][k] for k in ("half_width_m", "extension_m", "axis_tolerance_deg")}
    assert entry["corridor"] == expected_corridor, "runways['3'].corridor does not match the legacy corridor block"
    resolved_ground = detect.corridor_params(geofence, runway_id="3")[3]
    assert resolved_ground == geofence["corridor"]["ground_half_width_m"], (
        "runway 3's resolved ground gate (%r) no longer equals the legacy corridor block's measured "
        "ground_half_width_m (%r) - add it to runways['3'].corridor" % (
            resolved_ground, geofence["corridor"]["ground_half_width_m"],
        )
    )


def test_default_runway_id_matches_explicit_default(geofence):
    """runway_axis(geofence) matches runway_axis(geofence, runway_id='3')"""
    # runway_axis() with no runway_id and with the explicit default id
    # must return identical dicts - the new-shape runways['3'] entry is
    # provably interchangeable with omitting runway_id entirely.
    assert detect.runway_axis(geofence) == detect.runway_axis(geofence, runway_id="3"), (
        "runway_axis(geofence) != runway_axis(geofence, runway_id='3')"
    )


def test_neighbouring_runway_bearings_match_published_headings(geofence):
    """runway_axis: 06-24/02-20 computed bearings match their published true headings"""
    # The computed axes for 06/24 and 02/20 cross-check against the
    # published true headings already recorded in runway3.json.
    bearing_0624 = detect.runway_axis(geofence, runway_id="06-24")["bearing_deg"]
    assert abs(bearing_0624 - 62.0) <= 1.0, "expected 06-24 bearing within 1.0 deg of 62, got %r" % (bearing_0624,)
    bearing_0220 = detect.runway_axis(geofence, runway_id="02-20")["bearing_deg"]
    assert abs(bearing_0220 - 18.0) <= 1.0, "expected 02-20 bearing within 1.0 deg of 18, got %r" % (bearing_0220,)


def test_unknown_runway_id_falls_back_to_default_axis(geofence):
    """runway_axis(runway_id='totally-unknown') falls back to the default runway's axis"""
    # An unrecognised runway_id lands on the default runway's geometry -
    # never None, never an exception, never a different (widened) gate.
    default_axis = detect.runway_axis(geofence)
    unknown_axis = detect.runway_axis(geofence, runway_id="totally-unknown")
    assert unknown_axis == default_axis, "runway_axis(runway_id='totally-unknown') != the default axis"


def test_corridor_params_for_02_20_and_malformed_fallback(geofence):
    """corridor_params(runway_id='02-20') matches the file, negative entries fall back to the default"""
    # corridor_params() for a real neighbouring runway returns its own
    # numbers; a hand-mutated negative entry falls back to the module
    # default rather than accepting it.
    #
    # The 4th element is the on-ground pavement gate merged in from the
    # missed-flights-not-displayed session. The per-runway corridor
    # blocks do not carry `ground_half_width_m`, so a neighbouring runway
    # resolves it to DEFAULT_GROUND_HALF_WIDTH_M - the tight direction,
    # and the same 75.0 runway 3 gets from the file.
    half_width, extension, tolerance, ground_half_width = detect.corridor_params(geofence, runway_id="02-20")
    expected = geofence["runways"]["02-20"]["corridor"]
    assert (half_width, extension, tolerance) == (
        expected["half_width_m"], expected["extension_m"], expected["axis_tolerance_deg"],
    ), "corridor_params(runway_id='02-20') did not match runway3.json's own numbers"
    assert ground_half_width == detect.DEFAULT_GROUND_HALF_WIDTH_M, (
        "a runway block carrying no ground_half_width_m must resolve to the module default, got %r" % (ground_half_width,)
    )
    mutated = json.loads(json.dumps(geofence))  # deep copy without a new import
    mutated["runways"]["02-20"]["corridor"]["half_width_m"] = -5
    fallback_half_width, _, _, _ = detect.corridor_params(mutated, runway_id="02-20")
    assert fallback_half_width == detect.DEFAULT_CORRIDOR_HALF_WIDTH_M, (
        "a negative half_width_m was not rejected, got %r" % (fallback_half_width,)
    )


def test_positive_tracking_on_neighbouring_runways(geofence):
    """select_aircraft_for_runway positively tracks 06-24 and 02-20 on their own centrelines"""
    # Positive tracking on both neighbouring runways: a synthetic record
    # on 06/24's (resp. 02/20's) own centreline, aligned with its own
    # track, is selected when tracking that runway and rejected by the
    # runway-3 default gate.
    for runway_id in ("06-24", "02-20"):
        record = _on_axis_record(geofence, runway_id, 0.5, "TEST%s" % runway_id.replace("-", ""))
        own_selection = detect.select_aircraft_for_runway([record], geofence, runway_id=runway_id)
        assert own_selection is not None, "%s: a record on its own centreline, on-axis, was not selected" % runway_id
        assert own_selection.get("selected_runway") == runway_id, (
            "%s: selected_runway was %r" % (runway_id, own_selection.get("selected_runway"))
        )
        default_selection = detect.select_runway3_aircraft([record], geofence)
        assert default_selection is None, "%s: the same record was also selected as runway 3" % runway_id


def test_real_runway3_fixture_excluded_from_06_24(geofence):
    """the real runway-3 fixture is excluded from runway 06-24's gate (exclusive both ways)"""
    # Reverse direction: the real committed runway-3 fixture is still
    # selected with the default id and is NOT selected with
    # runway_id="06-24" - the gate is exclusive both ways, not merely
    # permissive.
    record = _runway3_record()
    assert detect.select_runway3_aircraft(record, geofence) is not None, (
        "premise broken: the real runway-3 fixture is no longer selected by default"
    )
    assert detect.select_aircraft_for_runway(record, geofence, runway_id="06-24") is None, (
        "the real runway-3 fixture was also selected as runway 06-24"
    )


def test_selected_runway_key_reports_effective_id(geofence):
    """selected_runway equals the requested id, or the default id on an unrecognised request"""
    # selected_runway carries the requested id when recognised, and the
    # default id (the one it actually fell back to) when not.
    record = _on_axis_record(geofence, "02-20", 0.5, "TESTSR01")
    selection = detect.select_aircraft_for_runway([record], geofence, runway_id="02-20")
    assert selection is not None and selection.get("selected_runway") == "02-20", (
        "expected selected_runway '02-20', got %r" % (selection and selection.get("selected_runway"),)
    )
    fallback_record = _on_axis_record(geofence, "3", 0.5, "TESTSR02")
    fallback_selection = detect.select_aircraft_for_runway([fallback_record], geofence, runway_id="not-a-runway")
    assert fallback_selection is not None and fallback_selection.get("selected_runway") == detect.DEFAULT_RUNWAY_ID, (
        "expected selected_runway to fall back to %r, got %r" % (
            detect.DEFAULT_RUNWAY_ID, fallback_selection and fallback_selection.get("selected_runway"),
        )
    )


def test_on_runway_and_deprecated_alias_tags(geofence):
    """filter_in_geofence tags carry on_runway and the deprecated on_runway3 alias correctly"""
    # filter_in_geofence() tags carry both on_runway (the real gate result
    # for the requested runway_id) and the deprecated on_runway3 alias,
    # which is False whenever a non-default runway was requested.
    record = _on_axis_record(geofence, "06-24", 0.5, "TESTALIAS")
    tagged_default = detect.filter_in_geofence([record], geofence)[0]
    assert tagged_default.get("on_runway") == tagged_default.get("on_runway3"), (
        "on_runway3 should equal on_runway for the default runway_id"
    )
    tagged_0624 = detect.filter_in_geofence([record], geofence, runway_id="06-24")[0]
    assert tagged_0624.get("on_runway"), "expected on_runway True when gated on its own runway (06-24)"
    assert tagged_0624.get("on_runway3") is False, "expected the deprecated on_runway3 alias to be False for a non-default runway_id"


def test_diagnostics_distinguishes_all_failed_from_no_selection(geofence, monkeypatch, stubbed_query_provider):
    """poll_current_aircraft diagnostics distinguishes all-providers-failed from a real selection"""
    # poll_current_aircraft()'s diagnostics dict is the sole signal that
    # tells "every source errored" apart from "nothing on the runway" -
    # both currently return None. Driven entirely by monkeypatching
    # detect.query_provider, so no real network call is ever made.
    import requests

    network_called = []

    def _all_raise(name, lat, lon, radius_nm, timeout=10.0):
        network_called.append(name)
        raise requests.RequestException("simulated outage: %s" % name)

    monkeypatch.setattr(detect, "query_provider", _all_raise)
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0)
    diagnostics = {}
    result = detect.poll_current_aircraft(geofence, diagnostics=diagnostics)

    assert result is None, "expected None when every provider raised, got %r" % (result,)
    assert sorted(diagnostics.get("queried") or []) == sorted(diagnostics.get("failed") or []), (
        "expected diagnostics['queried'] == diagnostics['failed'], got %r vs %r" % (
            diagnostics.get("queried"), diagnostics.get("failed"),
        )
    )
    assert network_called, "expected the stubbed query function to have been called at least once"

    # Second variant: one provider raises, the other returns a real
    # selection - failed has exactly one entry, corroborated is the
    # single-source "unknown" value (None), not suppressed.
    stubbed_query_provider({"adsbfi": _runway3_record(), "adsblol": requests.RequestException("simulated outage")})
    diagnostics2 = {}
    result2 = detect.poll_current_aircraft(geofence, diagnostics=diagnostics2)
    assert result2 is not None, "expected a selection when one of two providers succeeded"
    assert result2.get("corroborated") is None, "expected corroborated None (single source), got %r" % (result2.get("corroborated"),)
    assert diagnostics2.get("failed") == ["adsblol"], "expected diagnostics2['failed'] == ['adsblol'], got %r" % (
        diagnostics2.get("failed"),
    )

