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

Adding a theme (Phase 8 and beyond): append one entry to `THEMES` keyed by
a new short id, supplying `departing_index`, `arriving_index`, `ink_index`,
and `label`. No structural change to this module and no call-site change
anywhere else is required - `THEME_IDS`, `normalise_theme_id()`, and every
presentation accessor below derive from `THEMES` itself. This is the
concrete discharge of 03-CONTEXT.md's D-11 carried-forward obligation:
Phase 8 is where additional theme entries actually got added, following
the real-glass-then-registry sequence Phase 7's on-glass session
established for "sky".

This module is print-free by design - never log or print the config
file's contents. There is no secret in it, but it must stay safe to import
from an HTTP request handler without accidentally becoming a place a
future change could leak state into a log.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Allow both `import server.device_config` (package import) and direct
# script execution, matching server/poll_loop.py's own bootstrap (lines
# 31-38): sys.path[0] is server/ itself when this file is executed
# directly, so the repo root must be added by hand before the absolute
# `server.panel_format` import below can resolve.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server.panel_format import IDX_BLACK, IDX_BLUE, IDX_GREEN, IDX_RED, IDX_WHITE, IDX_YELLOW

DEFAULT_THEME_ID = "white"
DEFAULT_RUNWAY_ID = "3"
DEFAULT_LED_ENABLED = True  # D-02: matches the LED's current hardcoded always-on behaviour, so nothing changes until a user opts out
DEFAULT_QUIET_HOURS_ENABLED = False  # D-04: an explicit boolean independent of the stored times, the same shape led_enabled uses - never "empty fields mean off". False so nothing changes for any existing installation until a user opts in.
DEFAULT_QUIET_HOURS_START = "23:00"  # D-03: one daily recurring window, never per-weekday
DEFAULT_QUIET_HOURS_END = "07:00"  # D-03: one daily recurring window, never per-weekday

# Shape gate for a submitted/stored quiet-hours HH:MM string. Deliberately
# anchored with `\Z`, NOT `$`: Python's `$` also matches immediately before a
# trailing newline, so a submitted "07:00\n" would pass a `$`-anchored
# pattern, persist a dirty value into device_config.json, and later reach
# the panel's own "Back at ..." body text (T-06-01-01 / ASVS V5 - untrusted
# input must never reach a parser call it could make raise, or a document
# it could pollute, before its shape is checked).
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")

# The device has exactly one fixed physical location (10-RESEARCH.md
# Assumption A3), so the quiet-hours window's timezone is deliberately
# hardcoded here, not a per-installation setting. `zoneinfo` is stdlib
# since Python 3.9 and adds nothing to server/requirements.txt.
QUIET_HOURS_TZ = ZoneInfo("Europe/Paris")

# --- Theme registry ----------------------------------------------------
#
# D-09/D-10/D-11 (06-CONTEXT.md): the "sky" entry below was the *only*
# theme through Phase 7. Its Blue/Green hues were confirmed against
# on-screen previews only through D-21 (03-CONTEXT.md) - Phase 7's
# on-glass session (07-01, hardware/BRINGUP-LOG.md's "Phase 7 On-Glass
# Verification" entry) was the first time this design met real glass, and
# it found both hues genuinely too dark/saturated on the real panel versus
# the monitor preview. panel_format.PALETTE_RGB's Blue/Green triples were
# darkened accordingly (see that module's own comment block for the
# before/after values) - this THEMES dict references
# panel_format.IDX_BLUE/IDX_GREEN indirectly and needed no change itself,
# since the real-glass tuning lives entirely in the RGB triples those
# indices point at. Any additional selectable theme entries should be
# real-glass-validated the same way before landing here. Never write a
# bare palette integer here - always reference panel_format's named IDX_*
# constants, matching that module's own stated discipline.
#
# Phase 8, on-glass session (2026-08-31, 08-06): the registry widened from
# five entries to eleven, and its shape grew two fields - "dithered" (bool)
# and "weight" ("regular"/"bold") - after the developer, looking at the
# real deployed panel, asked to see every one of the 6 real Spectra 6 ink
# colours in two forms each: a flat, undithered field ("pure") and the
# same ink dithered ~40% toward White ("light", the treatment Phase 7
# introduced for Blue/Green because a flat saturated field read too
# dark/harsh at full-panel coverage). Both forms were shown live and
# individually confirmed on real ink for every colour before this dict was
# written - none of it is a guess.
#
# The `weight` field exists because "dithered" alone does not predict
# which font weight reads best: White/Black/Yellow/Red/Green/Blue's flat
# ("pure") fields all confirmed Regular - no dithered speckle to fight, so
# Bold's only job (D-06's original legibility rescue) is unnecessary and
# reads as needlessly heavy. Black/Red/Green/Blue's dithered ("light"/
# "grey") fields confirmed Bold is still needed there, matching the
# original D-06 finding for "sky". Yellow is the one exception: even
# dithered, Yellow's field is light/high-luminance enough that Regular
# stayed legible and was confirmed preferred over Bold - "yellow_light" is
# therefore the only dithered entry with weight "regular". Never assume a
# pattern across entries; read each one's own dithered/weight pair.
#
# "sky" (the old two-tone Blue-departing/Green-arriving pairing) is
# retired outright, not merely renamed - the developer explicitly chose
# separate single-colour themes over any paired departing/arriving
# combination (matching D-02's original single-colour precedent for
# Black/Yellow/Red, now applied to every colour). A stale
# `device_config.json` with `"theme": "sky"` on a previously-deployed host
# degrades safely to `DEFAULT_THEME_ID` via `normalise_theme_id()`'s
# existing unrecognised-value fallback - no migration needed.
THEMES = {
    "white": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "White",
        "dithered": False,
        "weight": "regular",
    },
    "black": {
        "departing_index": IDX_BLACK,
        "arriving_index": IDX_BLACK,
        "ink_index": IDX_WHITE,
        "label": "Black",
        "dithered": False,
        "weight": "regular",
    },
    "grey": {
        "departing_index": IDX_BLACK,
        "arriving_index": IDX_BLACK,
        "ink_index": IDX_WHITE,
        "label": "Grey",
        "dithered": True,
        "weight": "bold",
    },
    "yellow": {
        "departing_index": IDX_YELLOW,
        "arriving_index": IDX_YELLOW,
        "ink_index": IDX_BLACK,
        "label": "Yellow",
        "dithered": False,
        "weight": "regular",
    },
    "yellow_light": {
        "departing_index": IDX_YELLOW,
        "arriving_index": IDX_YELLOW,
        "ink_index": IDX_BLACK,
        "label": "Yellow Light",
        "dithered": True,
        "weight": "regular",
    },
    "red": {
        "departing_index": IDX_RED,
        "arriving_index": IDX_RED,
        "ink_index": IDX_WHITE,
        "label": "Red",
        "dithered": False,
        "weight": "regular",
    },
    "red_light": {
        "departing_index": IDX_RED,
        "arriving_index": IDX_RED,
        "ink_index": IDX_WHITE,
        "label": "Red Light",
        "dithered": True,
        "weight": "bold",
    },
    "green": {
        "departing_index": IDX_GREEN,
        "arriving_index": IDX_GREEN,
        "ink_index": IDX_WHITE,
        "label": "Green",
        "dithered": False,
        "weight": "regular",
    },
    "green_light": {
        "departing_index": IDX_GREEN,
        "arriving_index": IDX_GREEN,
        "ink_index": IDX_WHITE,
        "label": "Green Light",
        "dithered": True,
        "weight": "bold",
    },
    "blue": {
        "departing_index": IDX_BLUE,
        "arriving_index": IDX_BLUE,
        "ink_index": IDX_WHITE,
        "label": "Blue",
        "dithered": False,
        "weight": "regular",
    },
    "blue_light": {
        "departing_index": IDX_BLUE,
        "arriving_index": IDX_BLUE,
        "ink_index": IDX_WHITE,
        "label": "Blue Light",
        "dithered": True,
        "weight": "bold",
    },
    # Phase 9 (09-01): the diagonal-band theme family, validated end-to-end
    # in spike 003 (`.planning/spikes/003-diagonal-band-theme/README.md`,
    # round 15, developer-confirmed "oui !"). Every band candidate in the
    # spike rendered against `build_canvas(theme_id="white")` - the band's
    # own colour was always a separate function parameter, never a
    # base-canvas property - so all 5 entries below carry the exact same
    # departing_index/arriving_index/ink_index/dithered/weight as "white"
    # itself. Only label, band_index (the band's own IDX_* colour), and
    # band_dithered (whether that band is drawn flat or dithered ~40%
    # toward White) vary between the 5. band_index/band_dithered are read
    # by server/plane/render.py's draw_diagonal_band() (plans 09-02/09-03)
    # via theme_is_band()/theme_band_index()/theme_band_dithered() below -
    # never by indexing THEMES directly.
    "band_blue": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Blue",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_BLUE,
        "band_dithered": False,
    },
    "band_blue_light": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Blue Light",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_BLUE,
        "band_dithered": True,
    },
    "band_green_light": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Green Light",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_GREEN,
        "band_dithered": True,
    },
    "band_red": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Red",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_RED,
        "band_dithered": False,
    },
    "band_black": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Black",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_BLACK,
        "band_dithered": False,
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
#
# Quick task 260902-j21 (2026-09-02): each `label` now carries only the
# runway number Orly's own signage and runway-works documentation use
# ("Piste N"), sourced from the official Aeroport de Paris runway-works
# diagram the developer supplied - superseding the prior heading-pair
# labels ("Runway 3 (07/25)", "Runway 06/24", "Runway 02/20") quoted here
# for context only. The mapping is NOT inferable from the keys, so it is
# recorded explicitly: key "3" (DEFAULT_RUNWAY_ID) -> Piste 3 (07-25), key
# "06-24" -> Piste 4, key "02-20" -> Piste 2. The dict KEYS themselves are
# deliberately unchanged - they are the persisted `tracked_runway` value in
# device_config.json, the membership set RUNWAY_IDS validates against, the
# CFG-12 consistency check against adsb-test/runway3.json noted above, and
# the filename stem the companion/static/RUNWAY-IMAGES.md `runway-{id}.png`
# drop-in contract keys off of - renaming any of them would silently orphan
# the matching diagram asset. `tag_text`/`empty_heading` are deliberately
# left in their existing English airport-board voice: they render onto the
# physical Spectra 6 panel via server/plane/render.py's runway_tag_text()/
# runway_empty_heading(), a separate design surface nobody asked to change.
# The French "Piste" vocabulary is scoped to the companion web picker alone.
RUNWAYS = {
    "3": {
        "label": "Piste 3",
        "tag_text": "ORY · RWY 3",
        "empty_heading": "Watching Runway 3",
    },
    "06-24": {
        "label": "Piste 4",
        "tag_text": "ORY · RWY 06/24",
        "empty_heading": "Watching Runway 06/24",
    },
    "02-20": {
        "label": "Piste 2",
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


def normalise_quiet_hours_enabled(value):
    """Same contract as normalise_led_enabled(): return `value` unchanged
    only when `isinstance(value, bool)` is true, otherwise return
    `DEFAULT_QUIET_HOURS_ENABLED`. Never raises. Deliberately no registry/
    membership test, for the same reason normalise_led_enabled() documents.
    """
    if isinstance(value, bool):
        return value
    return DEFAULT_QUIET_HOURS_ENABLED


def normalise_quiet_hours_time(value, default):
    """Return `value` unchanged only when it is a string matching the
    `_HHMM_RE` shape gate (24-hour, zero-padded "HH:MM"), otherwise return
    `default`. One shared function for both the start and the end field -
    deliberately not two near-identical functions - so the two can never
    drift apart on validation strictness. Never raises.
    """
    if isinstance(value, str) and _HHMM_RE.match(value):
        return value
    return default


def load_device_config(state_dir):
    """Read `<state_dir>/device_config.json`; a missing file, an unreadable
    file, a malformed document, or a non-dict document all fall back to an
    empty dict rather than raising. Always returns all six keys with valid
    values - `theme`, `tracked_runway`, `led_enabled`, `quiet_hours_enabled`,
    `quiet_hours_start`, and `quiet_hours_end` - via
    normalise_theme_id()/normalise_runway_id()/normalise_led_enabled()/
    normalise_quiet_hours_enabled()/normalise_quiet_hours_time(), so a
    hostile or stale value on disk (e.g. a path-traversal string, a numeric
    runway id, a non-bool led_enabled, or a malformed quiet-hours time)
    never reaches a caller. Never raises.
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
        "quiet_hours_enabled": normalise_quiet_hours_enabled(data.get("quiet_hours_enabled")),
        "quiet_hours_start": normalise_quiet_hours_time(data.get("quiet_hours_start"), DEFAULT_QUIET_HOURS_START),
        "quiet_hours_end": normalise_quiet_hours_time(data.get("quiet_hours_end"), DEFAULT_QUIET_HOURS_END),
    }


def save_device_config(
    state_dir, theme=None, tracked_runway=None, led_enabled=None,
    quiet_hours_enabled=None, quiet_hours_start=None, quiet_hours_end=None,
):
    """Validate and persist a new theme and/or tracked-runway id and/or
    led_enabled flag and/or the three quiet-hours fields.

    Each supplied (non-None) value is checked before anything is written:
    `theme`/`tracked_runway` against their registries with an explicit
    membership test, `led_enabled`/`quiet_hours_enabled` with an explicit
    `isinstance(..., bool)` type check (there is no registry for a
    boolean), and `quiet_hours_start`/`quiet_hours_end` against the
    `_HHMM_RE` shape gate. An unknown/wrong-typed value raises `ValueError`
    naming the rejected value - and leaves any pre-existing file
    byte-identical (T-06-01-01/T-06-01-06). A value left `None` is carried
    over unchanged from the current on-disk config (falling back to the
    documented defaults if none exists yet), so a caller updating only the
    theme never has to also resupply the runway, the LED flag, or the
    quiet-hours fields.

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
    if quiet_hours_enabled is not None and not isinstance(quiet_hours_enabled, bool):
        raise ValueError("quiet_hours_enabled must be a bool, got %r" % (quiet_hours_enabled,))
    if quiet_hours_start is not None and not (isinstance(quiet_hours_start, str) and _HHMM_RE.match(quiet_hours_start)):
        raise ValueError("quiet_hours_start must be a 24-hour zero-padded HH:MM string, got %r" % (quiet_hours_start,))
    if quiet_hours_end is not None and not (isinstance(quiet_hours_end, str) and _HHMM_RE.match(quiet_hours_end)):
        raise ValueError("quiet_hours_end must be a 24-hour zero-padded HH:MM string, got %r" % (quiet_hours_end,))

    current = load_device_config(state_dir)
    new_config = {
        "theme": theme if theme is not None else current["theme"],
        "tracked_runway": tracked_runway if tracked_runway is not None else current["tracked_runway"],
        "led_enabled": led_enabled if led_enabled is not None else current["led_enabled"],
        "quiet_hours_enabled": quiet_hours_enabled if quiet_hours_enabled is not None else current["quiet_hours_enabled"],
        "quiet_hours_start": quiet_hours_start if quiet_hours_start is not None else current["quiet_hours_start"],
        "quiet_hours_end": quiet_hours_end if quiet_hours_end is not None else current["quiet_hours_end"],
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


# --- Quiet-hours window arithmetic --------------------------------------
#
# Genuinely new domain logic - no existing timezone-aware or window/
# schedule arithmetic exists anywhere else in the codebase
# (server/history_db.py is UTC-only). See 10-RESEARCH.md Pattern 2 and
# 10-PATTERNS.md's "New DST-safe window-arithmetic helper" section for the
# reference implementation this is adapted from, with exactly two
# mandatory deviations documented in seconds_until_quiet_hours_end()'s own
# docstring below.


def seconds_until_quiet_hours_end(now_utc, start_hm, end_hm):
    """Return the whole seconds remaining until the daily [start_hm, end_hm)
    Europe/Paris wall-clock window's end time, or `None` when `now_utc`
    falls outside the window. The window wraps midnight whenever
    `end_hm <= start_hm` (e.g. "23:00"/"07:00"); when `start_hm == end_hm`
    the window is zero-width and this always returns `None` for every
    instant - a zero-width window is never active, and that is intentional
    rather than a bug to "fix" into an always-active window.

    Parameter contract - this function is the arithmetic core only and
    performs no validation of its own, because stub-server/byos_server.py
    (plan 10-03) duplicates it byte-for-byte across the vendor boundary and
    every byte it carries has to be reproducible there:
      - `now_utc` MUST be a timezone-aware datetime.
      - `start_hm`/`end_hm` MUST already have passed `_HHMM_RE`.

    Two mandatory deviations from 10-PATTERNS.md's reference body, both
    load-bearing - do not "restore" the reference version:

    (a) The final return subtracts in UTC, not in local time:
    `end_dt.astimezone(timezone.utc) - now_utc`, NOT `end_dt - local_now`.
    This is a correctness fix, verified numerically during planning:
    `end_dt` and `local_now` share the same `tzinfo` object, and Python's
    documented rule for subtracting two aware datetimes with the same
    `tzinfo` is to ignore the zone and subtract the wall-clock numerals -
    so the reference body's naive numeral difference is wrong by exactly
    one hour across a Europe/Paris DST transition. Converting `end_dt` to
    UTC first restores the true-elapsed-duration property.

    (b) Accepted caveat (10-RESEARCH.md Pitfall 2), not engineered around: a
    window boundary configured inside the 02:00-03:00 transition hour on
    the last Sunday of March or October resolves via PEP 495's default
    `fold=0` semantics and can be up to an hour off for that one instant.
    No `fold=1` override is added - D-01's "never shorter than the base
    sleep" rule bounds the worst case to one extra or one missing wake,
    twice a year, only for a boundary configured inside that specific hour.
    """
    local_now = now_utc.astimezone(QUIET_HOURS_TZ)
    start_h, start_m = (int(x) for x in start_hm.split(":"))
    end_h, end_m = (int(x) for x in end_hm.split(":"))
    start_today = local_now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end_today = local_now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if (start_h, start_m) <= (end_h, end_m):
        if not (start_today <= local_now < end_today):
            return None
        end_dt = end_today
    else:
        if local_now >= start_today:
            end_dt = end_today + timedelta(days=1)
        elif local_now < end_today:
            end_dt = end_today
        else:
            return None
    return max(0, int((end_dt.astimezone(timezone.utc) - now_utc).total_seconds()))


def quiet_hours_status(config, now_epoch):
    """Convenience wrapper server/poll_loop.py calls (plan 10-04) -
    deliberately NOT part of what stub-server/byos_server.py duplicates.

    `config` is a load_device_config() return dict; `now_epoch` is epoch
    seconds as a float (so poll_loop.py can pass its existing now_s() seam
    straight through). Returns `(seconds_remaining, end_hm)`, or
    `(None, None)` when `config` is not a dict, `config.get(
    "quiet_hours_enabled")` is not literally `True`, or
    seconds_until_quiet_hours_end() returns `None`.

    Both time strings are re-normalised through normalise_quiet_hours_time()
    before use, so a caller passing a hand-built dict cannot slip an
    unvalidated string into the arithmetic. Never raises, including for a
    hostile `now_epoch` (non-numeric, None, NaN, or absurdly large) -
    poll_loop.py calls this before it has rendered anything, and this
    module's never-raise contract has to hold here too.
    """
    try:
        if not isinstance(config, dict) or config.get("quiet_hours_enabled") is not True:
            return None, None
        start_hm = normalise_quiet_hours_time(config.get("quiet_hours_start"), DEFAULT_QUIET_HOURS_START)
        end_hm = normalise_quiet_hours_time(config.get("quiet_hours_end"), DEFAULT_QUIET_HOURS_END)
        now_utc = datetime.fromtimestamp(float(now_epoch), timezone.utc)
        remaining = seconds_until_quiet_hours_end(now_utc, start_hm, end_hm)
        if remaining is None:
            return None, None
        return remaining, end_hm
    except (TypeError, ValueError, OverflowError, OSError):
        return None, None


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


def theme_dithered(theme_id):
    """Whether `theme_id`'s background field is dithered ~40% toward White
    (the "light"/"grey" treatment) rather than a flat, undithered fill.
    Phase 8 08-06 on-glass finding - see THEMES' own module comment for the
    full rationale.
    """
    return THEMES[theme_id]["dithered"]


def theme_weight(theme_id):
    """The PT Serif static weight `theme_id`'s active-state text roles use
    - `"regular"` or `"bold"`. Not derivable from `theme_dithered()` alone;
    see THEMES' own module comment for why (Yellow Light is the one
    dithered entry that still uses Regular).
    """
    return THEMES[theme_id]["weight"]


def theme_is_band(theme_id):
    """Whether `theme_id` is one of the 5 Phase 9 diagonal-band themes -
    true iff its THEMES entry carries the band-only `"band_index"` key.
    False for every one of the 11 pre-Phase-9 themes, which never carry it.
    """
    return "band_index" in THEMES[theme_id]


def theme_band_index(theme_id):
    """`theme_id`'s diagonal band colour as a panel_format.IDX_* constant,
    or `None` for a non-band theme. Absent-key-safe via `.get()` - never
    raises for any registered id, band or not.
    """
    return THEMES[theme_id].get("band_index")


def theme_band_dithered(theme_id):
    """Whether `theme_id`'s diagonal band is dithered ~40% toward White
    rather than a flat, undithered fill; `False` for a non-band theme.
    Absent-key-safe via `.get()` - never raises for any registered id.
    """
    return THEMES[theme_id].get("band_dithered", False)


def runway_tag_text(runway_id):
    return RUNWAYS[runway_id]["tag_text"]


def runway_empty_heading(runway_id):
    return RUNWAYS[runway_id]["empty_heading"]


def runway_label(runway_id):
    return RUNWAYS[runway_id]["label"]
