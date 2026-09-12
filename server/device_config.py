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
DEFAULT_DISPLAY_ENABLED = True  # D-09 (12-CONTEXT.md): an explicit boolean following the
# DEFAULT_LED_ENABLED/DEFAULT_QUIET_HOURS_ENABLED precedent, never an
# absence-means-off convention, so nothing changes for an installation already in
# service until someone opts in.

# D-02 (11-CONTEXT.md): bounds for the stored `wake_interval_s` config field only - the
# value quiet_hours_sleep_s() hands the device is explicitly allowed to exceed
# WAKE_INTERVAL_MAX_S during an active quiet-hours window (11-RESEARCH.md Pitfall 4).
# 60 mirrors firmware/main/Kconfig.projbuild's FP_MIN_REFRESH_SPACING_S `default`
# (with `range 30 86400`) - this project's own conservative margin against needless
# redraws and the battery they spend, NOT a vendor-mandated threshold; the GDEP133C02
# datasheet specifies no minimum. 3600 (one hour) is the developer-confirmed ceiling.
WAKE_INTERVAL_MIN_S = 60
WAKE_INTERVAL_MAX_S = 3600

# D-01 (12-CONTEXT.md): the fixed off-state check-in cadence while display_enabled is
# False - deliberately replaces wake_interval_s rather than being derived from it: a
# short configured interval (near WAKE_INTERVAL_MIN_S) gets roughly a 5x wake reduction
# while off, and a long one (near WAKE_INTERVAL_MAX_S) gets a predictable
# back-within-five-minutes switch-on instead of waiting up to an hour. 300 sits inside
# the inclusive [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] band above, so unlike
# quiet_hours_sleep_s() this mechanism needs none of the ceiling-exceeding latitude that
# function was granted. stub-server/byos_server.py independently redefines this same
# value across the vendor boundary (plan 12-03, VENDOR.md) and must be kept in step with
# it - the same cross-file convention WAKE_INTERVAL_MIN_S/WAKE_INTERVAL_MAX_S already use.
DISPLAY_OFF_SLEEP_S = 300

# Deliberately no DEFAULT_WAKE_INTERVAL_S constant. Unlike every other field in this
# module, wake_interval_s's unset state is `None`, a single deliberate exception to this
# module's otherwise-universal "always return a concrete value" contract - the true
# fallback is the deployed SKYPANE_SLEEP_S / --sleep value, which lives in a different OS
# process's argparse namespace and is not knowable here (D-07, 11-RESEARCH.md Pattern 1).
# Do not "restore consistency" by inventing a default; there isn't one to invent.

# D-04/D-05 (15-CONTEXT.md): the one sentinel in this module that widens what a
# save_device_config() argument can mean. For every field including
# theme_arriving, `None` keeps its single existing meaning - "the caller
# didn't supply this parameter, carry the current on-disk value forward" -
# and that meaning never changes. `CLEAR_THEME_ARRIVING` is a second,
# distinct value that means "the caller explicitly wants theme_arriving
# cleared back to unset (None)", something `None` itself cannot express
# without colliding with carry-forward. This mirrors
# companion/pages/health_page.py's `_DB_UNAVAILABLE` module-level `object()`
# sentinel - the existing in-codebase idiom for a state plain `None` cannot
# carry - rather than inventing a new pattern. The alternative considered and
# rejected (15-RESEARCH.md Assumption A1) was a second boolean parameter
# `clear_theme_arriving=False`: that would give exactly one field an
# asymmetric extra argument while every other field keeps identical arity.
# `load_device_config()` never sees this sentinel - it exists only in
# save_device_config()'s write path, compared by identity (`is`), never by
# equality, so no crafted value could ever collide with it.
CLEAR_THEME_ARRIVING = object()

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
    # base-canvas property - so all 5 entries immediately below (band_blue
    # through band_black) carry the exact same
    # departing_index/arriving_index/ink_index/dithered/weight as "white"
    # itself. Only label, band_index (the band's own IDX_* colour), and
    # band_dithered (whether that band is drawn flat or dithered ~40%
    # toward White) vary between the 5. band_index/band_dithered are read
    # by server/plane/render.py's draw_diagonal_band() (plans 09-02/09-03)
    # via theme_is_band()/theme_band_index()/theme_band_dithered() below -
    # never by indexing THEMES directly.
    #
    # (Quick task 260905-e04 added two further band entries below band_black
    # whose base canvas is NOT White - see the comment above them.)
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
    # Quick task 260905-e04: the first two band themes whose field is NOT
    # White - a solid diagonal band on a dithered field tinted the SAME hue
    # as the band itself ("tone-on-tone"), per the developer's own request
    # ("Diagonale bleu et fond bleu claire" / "Diagonale rouge et fond rouge
    # clair"). Each row below is its `_light` sibling's base-canvas fields
    # plus its solid-band sibling's band fields, with nothing invented:
    #   - departing_index/arriving_index/dithered are copied from
    #     blue_light/red_light (the hue itself, dithered True - the dithering
    #     is what produces the ~40%-toward-White light tint via
    #     dither.dithered_state_background()).
    #   - ink_index/weight are ALSO copied from blue_light/red_light, NOT
    #     from the band family's White-field/Black-ink pairing above. This
    #     is deliberate, not an oversight: draw_main_text_block() forces
    #     `effective_ink = IDX_WHITE` unconditionally for every band theme,
    #     so a registry row's own ink_index never colours in-band text - it
    #     only colours everything OUTSIDE the band (top labels, the
    #     previous-flight card, the battery/source-fault indicators), all of
    #     which sit on the tinted field here. The field's own on-glass-
    #     confirmed ink/weight pairing (08-06) is what governs that surface,
    #     not the band family's - putting Black ink on a saturated tinted
    #     field would be an untested combination nothing has confirmed.
    #   - band_index deliberately EQUALS departing_index/arriving_index -
    #     tone-on-tone is the entire point, not a copy-paste slip a future
    #     reader should "fix".
    #   - band_dithered is False, copied from band_blue/band_red: the
    #     developer asked for a SOLID diagonal, and a dithered band on an
    #     already-dithered field of the same hue would leave almost no edge
    #     to read.
    # Disambiguation (DP-1): the `band_` prefix separates these two from the
    # fieldless tints `blue_light`/`green_light`; the `_field` suffix
    # separates them from `band_blue_light` (an existing Phase 9 entry)
    # where `_light` describes the BAND's own dithered treatment, not the
    # field - these two new ids name the FIELD instead.
    "band_blue_field": {
        "departing_index": IDX_BLUE,
        "arriving_index": IDX_BLUE,
        "ink_index": IDX_WHITE,
        "label": "Band Blue Field",
        "dithered": True,
        "weight": "bold",
        "band_index": IDX_BLUE,
        "band_dithered": False,
    },
    "band_red_field": {
        "departing_index": IDX_RED,
        "arriving_index": IDX_RED,
        "ink_index": IDX_WHITE,
        "label": "Band Red Field",
        "dithered": True,
        "weight": "bold",
        "band_index": IDX_RED,
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
# 19-12-PLAN.md Task 1 (D-11/A-29): each `label` now reads in plain
# English, carrying both the ADP runway number and the physical
# heading-pair designator in parentheses - "Runway 3 (07/25)",
# "Runway 4 (06/24)", "Runway 2 (02/20)" - superseding the prior quick
# task 260902-j21's French ADP vocabulary (the French word for
# "runway" followed by the number, sourced from the official Aeroport
# de Paris runway-works diagram) quoted here for
# context only. The "3" key's parenthetical, "07/25", is NOT derivable
# from the key itself and is therefore typed by hand, not templated.
# The mapping is recorded explicitly: key "3" (DEFAULT_RUNWAY_ID) ->
# Runway 3 (07/25), key "06-24" -> Runway 4 (06/24), key "02-20" ->
# Runway 2 (02/20). The dict KEYS themselves are deliberately unchanged
# - they are the persisted `tracked_runway` value in device_config.json,
# the membership set RUNWAY_IDS validates against, the CFG-12
# consistency check against adsb-test/runway3.json noted above, and the
# filename stem the companion/static/RUNWAY-IMAGES.md `runway-{id}.png`
# drop-in contract keys off of - renaming any of them would silently
# orphan the matching diagram asset. `tag_text`/`empty_heading` are
# deliberately left UNCHANGED, in their existing English,
# parentheses-free airport-board voice: they render onto the physical
# Spectra 6 panel via server/plane/render.py's runway_tag_text()/
# runway_empty_heading(), a separate design surface D-11 does not touch
# and server/test_render.py's own pinned expectations depend on. Only
# `label` - the companion web picker's own value - changes here; the
# picker is English again, and the ADP number survives inside the label
# rather than the vocabulary the picker used before this change.
RUNWAYS = {
    "3": {
        "label": "Runway 3 (07/25)",
        "tag_text": "ORY · RWY 3",
        "empty_heading": "Watching Runway 3",
    },
    "06-24": {
        "label": "Runway 4 (06/24)",
        "tag_text": "ORY · RWY 06/24",
        "empty_heading": "Watching Runway 06/24",
    },
    "02-20": {
        "label": "Runway 2 (02/20)",
        "tag_text": "ORY · RWY 02/20",
        "empty_heading": "Watching Runway 02/20",
    },
}

THEME_IDS = tuple(THEMES)
RUNWAY_IDS = tuple(RUNWAYS)

# --- Screen-id seam (D-23, 19-12-PLAN.md Task 1) --------------------------
#
# `companion/screens.py` owns the real screen-type registry
# (SCREEN_TYPES/SCREEN_IDS/DEFAULT_SCREEN_ID) - the two constants below
# are a DELIBERATE DUPLICATE of that module's own `SCREEN_IDS`/
# `DEFAULT_SCREEN_ID` values, not an import of them. This module is a
# leaf (its own docstring above: stdlib plus server.panel_format only)
# and `server/` must never import `companion/` - the dependency between
# the two packages runs one way only (companion/ imports server/, e.g.
# companion/app.py's `from server import device_config, history_db`),
# so importing companion.screens here would invert it. This is the same
# duplicated-not-imported contract companion/app.py's `*_SCRIPT_ROUTE`
# constants and companion/layout.py's matching `*_SCRIPT_SRC` constants
# already use for an identical reason (companion/app.py cannot import
# companion/layout.py's constant either, for its own, unrelated cycle
# reason) - a dedicated harness check
# (server/test_config_history.py) pins SCREEN_IDS/DEFAULT_SCREEN_ID
# equal to companion.screens's own values, so the two can never
# silently drift apart. Keep both files' names identical when either
# changes.
DEFAULT_SCREEN_ID = "plane-frame"
SCREEN_IDS = ("plane-frame",)

# D-26/D-28 (20-CONTEXT.md): the notifications config group - the first
# DICT-VALUED field in this registry, every sibling field above being a
# scalar (string/bool/int) or None. `topic_url` is write-only (D-26's
# amendment: never rendered back, not partially masked - that contract
# lives in the web app's own Device-page renderer, a later plan, not
# here); this module stores it verbatim because server/poll_loop.py's
# notification sender needs the real value to POST to. `lang` is a
# persisted en/fr snapshot (D-28) because the poll loop has no browser
# to read a per-request language from.
DEFAULT_NOTIFICATIONS = {
    "topic_url": None,
    "battery_low": True,
    "frame_silent": True,
    "lang": "en",
}

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


def normalise_theme_arriving(value):
    """Return `value` unchanged only when it is a string AND a member of
    `THEMES` - otherwise return `None`. Never raises.

    Unlike `normalise_theme_id()`, which degrades an unrecognised value to
    this module's documented theme default, this degrades to `None` - and
    `None` here means "no override, i.e. same as `theme`" (D-04), NOT
    "degraded to the documented default". Copying normalise_theme_id()'s
    degrade-to-default shape here would be wrong: there is no sensible
    "default arrivals theme" to fall back to, only "defer to whatever the
    base theme already is".

    This makes `theme_arriving` the second key in this module, after
    `wake_interval_s`, whose valid value set includes `None` - and the two
    diverge on write (see CLEAR_THEME_ARRIVING and save_device_config()'s own
    docstring): `wake_interval_s`'s `None` is permanent-until-a-new-value,
    while `theme_arriving` must be genuinely clearable back to `None`.
    """
    if isinstance(value, str) and value in THEMES:
        return value
    return None


def normalise_calendar_theme_id(value):
    """Return `value` unchanged only when it is a string AND a member of
    `THEMES` - otherwise return `None`. Never raises.

    Same degrade-to-`None` shape as `normalise_theme_arriving()`, and for the
    same reason: `None` here means "the operator has not chosen a theme for
    calendar-matched flights, so a calendar match resolves to nothing and the
    manual rules run next" - NOT "degraded to the documented default".
    Degrading to `DEFAULT_THEME_ID` instead would be actively wrong: every
    calendar match would then silently repaint the panel in whatever theme
    the frame already happened to be using, which looks exactly like the
    feature not having matched at all, rather than the honest inert state of
    "no calendar theme chosen" (phase 16 plan 02, T-16-TAMPER).

    Deliberately no `CLEAR_THEME_ARRIVING`-style SENTINEL for this key,
    even though 21-05-PLAN.md's Frame colours card (D-09) does now give
    the operator a "Same as departures" chip that must clear a
    previously-set override: the empty string itself is the clear
    signal at the WRITE path (`save_device_config()`'s own validation
    gate accepts `""` as a genuine, storable value, distinct from
    `None`'s "not supplied, carry forward" meaning) — no second
    sentinel object is needed because this function's own degrade-to-
    `None` contract already treats `""` exactly like any other
    non-member string. `None` here keeps its single existing meaning of
    "not supplied, carry forward" - the same resolution `wake_interval_s`
    already has, for the same reason.

    This makes `calendar_theme_id` the third key in this module, after
    `wake_interval_s` and `theme_arriving`, whose valid value set includes
    `None`.
    """
    if isinstance(value, str) and value in THEMES:
        return value
    return None


def normalise_runway_id(value):
    """Same contract as normalise_theme_id(), against RUNWAYS/DEFAULT_RUNWAY_ID."""
    if isinstance(value, str) and value in RUNWAYS:
        return value
    return DEFAULT_RUNWAY_ID


def normalise_screen_id(value):
    """Return `value` unchanged only when it is a string AND a member of
    `SCREEN_IDS` - otherwise return `DEFAULT_SCREEN_ID`. Never raises,
    and never uses `value` as a lookup key without the membership test
    first (T-19-11, ASVS V5) - same read-path "degrade to the default"
    shape every sibling normaliser in this module already uses
    (normalise_theme_id()/normalise_runway_id() above)."""
    if isinstance(value, str) and value in SCREEN_IDS:
        return value
    return DEFAULT_SCREEN_ID


def normalise_notifications(value):
    """Return a well-formed notifications sub-dict - never raises,
    degrades to a fresh copy of `DEFAULT_NOTIFICATIONS` wholesale for
    anything that isn't a dict, and per-field within it for anything
    malformed, mirroring `normalise_screen_id()`'s own "membership
    test on read, degrade to default" shape, applied once per sub-key
    (D-26/D-28).

    `topic_url` keeps a `str` or becomes `None` (no scheme/host check
    here - `server/notify.py`'s `_url_is_safe()`-gated send is the one
    place that validates it, at send time, so there is no second,
    driftable copy of that gate). `battery_low`/`frame_silent` keep a
    real `bool` or take their own documented default (the
    `isinstance(True, int)` gotcha every sibling boolean normaliser in
    this module already guards against does not apply here - there is
    no numeric sibling field to confuse it with, but the same explicit
    `isinstance(..., bool)` test is used anyway, for the same reason
    every other boolean field in this module uses it). `lang` keeps a
    member of `("en", "fr")` or becomes `DEFAULT_NOTIFICATIONS["lang"]`.
    """
    if not isinstance(value, dict):
        return dict(DEFAULT_NOTIFICATIONS)
    topic_url = value.get("topic_url")
    battery_low = value.get("battery_low")
    frame_silent = value.get("frame_silent")
    lang = value.get("lang")
    return {
        "topic_url": topic_url if isinstance(topic_url, str) else None,
        "battery_low": battery_low if isinstance(battery_low, bool) else DEFAULT_NOTIFICATIONS["battery_low"],
        "frame_silent": frame_silent if isinstance(frame_silent, bool) else DEFAULT_NOTIFICATIONS["frame_silent"],
        "lang": lang if lang in ("en", "fr") else DEFAULT_NOTIFICATIONS["lang"],
    }


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


def normalise_display_enabled(value):
    """Same contract as normalise_led_enabled(): return `value` unchanged only
    when `isinstance(value, bool)` is true, otherwise return
    `DEFAULT_DISPLAY_ENABLED`. Never raises. Deliberately no registry/
    membership test, for the same reason normalise_led_enabled() documents.

    Security-relevant consequence of the default's direction (D-09,
    12-CONTEXT.md): because DEFAULT_DISPLAY_ENABLED is True, every
    degradation path - a missing file, an unreadable file, malformed JSON, a
    non-dict document, or a wrong-typed value - leaves the display ON. A
    corrupted config can never be the reason a frame goes dark; this is the
    fail-open direction this field deliberately needs (a fail-closed default
    would turn a disk-level fault into an apparently-dead device, exactly the
    ambiguity D-03 rejected the blank-field off-screen option to avoid).
    """
    if isinstance(value, bool):
        return value
    return DEFAULT_DISPLAY_ENABLED


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


def normalise_wake_interval_s(value):
    """Return `value` unchanged only when it is an `int` that is not a `bool`
    AND falls within `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]` inclusive -
    otherwise return `None`. Never raises.

    Unlike every sibling normaliser in this module, `None` here does NOT mean
    "degraded to the documented default" - there is no default to degrade to.
    It means "never explicitly set", the same never-configured state a fresh
    install starts in.

    The bool exclusion is mandatory and load-bearing, not defensive noise: in
    Python `isinstance(True, int)` evaluates true, so the type test must be
    `isinstance(value, int) and not isinstance(value, bool)` - see
    normalise_led_enabled()'s own docstring, which documents the same gotcha
    from the other direction (an int such as 0 or 1 is deliberately not
    accepted as a bool).
    """
    if isinstance(value, int) and not isinstance(value, bool) and WAKE_INTERVAL_MIN_S <= value <= WAKE_INTERVAL_MAX_S:
        return value
    return None


def load_device_config(state_dir):
    """Read `<state_dir>/device_config.json`; a missing file, an unreadable
    file, a malformed document, or a non-dict document all fall back to an
    empty dict rather than raising. Always returns all twelve keys with valid
    values - `theme`, `theme_arriving`, `calendar_theme_id`,
    `tracked_runway`, `led_enabled`, `quiet_hours_enabled`,
    `quiet_hours_start`, `quiet_hours_end`, `wake_interval_s`,
    `display_enabled`, `screen_id`, and `notifications` - via normalise_theme_id()/
    normalise_theme_arriving()/normalise_calendar_theme_id()/
    normalise_runway_id()/normalise_led_enabled()/
    normalise_quiet_hours_enabled()/normalise_quiet_hours_time()/
    normalise_wake_interval_s()/normalise_display_enabled()/
    normalise_screen_id()/normalise_notifications(), so a hostile or stale
    value on disk (e.g. a path-traversal string, a numeric runway id, a
    non-bool led_enabled, a malformed quiet-hours time, a hostile
    wake_interval_s, an unregistered theme_arriving, calendar_theme_id or
    screen_id, a non-bool display_enabled, or a malformed notifications
    group) never reaches a caller. `theme_arriving` (D-04),
    `calendar_theme_id` (phase 16 plan 02), `screen_id` (D-23,
    19-12-PLAN.md Task 1), and `notifications` (D-26, 20-02-PLAN.md Task 3)
    are all read with `.get()`, so a `device_config.json` written before
    any of the four existed - one that has never carried it - resolves
    that key to its documented default (`None` for the first two,
    `DEFAULT_SCREEN_ID` for the third, `DEFAULT_NOTIFICATIONS` for the
    fourth) with no migration and no rewrite of the file on disk.
    `wake_interval_s`, `theme_arriving`, and `calendar_theme_id` are the
    three keys whose valid value set includes `None`: `wake_interval_s`'s
    `None` means never-explicitly-set, `theme_arriving`'s `None` means "no
    override, same as `theme`", and `calendar_theme_id`'s `None` means "the
    operator has not chosen a calendar theme, so a calendar match has no
    effect" - every other key always has a concrete default (D-09:
    `display_enabled` defaults to `True`). Never raises.
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
        "theme_arriving": normalise_theme_arriving(data.get("theme_arriving")),
        "calendar_theme_id": normalise_calendar_theme_id(data.get("calendar_theme_id")),
        "tracked_runway": normalise_runway_id(data.get("tracked_runway")),
        "led_enabled": normalise_led_enabled(data.get("led_enabled")),
        "quiet_hours_enabled": normalise_quiet_hours_enabled(data.get("quiet_hours_enabled")),
        "quiet_hours_start": normalise_quiet_hours_time(data.get("quiet_hours_start"), DEFAULT_QUIET_HOURS_START),
        "quiet_hours_end": normalise_quiet_hours_time(data.get("quiet_hours_end"), DEFAULT_QUIET_HOURS_END),
        "wake_interval_s": normalise_wake_interval_s(data.get("wake_interval_s")),
        "display_enabled": normalise_display_enabled(data.get("display_enabled")),
        "screen_id": normalise_screen_id(data.get("screen_id")),
        "notifications": normalise_notifications(data.get("notifications")),
    }


def save_device_config(
    state_dir, theme=None, theme_arriving=None, tracked_runway=None, led_enabled=None,
    quiet_hours_enabled=None, quiet_hours_start=None, quiet_hours_end=None,
    wake_interval_s=None, display_enabled=None, calendar_theme_id=None,
    screen_id=None, notifications=None,
):
    """Validate and persist a new theme and/or theme_arriving override and/or
    tracked-runway id and/or led_enabled flag and/or the three quiet-hours
    fields and/or wake_interval_s and/or display_enabled and/or
    calendar_theme_id and/or screen_id and/or notifications.

    `screen_id` (D-23, 19-12-PLAN.md Task 1) is placed LAST-but-one so
    every existing positional/keyword call site predating that plan is
    unaffected. It follows the identical "membership test, raise on
    write, degrade on read" split every sibling registry field here
    already uses: a non-None value not in `SCREEN_IDS` raises
    `ValueError` naming both the rejected value and `SCREEN_IDS`
    (matching `tracked_runway`'s own message shape below) before
    anything is written; `None` carries the current on-disk value
    forward, the same "not supplied" meaning every other field's `None`
    already has.

    `notifications` (D-26, 20-02-PLAN.md Task 3) is placed LAST for the
    identical reason `screen_id` documents above - so every existing
    positional/keyword call site predating this plan (including
    `screen_id` itself) is unaffected. Unlike every other field in this
    module, it is a dict, not a scalar: a non-None value that is not a
    dict, or whose `topic_url` is neither a `str` nor `None`, or whose
    `battery_low`/`frame_silent` are not real `bool`s, or whose `lang` is
    outside `("en", "fr")`, raises `ValueError` naming the rejected
    field - the raise-on-write half of `normalise_notifications()`'s own
    degrade-on-read contract. `None` carries the current on-disk group
    forward unchanged, the same "not supplied" meaning every other field's
    `None` already has. This module does no URL-safety check of its own
    on `topic_url` - `server/notify.py`'s `_url_is_safe()`-gated send is
    the one place that validates it, at send time (D-25's own boundary),
    so there is no second, driftable copy of that gate here.

    Each supplied (non-None) value is checked before anything is written:
    `theme`/`tracked_runway`/`calendar_theme_id`/`screen_id` against their registries
    with an explicit membership test, `led_enabled`/`quiet_hours_enabled`/
    `display_enabled` with an explicit `isinstance(..., bool)` type check
    (there is no registry for a boolean), `quiet_hours_start`/
    `quiet_hours_end` against the `_HHMM_RE` shape gate, `wake_interval_s`
    against the bounded-int gate (`isinstance(value, int) and not
    isinstance(value, bool)`, then `[WAKE_INTERVAL_MIN_S,
    WAKE_INTERVAL_MAX_S]` inclusive), and `theme_arriving` against a
    three-state contract described below. An unknown/wrong-typed value
    raises `ValueError` naming both the bounds (for `wake_interval_s`) or the
    registry (for the others) and the rejected value - and leaves any
    pre-existing file byte-identical (T-06-01-01/T-06-01-06). A value left
    `None` is carried over unchanged from the current on-disk config
    (falling back to the documented defaults if none exists yet), so a
    caller updating only the theme never has to also resupply the runway,
    the LED flag, the quiet-hours fields, wake_interval_s, display_enabled,
    or calendar_theme_id.

    Because `None` means "not supplied / carry forward" for every field,
    there is no way to clear an already-set `wake_interval_s` back to unset
    through this function - that is the resolution of 11-RESEARCH.md's Open
    Question 2 (an empty numeric input means "leave unchanged", never
    "reject the save"), not an oversight.

    `calendar_theme_id` (phase 16 plan 02) is genuinely clearable, but
    via a DIFFERENT mechanism from `theme_arriving`'s own sentinel
    (below): the empty string is accepted here as a normal, storable
    non-`None` value (21-05-PLAN.md Task 2, D-09/R-07 — the Frame
    colours card's own "Same as departures" chip submits it), and
    `normalise_calendar_theme_id()`'s existing degrade-to-`None`
    contract on the READ path treats a stored `""` exactly like any
    other non-member string. No sentinel object is needed for this key
    specifically because, unlike `theme_arriving`, its own clear signal
    (`""`) can never collide with "not supplied" (`None`) — the two are
    already distinct Python values.

    `theme_arriving` (D-04/D-05) is the one field with a genuinely different,
    three-state argument contract, because its own historical UI (an
    arrivals-theme-override checkbox, now retired) could not distinguish
    "not supplied" from "explicitly clear" using the submitted id alone
    (both would submit no theme_arriving value at all) — a distinction
    `wake_interval_s` and `calendar_theme_id` deliberately do not need:
      - `None` (the default): not supplied, carry the current on-disk value
        forward - the same meaning `None` has for every other field here.
      - `CLEAR_THEME_ARRIVING` (a distinct module-level sentinel, compared by
        identity): explicitly clear the override back to `None` (meaning "no
        override, same as `theme`").
      - any other value: must be a `THEMES` member, or `ValueError` is raised
        and nothing is written.

    Writes with the same tmp-write-then-os.replace() idiom
    server/poll_loop.py's save_poll_state() uses, including the except
    branch that removes a stray `.tmp` file before re-raising - a crash
    mid-write can never leave a half-written config, and a rejected write
    never leaves a `.tmp` file behind either, since validation happens
    before the file is ever touched.
    """
    if theme is not None and theme not in THEMES:
        raise ValueError("unknown theme id %r (expected one of %r)" % (theme, THEME_IDS))
    if theme_arriving is not None and theme_arriving is not CLEAR_THEME_ARRIVING and theme_arriving not in THEMES:
        raise ValueError("unknown theme_arriving id %r (expected None, CLEAR_THEME_ARRIVING, or one of %r)" % (theme_arriving, THEME_IDS))
    # 21-05-PLAN.md Task 2 (D-09/R-07, companion/pages/config_page.py's
    # own handle_post()): the empty string is now a THIRD, deliberately
    # accepted write-time value, alongside None (carry forward) and a
    # real theme id (set it) — the Frame colours card's own "Same as
    # departures" chip submits "" for this field, and this validation
    # gate must not reject it before it is ever stored. Unlike
    # theme_arriving, this needs no CLEAR_THEME_ARRIVING-style sentinel:
    # "" is stored as a genuine (non-None) value below, exactly like any
    # other string, and normalise_calendar_theme_id() (the READ path,
    # unchanged by this fix) already degrades any non-member string —
    # including "" — to None on the very next load_device_config() call.
    # Every OTHER consumer of a loaded calendar_theme_id (server/plane/
    # calendar_rules.py, server/plane/colour_rules.py) already
    # membership-tests it before use, so a transiently-stored "" is
    # never treated as a real theme id anywhere in this codebase, even
    # before the next load.
    if calendar_theme_id is not None and calendar_theme_id not in ("",) + THEME_IDS:
        raise ValueError("unknown calendar_theme_id %r (expected None, the empty string, or one of %r)" % (calendar_theme_id, THEME_IDS))
    if tracked_runway is not None and tracked_runway not in RUNWAYS:
        raise ValueError("unknown tracked_runway id %r (expected one of %r)" % (tracked_runway, RUNWAY_IDS))
    if screen_id is not None and screen_id not in SCREEN_IDS:
        raise ValueError("unknown screen_id %r (expected one of %r)" % (screen_id, SCREEN_IDS))
    if led_enabled is not None and not isinstance(led_enabled, bool):
        raise ValueError("led_enabled must be a bool, got %r" % (led_enabled,))
    if quiet_hours_enabled is not None and not isinstance(quiet_hours_enabled, bool):
        raise ValueError("quiet_hours_enabled must be a bool, got %r" % (quiet_hours_enabled,))
    if display_enabled is not None and not isinstance(display_enabled, bool):
        raise ValueError("display_enabled must be a bool, got %r" % (display_enabled,))
    if quiet_hours_start is not None and not (isinstance(quiet_hours_start, str) and _HHMM_RE.match(quiet_hours_start)):
        raise ValueError("quiet_hours_start must be a 24-hour zero-padded HH:MM string, got %r" % (quiet_hours_start,))
    if quiet_hours_end is not None and not (isinstance(quiet_hours_end, str) and _HHMM_RE.match(quiet_hours_end)):
        raise ValueError("quiet_hours_end must be a 24-hour zero-padded HH:MM string, got %r" % (quiet_hours_end,))
    if wake_interval_s is not None and not (
        isinstance(wake_interval_s, int)
        and not isinstance(wake_interval_s, bool)
        and WAKE_INTERVAL_MIN_S <= wake_interval_s <= WAKE_INTERVAL_MAX_S
    ):
        raise ValueError(
            "wake_interval_s must be an int in [%d, %d], got %r"
            % (WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S, wake_interval_s)
        )
    if notifications is not None:
        if not isinstance(notifications, dict):
            raise ValueError("notifications must be a dict, got %r" % (notifications,))
        topic_url = notifications.get("topic_url")
        if topic_url is not None and not isinstance(topic_url, str):
            raise ValueError("notifications['topic_url'] must be a str or None, got %r" % (topic_url,))
        battery_low = notifications.get("battery_low")
        if not isinstance(battery_low, bool):
            raise ValueError("notifications['battery_low'] must be a bool, got %r" % (battery_low,))
        frame_silent = notifications.get("frame_silent")
        if not isinstance(frame_silent, bool):
            raise ValueError("notifications['frame_silent'] must be a bool, got %r" % (frame_silent,))
        lang = notifications.get("lang")
        if lang not in ("en", "fr"):
            raise ValueError("notifications['lang'] must be 'en' or 'fr', got %r" % (lang,))

    current = load_device_config(state_dir)
    # theme_arriving is the one field in this module with three write-time
    # meanings instead of two (D-05): the sentinel clears to None, any other
    # non-None value sets it, and None (the default, meaning "not supplied")
    # carries the current on-disk value forward - the opposite of the
    # resolution wake_interval_s deliberately took, because an unchecked
    # arrivals-theme-override checkbox must genuinely clear the override.
    if theme_arriving is CLEAR_THEME_ARRIVING:
        new_theme_arriving = None
    elif theme_arriving is not None:
        new_theme_arriving = theme_arriving
    else:
        new_theme_arriving = current["theme_arriving"]
    new_config = {
        "theme": theme if theme is not None else current["theme"],
        "theme_arriving": new_theme_arriving,
        "calendar_theme_id": calendar_theme_id if calendar_theme_id is not None else current["calendar_theme_id"],
        "tracked_runway": tracked_runway if tracked_runway is not None else current["tracked_runway"],
        "led_enabled": led_enabled if led_enabled is not None else current["led_enabled"],
        "quiet_hours_enabled": quiet_hours_enabled if quiet_hours_enabled is not None else current["quiet_hours_enabled"],
        "quiet_hours_start": quiet_hours_start if quiet_hours_start is not None else current["quiet_hours_start"],
        "quiet_hours_end": quiet_hours_end if quiet_hours_end is not None else current["quiet_hours_end"],
        "wake_interval_s": wake_interval_s if wake_interval_s is not None else current["wake_interval_s"],
        "display_enabled": display_enabled if display_enabled is not None else current["display_enabled"],
        "screen_id": screen_id if screen_id is not None else current["screen_id"],
        "notifications": (
            {
                "topic_url": notifications.get("topic_url"),
                "battery_low": notifications.get("battery_low"),
                "frame_silent": notifications.get("frame_silent"),
                "lang": notifications.get("lang"),
            }
            if notifications is not None
            else current["notifications"]
        ),
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
