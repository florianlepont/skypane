#!/usr/bin/env python3
"""The systemd-timer oneshot entrypoint: detect -> render -> atomic swap
(PLANE-03, D-04, D-P2-02).

Poll cadence decision: **30 seconds**, matching Phase 1's validated sampler
interval (adsb-test/RESULTS.md) and comfortably inside both aggregators'
1 req/s limit given one call per cycle. This script itself has no
`while True: sleep()` loop and no APScheduler - it is a single-cycle
oneshot invoked repeatedly by a systemd `.timer`/`.service` unit pair; the
timer unit that actually drives the 30s cadence lands in plan 02-05, not
this plan (02-RESEARCH.md's Don't Hand-Roll table).

Cross-cycle state (D-P2-02): this script has no in-process memory between
invocations, so the last detected flight, last chosen state, and the
unrecognized-ICAO-prefix registry (quick task 260827-oz9 - journald rotates,
the coverage question does not) all live in `<state_dir>/poll_state.json`,
written with the same tmp-write-then-os.replace() pattern
stub-server/byos_server.py's save_state() uses. An unreadable or malformed
state file is treated as empty state, never as a crash.

Usage:
    server/.venv/bin/python3 server/poll_loop.py --once
    server/.venv/bin/python3 server/poll_loop.py --once --state-dir /tmp/x
"""
import argparse
import hashlib
import json
import os
import sys

# Allow both `import server.poll_loop` (package import) and direct script
# execution (`python3 server/poll_loop.py`, where sys.path[0] is server/
# itself and the repo root must be added by hand before the absolute
# `server.plane.*` imports below can resolve).
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import server.plane.detect as detect
import server.plane.enrich as enrich
import server.plane.render as render
import server.plane.runway_config as runway_config

DEFAULT_STATE_DIR = os.path.join(_HERE, "state")
POLL_INTERVAL_S = 30


def _extract_aircraft(snapshot):
    """A raw aggregator response dict (as injected by tests, or as returned
    by one of detect.PROVIDERS) carries its aircraft array under a
    provider-specific key ("ac" for airplanes.live and adsb.lol, "aircraft"
    for adsb.fi). Never raises on an unexpected shape - an empty list is
    the safe default (T-02-01-01's "skip/don't-claim" discipline).
    """
    if not isinstance(snapshot, dict):
        return []
    for key in ("ac", "aircraft"):
        value = snapshot.get(key)
        if isinstance(value, list):
            return value
    return []


def _classify_state_source(vertical_rate_fpm):
    """Was this cycle's confirmed state newly inferred from a vertical-rate
    reading that actually crossed a D-P2-04 threshold, or held over from a
    prior cycle because this reading sat inside the deadband (or was
    missing/non-numeric)? Log-only classification - mirrors
    runway_config.infer_runway_config()'s own branches without duplicating
    its threshold constants as literals.
    """
    if isinstance(vertical_rate_fpm, bool):
        return "held"
    if not isinstance(vertical_rate_fpm, (int, float)):
        return "held"
    if vertical_rate_fpm >= runway_config.CLIMB_THRESHOLD_FPM or vertical_rate_fpm <= runway_config.DESCEND_THRESHOLD_FPM:
        return "inferred"
    return "held"


def _poll_state_path(state_dir):
    return os.path.join(state_dir, "poll_state.json")


def load_poll_state(state_dir):
    """Missing, unreadable, or malformed -> empty state (D-P2-02), never a
    crash.
    """
    try:
        with open(_poll_state_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_poll_state(state_dir, state):
    """Atomic tmp-write-then-os.replace(), matching
    stub-server/byos_server.py's save_state() (T-02-01-03 / V12). Never
    leaves a stray .tmp file behind, even if the write itself fails.
    """
    path = _poll_state_path(state_dir)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(state, fh, indent=1)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def write_panel_atomic(state_dir, rendered):
    """Write `rendered` (packed panel bytes) to <state_dir>/panel.bin only
    if its SHA-256 differs from the currently-served bytes (T-02-01-03 /
    V12) - tmp-write-then-os.replace(), so byos_server.py can never serve a
    half-written file. Returns True if the served panel actually changed.
    """
    panel_path = os.path.join(state_dir, "panel.bin")
    if os.path.exists(panel_path):
        with open(panel_path, "rb") as fh:
            existing = fh.read()
        if hashlib.sha256(existing).hexdigest() == hashlib.sha256(rendered).hexdigest():
            return False

    tmp = panel_path + ".tmp"
    try:
        with open(tmp, "wb") as fh:
            fh.write(rendered)
        os.replace(tmp, panel_path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
    return True


def run_once(snapshot=None, state_dir=None, geofence=None):
    """One poll cycle. `snapshot=None` polls the live aggregators
    (detect.poll_current_aircraft()); a non-None `snapshot` is a raw
    aggregator response dict injected by the test harness so
    test_pipeline_e2e.py is fully hermetic (no live network call).

    Returns a small result dict: {"flight": ..., "state": ..., "panel_changed": ...}.

    Never logs a bearer token or BYOS setup secret - this module has no
    access to either; only the selected hex/callsign/altitude/state and
    whether the panel changed are printed (T-02-01-04).
    """
    state_dir = state_dir or DEFAULT_STATE_DIR
    os.makedirs(state_dir, exist_ok=True)
    geofence_data = detect.load_geofence(geofence)

    if snapshot is not None:
        aircraft = _extract_aircraft(snapshot)
        flight = detect.select_runway3_aircraft(aircraft, geofence_data)
    else:
        flight = detect.poll_current_aircraft(geofence_data)

    poll_state = load_poll_state(state_dir)
    last_flight = poll_state.get("last_flight")
    last_confirmed_state = poll_state.get("last_confirmed_state")
    last_route = poll_state.get("last_route")
    previous_flight = poll_state.get("previous_flight")
    previous_confirmed_state = poll_state.get("previous_confirmed_state")
    previous_route = poll_state.get("previous_route")
    # quick task 260827-oz9: only the flight-detected branch below can ever
    # set this, but every branch (including the two no-detection branches)
    # falls through to the single shared log statement at the bottom, so
    # it must be defined here, before any branching, or an ordinary cycle
    # that detects nothing raises UnboundLocalError.
    unknown_prefix = None

    if flight is not None:
        # D-25 (03-CONTEXT.md): two-deep flight history for the poster's
        # current+previous layout. A genuinely NEW aircraft (a different
        # hex than the current "last_flight") shifts the old current
        # flight - and its resolved state/route - down into "previous"
        # BEFORE this cycle's detection overwrites "last_flight" below.
        # Re-detecting the SAME aircraft across consecutive poll cycles
        # (same hex) must NOT shift anything - it is still the same
        # current flight, not a new one.
        new_hex = flight.get("hex")
        old_hex = last_flight.get("hex") if isinstance(last_flight, dict) else None
        if last_flight is not None and new_hex != old_hex:
            previous_flight = last_flight
            previous_confirmed_state = last_confirmed_state
            previous_route = last_route

        # D-03/D-P2-04: real runway-configuration inference from the
        # aircraft's own vertical rate, with a deadband and hold-last-state
        # behaviour (server.plane.runway_config). Replaces the 02-01 stub
        # that hardcoded every detected flight as "arriving".
        confirmed_state = runway_config.infer_from_flight(flight, last_confirmed_state)
        state_source = _classify_state_source(flight.get("vertical_rate_fpm"))
        if confirmed_state is None:
            # A first-ever detection whose vertical rate sits inside the
            # deadband - nothing can be concluded yet. Render the Empty
            # state rather than guessing a colour: an unknown runway
            # configuration must not be shown as a confident Blue/Green
            # field.
            render_state = "empty"
            route_source = "n/a"
            route = None
            rendered = render.render_panel(None, render_state)
        else:
            render_state = confirmed_state
            # D-02/D-P2-05: resolve the airline + route for zones 7/9 via a
            # persistent, callsign-keyed cache (D-P2-02 - this cache lives
            # in poll_state.json, not in-process, since this script is a
            # systemd oneshot with no memory between invocations).
            cache = poll_state.get("enrichment_cache")
            if not isinstance(cache, dict):
                cache = {}
            # D-05 (quick task 260827-hyy): a single seam now classifies
            # four categories, not three - "fresh_hit"/"cache_hit" mean
            # exactly what they always did (a cached *miss* is still a
            # "miss" here, not a "cache hit" - "cache hit" means the cache
            # spared us a request AND returned a usable route); the new
            # fourth category, "airline_only", means adsbdb had no route
            # this cycle but the callsign's ICAO prefix identified the
            # carrier from a static in-repo table - no additional network
            # call, no additional cache entry. Nothing derived from the
            # adsbdb response body is ever logged, on any of the four paths.
            route, route_source = enrich.resolve_route(flight.get("callsign"), cache)
            enrich.trim_cache(cache)
            poll_state["enrichment_cache"] = cache
            # quick task 260827-oz9: a "miss" means neither adsbdb nor the
            # static prefix table resolved anything for a shape-valid
            # callsign - exactly "unrecognized ICAO prefix". Record it into
            # the same durable poll_state.json this cycle already writes,
            # so the finding survives this oneshot's process boundary.
            # Never called for "airline_only"/"fresh_hit"/"cache_hit" (a
            # source resolved something) or "held"/"n/a" (no enrichment
            # ran this cycle at all).
            unresolved_prefixes = poll_state.get("unresolved_prefixes")
            if not isinstance(unresolved_prefixes, dict):
                unresolved_prefixes = {}
            if route_source == "miss":
                unknown_prefix = enrich.note_unresolved_prefix(flight.get("callsign"), unresolved_prefixes)
            enrich.trim_unresolved_prefixes(unresolved_prefixes)
            poll_state["unresolved_prefixes"] = unresolved_prefixes
            # D-25/D-26: the previous flight's own real illustration/text
            # rides along on the same panel as the current detection's.
            rendered = render.render_panel(
                flight,
                render_state,
                route=route,
                previous_flight=previous_flight,
                previous_route=previous_route,
                previous_state=previous_confirmed_state,
            )
        panel_changed = write_panel_atomic(state_dir, rendered)
        poll_state["last_flight"] = flight
        poll_state["last_confirmed_state"] = confirmed_state
        poll_state["last_route"] = route
        poll_state["previous_flight"] = previous_flight
        poll_state["previous_confirmed_state"] = previous_confirmed_state
        poll_state["previous_route"] = previous_route
        save_poll_state(state_dir, poll_state)
    elif last_flight is not None:
        # D-04: nothing detected this cycle, but a flight was already on
        # screen - do nothing to panel.bin. No waiting state, no expiry.
        confirmed_state = last_confirmed_state
        render_state = confirmed_state if confirmed_state is not None else "empty"
        state_source = "held"
        route_source = "held"
        panel_changed = False
    else:
        # Nothing detected, and nothing has ever been detected since the
        # state directory was last empty - render the Empty state.
        confirmed_state = None
        render_state = "empty"
        state_source = "held"
        route_source = "n/a"
        rendered = render.render_panel(None, render_state)
        panel_changed = write_panel_atomic(state_dir, rendered)

    # T-02-04-05: log only the callsign, the enrichment outcome
    # (cache_hit / fresh_hit / miss / n/a / held), and the selection's own
    # corroboration flag - a three-state provenance signal about this
    # project's own ADS-B sources, not third-party response content, so it
    # stays within this rule - never the raw adsbdb response body.
    # quick task 260827-oz9: unknown_prefix is the first three characters
    # of the callsign this same line already prints in full, derived from
    # this project's own selected-aircraft record - not from any
    # third-party response body - so it stays within the rule above too.
    print(
        "poll_loop: hex=%s callsign=%s aircraft_type=%s corroborated=%s altitude_ft=%s confirmed_state=%s "
        "render_state=%s state_source=%s route_source=%s unknown_prefix=%s panel_changed=%s"
        % (
            (flight or {}).get("hex"),
            (flight or {}).get("callsign"),
            (flight or {}).get("aircraft_type"),
            (flight or {}).get("corroborated"),
            (flight or {}).get("altitude_ft"),
            confirmed_state,
            render_state,
            state_source,
            route_source,
            unknown_prefix,
            panel_changed,
        )
    )

    return {"flight": flight, "state": render_state, "panel_changed": panel_changed}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll cycle and exit. This script is always single-cycle "
             "(a systemd timer, added in plan 02-05, drives the 30s repeat cadence) - "
             "accepted for explicitness at the CLI.",
    )
    parser.add_argument(
        "--state-dir",
        default=DEFAULT_STATE_DIR,
        help="Directory holding panel.bin / poll_state.json (default: server/state/).",
    )
    parser.add_argument(
        "--geofence",
        default=None,
        help="Path to the geofence JSON (default: adsb-test/runway3.json).",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        run_once(state_dir=args.state_dir, geofence=args.geofence)
    except Exception as exc:
        # A failed cycle must leave the previously served panel intact and
        # never crash-loop the systemd timer silently - log to stdout
        # (journald captures this) and exit non-zero.
        print("poll_loop: cycle failed: %s: %s" % (type(exc).__name__, exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
