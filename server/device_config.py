#!/usr/bin/env python3
"""Single source of truth for every user-settable SkyPane device setting
(D-01/D-10/D-26, 06-CONTEXT.md) - today that means the CFG-01 theme id and
the CFG-12 tracked-runway id, both picked on the companion web page and
consumed by the poll pipeline on the device's next scheduled poll (D-06).

This is a **separate** file (`device_config.json`) from `poll_state.json`,
deliberately: `server/poll_loop.py` read-modify-writes `poll_state.json`
every 30 seconds, and a second writer touching that same file would
silently lose one side of the race (06-RESEARCH.md Pitfall 5 - two
processes read-modify-writing the same JSON file without coordination).
Keeping the user-settable config in its own file means the companion
service and the poll oneshot never contend for the same lock-free file.

This module is a **leaf**: it imports only the Python stdlib plus
`server.panel_format`. It must never import `server.plane.detect`,
`server.plane.render`, or `server.poll_loop` - those modules (will) import
this one, and the reverse direction would be a cycle.

Adding a theme (Phase 7 and beyond): append one entry to `THEMES` keyed by
a new short id, supplying `departing_index`, `arriving_index`, `ink_index`,
and `label`. No structural change to this module and no call-site change
anywhere else is required - `THEME_IDS`, `normalise_theme_id()`, and every
presentation accessor below derive from `THEMES` itself. This is the
concrete discharge of 03-CONTEXT.md's D-11 carried-forward obligation:
Phase 7's on-glass session is where additional real, hardware-validated
theme entries actually get added.

This module is print-free by design - never log or print the config
file's contents. There is no secret in it, but it must stay safe to import
from an HTTP request handler without accidentally becoming a place a
future change could leak state into a log.
"""
import json
import os
import sys

# Allow both `import server.device_config` (package import) and direct
# script execution, matching server/poll_loop.py's own bootstrap (lines
# 31-38): sys.path[0] is server/ itself when this file is executed
# directly, so the repo root must be added by hand before the absolute
# `server.panel_format` import below can resolve.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server.panel_format import IDX_BLUE, IDX_GREEN, IDX_WHITE

DEFAULT_THEME_ID = "sky"
DEFAULT_RUNWAY_ID = "3"
DEFAULT_LED_ENABLED = True  # D-02: matches the LED's current hardcoded always-on behaviour, so nothing changes until a user opts out

# --- Theme registry ----------------------------------------------------
#
# D-09/D-10/D-11 (06-CONTEXT.md): the "sky" entry below is the *only*
# theme today. Its Blue/Green hues were confirmed against on-screen
# previews only through D-21 (03-CONTEXT.md) - Phase 7's on-glass session
# (07-01, hardware/BRINGUP-LOG.md's "Phase 7 On-Glass Verification" entry)
# was the first time this design met real glass, and it found both hues
# genuinely too dark/saturated on the real panel versus the monitor
# preview. panel_format.PALETTE_RGB's Blue/Green triples were darkened
# accordingly (see that module's own comment block for the before/after
# values) - this THEMES dict references panel_format.IDX_BLUE/IDX_GREEN
# indirectly and needed no change itself, since the real-glass tuning
# lives entirely in the RGB triples those indices point at. Any additional
# selectable theme entries should be real-glass-validated the same way
# before landing here. Never write a bare palette integer here - always
# reference panel_format's named IDX_* constants, matching that module's
# own stated discipline.
THEMES = {
    "sky": {
        "departing_index": IDX_BLUE,
        "arriving_index": IDX_GREEN,
        "ink_index": IDX_WHITE,
        "label": "Sky (default)",
    },
}

# --- Runway registry -----------------------------------------------------
#
# CFG-12 (D-26/D-27/D-28, 06-CONTEXT.md): these three keys must stay equal
# to adsb-test/runway3.json's `runway`/`neighbouring_runways` key set - the
# consistency check lives in plan 06-10's test_poll_loop.py, not here.
# `tag_text`/`empty_heading` for "3" are byte-identical to render.py's
# current TOP_RIGHT_TAG_TEXT/EMPTY_HEADING_TEXT so the default render is
# unchanged; the "06-24"/"02-20" entries use the same "ORY · RWY ..."/
# "Watching Runway ..." shape with the U+00B7 middle-dot separator.
RUNWAYS = {
    "3": {
        "label": "Runway 3 (07/25)",
        "tag_text": "ORY · RWY 3",
        "empty_heading": "Watching Runway 3",
    },
    "06-24": {
        "label": "Runway 06/24",
        "tag_text": "ORY · RWY 06/24",
        "empty_heading": "Watching Runway 06/24",
    },
    "02-20": {
        "label": "Runway 02/20",
        "tag_text": "ORY · RWY 02/20",
        "empty_heading": "Watching Runway 02/20",
    },
}

THEME_IDS = tuple(THEMES)
RUNWAY_IDS = tuple(RUNWAYS)

DEVICE_CONFIG_FILENAME = "device_config.json"


def device_config_path(state_dir):
    return os.path.join(state_dir, DEVICE_CONFIG_FILENAME)


def normalise_theme_id(value):
    """Return `value` unchanged only when it is a string AND a member of
    `THEMES` - otherwise return `DEFAULT_THEME_ID`. Never raises, and never
    uses `value` as a dict key without the membership test first (T-06-01-01,
    ASVS V5) - an unrecognised, hostile, or wrong-typed value degrades to
    the documented default instead of ever reaching a lookup.
    """
    if isinstance(value, str) and value in THEMES:
        return value
    return DEFAULT_THEME_ID


def normalise_runway_id(value):
    """Same contract as normalise_theme_id(), against RUNWAYS/DEFAULT_RUNWAY_ID."""
    if isinstance(value, str) and value in RUNWAYS:
        return value
    return DEFAULT_RUNWAY_ID


def normalise_led_enabled(value):
    """Return `value` unchanged only when `isinstance(value, bool)` is true -
    otherwise return `DEFAULT_LED_ENABLED`. Never raises. Deliberately no
    registry/membership test (unlike normalise_theme_id()/
    normalise_runway_id()) - a boolean has no attributes beyond itself, so a
    LED_STATES registry mirroring THEMES/RUNWAYS would be pure indirection
    (06.2-RESEARCH.md "Alternatives Considered"). Note: an int such as `0`
    or `1` is NOT a bool under `isinstance` in Python and therefore degrades
    to the default - this is intentional, not an oversight.
    """
    if isinstance(value, bool):
        return value
    return DEFAULT_LED_ENABLED


def load_device_config(state_dir):
    """Read `<state_dir>/device_config.json`; a missing file, an unreadable
    file, a malformed document, or a non-dict document all fall back to an
    empty dict rather than raising. Always returns all three keys with
    valid values - `theme`, `tracked_runway`, and `led_enabled` - via
    normalise_theme_id()/normalise_runway_id()/normalise_led_enabled(), so a
    hostile or stale value on disk (e.g. a path-traversal string, a numeric
    runway id, or a non-bool led_enabled) never reaches a caller. Never
    raises.
    """
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    return {
        "theme": normalise_theme_id(data.get("theme")),
        "tracked_runway": normalise_runway_id(data.get("tracked_runway")),
        "led_enabled": normalise_led_enabled(data.get("led_enabled")),
    }


def save_device_config(state_dir, theme=None, tracked_runway=None, led_enabled=None):
    """Validate and persist a new theme and/or tracked-runway id and/or
    led_enabled flag.

    Each supplied (non-None) value is checked before anything is written:
    `theme`/`tracked_runway` against their registries with an explicit
    membership test, `led_enabled` with an explicit `isinstance(..., bool)`
    type check (there is no registry for a boolean). An unknown/wrong-typed
    value raises `ValueError` naming the rejected value - and leaves any
    pre-existing file byte-identical (T-06-01-01/T-06-01-06). A value left
    `None` is carried over unchanged from the current on-disk config
    (falling back to the documented defaults if none exists yet), so a
    caller updating only the theme never has to also resupply the runway
    or the LED flag.

    Writes with the same tmp-write-then-os.replace() idiom
    server/poll_loop.py's save_poll_state() uses, including the except
    branch that removes a stray `.tmp` file before re-raising - a crash
    mid-write can never leave a half-written config, and a rejected write
    never leaves a `.tmp` file behind either, since validation happens
    before the file is ever touched.
    """
    if theme is not None and theme not in THEMES:
        raise ValueError("unknown theme id %r (expected one of %r)" % (theme, THEME_IDS))
    if tracked_runway is not None and tracked_runway not in RUNWAYS:
        raise ValueError("unknown tracked_runway id %r (expected one of %r)" % (tracked_runway, RUNWAY_IDS))
    if led_enabled is not None and not isinstance(led_enabled, bool):
        raise ValueError("led_enabled must be a bool, got %r" % (led_enabled,))

    current = load_device_config(state_dir)
    new_config = {
        "theme": theme if theme is not None else current["theme"],
        "tracked_runway": tracked_runway if tracked_runway is not None else current["tracked_runway"],
        "led_enabled": led_enabled if led_enabled is not None else current["led_enabled"],
    }

    os.makedirs(state_dir, exist_ok=True)
    path = device_config_path(state_dir)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(new_config, fh, indent=1)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


# --- Presentation accessors -------------------------------------------
#
# Every accessor below takes an already-normalised id (the caller is
# expected to have run it through normalise_theme_id()/normalise_runway_id()
# first, e.g. via load_device_config()) and never raises for a valid,
# registry-member id.


def theme_background_index(state, theme_id):
    """Map the render-pipeline state string `state` ("departing" or
    "arriving") to the theme's corresponding background palette index.
    Raises `ValueError` for any other `state` value - a bad state must be
    loud at the render boundary, matching
    `server.plane.render._build_active_canvas()`'s existing behaviour for
    an unrecognised state.
    """
    theme = THEMES[theme_id]
    if state == "departing":
        return theme["departing_index"]
    if state == "arriving":
        return theme["arriving_index"]
    raise ValueError("unknown state %r (expected 'departing' or 'arriving')" % (state,))


def theme_ink_index(theme_id):
    return THEMES[theme_id]["ink_index"]


def theme_label(theme_id):
    return THEMES[theme_id]["label"]


def runway_tag_text(runway_id):
    return RUNWAYS[runway_id]["tag_text"]


def runway_empty_heading(runway_id):
    return RUNWAYS[runway_id]["empty_heading"]


def runway_label(runway_id):
    return RUNWAYS[runway_id]["label"]
