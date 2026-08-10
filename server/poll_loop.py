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
invocations, so the last detected flight and last chosen state live in
`<state_dir>/poll_state.json`, written with the same tmp-write-then-
os.replace() pattern stub-server/byos_server.py's save_state() uses. An
unreadable or malformed state file is treated as empty state, never as a
crash.

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
import server.plane.render as render
import server.plane.runway_config as runway_config

DEFAULT_STATE_DIR = os.path.join(_HERE, "state")
POLL_INTERVAL_S = 30


def _extract_aircraft(snapshot):
    """A raw aggregator response dict (as injected by tests, or as returned
    by one of detect.PROVIDERS) carries its aircraft array under a
    provider-specific key ("ac" for airplanes.live, "aircraft" for
    adsb.fi). Never raises on an unexpected shape - an empty list is the
    safe default (T-02-01-01's "skip/don't-claim" discipline).
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

    if flight is not None:
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
            rendered = render.render_panel(None, render_state)
        else:
            render_state = confirmed_state
            rendered = render.render_panel(flight, render_state)
        panel_changed = write_panel_atomic(state_dir, rendered)
        poll_state["last_flight"] = flight
        poll_state["last_confirmed_state"] = confirmed_state
        save_poll_state(state_dir, poll_state)
    elif last_flight is not None:
        # D-04: nothing detected this cycle, but a flight was already on
        # screen - do nothing to panel.bin. No waiting state, no expiry.
        confirmed_state = last_confirmed_state
        render_state = confirmed_state if confirmed_state is not None else "empty"
        state_source = "held"
        panel_changed = False
    else:
        # Nothing detected, and nothing has ever been detected since the
        # state directory was last empty - render the Empty state.
        confirmed_state = None
        render_state = "empty"
        state_source = "held"
        rendered = render.render_panel(None, render_state)
        panel_changed = write_panel_atomic(state_dir, rendered)

    print(
        "poll_loop: hex=%s callsign=%s altitude_ft=%s confirmed_state=%s render_state=%s "
        "state_source=%s panel_changed=%s"
        % (
            (flight or {}).get("hex"),
            (flight or {}).get("callsign"),
            (flight or {}).get("altitude_ft"),
            confirmed_state,
            render_state,
            state_source,
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
