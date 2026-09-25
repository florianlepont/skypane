#!/usr/bin/env python3
"""Single source of truth for every user-settable SkyPane device setting -
the theme id, tracked-runway id, and related settings, picked on the
companion web page and consumed on the device's next scheduled poll.

Separate file (`device_config.json`) from `poll_state.json`: a second
writer touching poll_state.json would race server/poll_loop.py's own
read-modify-write cycle every 30s.

Leaf module: stdlib plus `server.panel_format` only; must never import
`server.plane.detect`, `server.plane.render`, or `server.poll_loop`.

Adding a theme: append one entry to `THEMES`; every accessor below
derives from it, no other call-site change needed.

Print-free by design - never log or print the config file's contents.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Allow both `import server.device_config` (package import) and direct
# script execution: sys.path[0] is server/ itself when this file is
# executed directly, so the repo root must be added by hand before the
# absolute `server.panel_format` import below can resolve.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server.panel_format import IDX_BLACK, IDX_BLUE, IDX_GREEN, IDX_RED, IDX_WHITE, IDX_YELLOW

DEFAULT_THEME_ID = "white"
DEFAULT_RUNWAY_ID = "3"
DEFAULT_LED_ENABLED = True  # Matches the LED's current hardcoded always-on behaviour, so nothing changes until a user opts out.
DEFAULT_QUIET_HOURS_ENABLED = False  # An explicit boolean independent of the stored times - never "empty fields mean off" - so nothing changes for any existing installation until a user opts in.
DEFAULT_QUIET_HOURS_START = "23:00"  # One daily recurring window, never per-weekday.
DEFAULT_QUIET_HOURS_END = "07:00"  # One daily recurring window, never per-weekday.
DEFAULT_DISPLAY_ENABLED = True  # An explicit boolean following the
# DEFAULT_LED_ENABLED/DEFAULT_QUIET_HOURS_ENABLED precedent, never an
# absence-means-off convention, so nothing changes for an installation
# already in service until someone opts in.

# Bounds for the stored wake_interval_s field. 60 mirrors firmware's
# FP_MIN_REFRESH_SPACING_S default (a conservative margin against
# needless redraws, not a vendor minimum - GDEP133C02 specifies none).
# 3600 is the developer-confirmed ceiling.
WAKE_INTERVAL_MIN_S = 60
WAKE_INTERVAL_MAX_S = 3600

# Fixed off-state check-in cadence while display_enabled is False,
# independent of wake_interval_s. stub-server/byos_server.py
# independently redefines this value and must be kept in step.
DISPLAY_OFF_SLEEP_S = 300

# Fixed check-in cadence while BATTERY EMPTY is active - one hour, since
# detection is skipped entirely while parked. Kept in step with
# stub-server/byos_server.py's independent copy.
BATTERY_CRITICAL_SLEEP_S = 3600

# No DEFAULT_WAKE_INTERVAL_S: wake_interval_s's unset state is `None`
# (the real fallback is the deployed SKYPANE_SLEEP_S, not knowable here).

# Sentinel distinguishing "clear theme_arriving back to None" from
# `None`'s own "not supplied, carry forward" meaning - mirrors
# companion/pages/health_page.py's `_DB_UNAVAILABLE` idiom. Compared by
# identity, never equality.
CLEAR_THEME_ARRIVING = object()

# Anchored with `\Z`, not `$`: `$` also matches before a trailing
# newline, which would let a dirty "07:00\n" reach the panel's body text
# unvalidated.
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")

# Fixed physical location, so the timezone is hardcoded, not
# per-installation.
QUIET_HOURS_TZ = ZoneInfo("Europe/Paris")

# --- Theme registry ----------------------------------------------------
#
# Always reference panel_format's IDX_* constants, never a bare integer.
# "dithered" selects a flat field vs. the same ink dithered ~40% toward
# White (a flat saturated field reads too harsh at full-panel coverage).
# "weight" isn't derivable from "dithered" alone: flat fields read best
# Regular; dithered fields need Bold except Yellow, which stays legible
# Regular even dithered.
#
# The old two-tone "sky" pairing is retired; a stale `"theme": "sky"`
# degrades safely to DEFAULT_THEME_ID via normalise_theme_id().
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
    # Diagonal-band themes: base canvas renders as build_canvas("white");
    # only label, band_index and band_dithered vary between these 5. Read
    # via theme_is_band()/theme_band_index()/theme_band_dithered() below,
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
    # Two "tone-on-tone" themes whose field is not White: base-canvas
    # fields copied from the matching `_light` theme (ink/weight too -
    # draw_main_text_block() forces white ink for every band theme, so a
    # row's own ink_index only colours outside the band). band_index
    # equals the field colour on purpose; band_dithered is False for a
    # solid diagonal.
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
# Keys must match adsb-test/runway3.json's key set (checked in
# test_poll_loop.py) and the filename stem
# companion/static/RUNWAY-IMAGES.md's `runway-{id}.png` contract keys off
# of - never rename them. `tag_text`/`empty_heading` render onto the
# physical panel and stay unchanged; only `label` (the web picker's
# value) is plain English with the ADP runway number and heading-pair in
# parentheses.
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

# --- Screen-id seam --------------------------------------------------------
#
# Duplicate (not import) of companion/screens.py's SCREEN_IDS/
# DEFAULT_SCREEN_ID - server/ must never import companion/.
# server/test_config_history.py pins the two equal.
DEFAULT_SCREEN_ID = "plane-frame"
SCREEN_IDS = ("plane-frame",)

# First dict-valued field in this registry. `topic_url` is write-only,
# stored verbatim for poll_loop.py's notification sender to POST to.
# `lang` is a persisted en/fr snapshot since the poll loop has no browser.
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
    """`value` unchanged if it's a string member of `THEMES`, else
    `DEFAULT_THEME_ID`. Never raises.
    """
    if isinstance(value, str) and value in THEMES:
        return value
    return DEFAULT_THEME_ID


def normalise_theme_arriving(value):
    """`value` unchanged if it's a string member of `THEMES`, else None -
    never raises. Unlike `normalise_theme_id()`, degrades to `None`
    (meaning "no override, same as `theme`"), not to a documented
    default - there's no sensible default arrivals theme to fall back to.
    """
    if isinstance(value, str) and value in THEMES:
        return value
    return None


def normalise_calendar_theme_id(value):
    """`value` unchanged if it's a string member of `THEMES`, else None -
    never raises. `None` means "no calendar theme chosen"; degrading to
    `DEFAULT_THEME_ID` instead would look like a calendar match happened
    when it didn't. No `CLEAR_THEME_ARRIVING`-style sentinel needed: the
    empty string is itself a genuine, storable "clear" value at the write
    path, distinct from `None`'s "not supplied".
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
    """`value` unchanged if it's a string member of `SCREEN_IDS`, else
    `DEFAULT_SCREEN_ID`. Never raises."""
    if isinstance(value, str) and value in SCREEN_IDS:
        return value
    return DEFAULT_SCREEN_ID


def normalise_notifications(value):
    """A well-formed notifications sub-dict - degrades to
    `DEFAULT_NOTIFICATIONS` wholesale for a non-dict, per-field otherwise.
    Never raises. `topic_url` is not URL-validated here -
    `server/notify.py`'s `_url_is_safe()` does that at send time.
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
    """`value` unchanged if `isinstance(value, bool)`, else
    `DEFAULT_LED_ENABLED`. Never raises; an int like 0/1 is not a bool
    and degrades to the default, intentionally.
    """
    if isinstance(value, bool):
        return value
    return DEFAULT_LED_ENABLED


def normalise_quiet_hours_enabled(value):
    """Same bool-or-default contract as normalise_led_enabled(), against
    `DEFAULT_QUIET_HOURS_ENABLED`.
    """
    if isinstance(value, bool):
        return value
    return DEFAULT_QUIET_HOURS_ENABLED


def normalise_display_enabled(value):
    """Same bool-or-default contract as normalise_led_enabled(), against
    `DEFAULT_DISPLAY_ENABLED`. Because the default is True, every
    degradation path (missing/unreadable/malformed config) leaves the
    display ON - a corrupted config can never be why a frame goes dark.
    """
    if isinstance(value, bool):
        return value
    return DEFAULT_DISPLAY_ENABLED


def normalise_quiet_hours_time(value, default):
    """`value` unchanged if it matches the `_HHMM_RE` shape gate, else
    `default`. Shared by both start/end fields so they can't drift apart
    on validation strictness.
    """
    if isinstance(value, str) and _HHMM_RE.match(value):
        return value
    return default


def normalise_wake_interval_s(value):
    """`value` unchanged if it's a positive int (not bool) within
    [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S], else None - meaning
    "never explicitly set", not "degraded to a default" (there is none).
    `isinstance(True, int)` is True in Python, so the bool exclusion is
    load-bearing, not defensive noise.
    """
    if isinstance(value, int) and not isinstance(value, bool) and WAKE_INTERVAL_MIN_S <= value <= WAKE_INTERVAL_MAX_S:
        return value
    return None


def load_device_config(state_dir):
    """Read device_config.json; a missing/unreadable/malformed/non-dict
    file falls back to an empty dict, never raises. Always returns all
    twelve keys with valid values via the normalise_*() functions above,
    so a hostile or stale value on disk never reaches a caller.
    `theme_arriving`, `calendar_theme_id`, `screen_id`, `notifications`
    are read with `.get()` so an older file missing them resolves to
    their documented default. `wake_interval_s`, `theme_arriving`,
    `calendar_theme_id` are the three keys whose valid value set includes
    `None`.
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
    """Validate and persist any subset of the device settings; `None`
    means "not supplied, carry the current on-disk value forward" for
    every field. An invalid non-None value raises `ValueError` naming the
    rejected value and the registry/bounds, before anything is written -
    a rejected write leaves any pre-existing file byte-identical.

    `theme_arriving` has a three-state contract instead of two: `None`
    carries forward, `CLEAR_THEME_ARRIVING` (an identity-compared
    sentinel) clears the override to `None`, any other value must be a
    THEMES member. `calendar_theme_id` needs no sentinel - the empty
    string is itself a genuine "clear" value, distinct from `None`.
    `notifications` is the one dict-valued field; its sub-keys are each
    validated individually, and its `topic_url` is not URL-checked here
    (`server/notify.py` does that at send time).

    Writes with the same tmp-write-then-os.replace() idiom
    server/poll_loop.py's save_poll_state() uses.
    """
    if theme is not None and theme not in THEMES:
        raise ValueError("unknown theme id %r (expected one of %r)" % (theme, THEME_IDS))
    if theme_arriving is not None and theme_arriving is not CLEAR_THEME_ARRIVING and theme_arriving not in THEMES:
        raise ValueError("unknown theme_arriving id %r (expected None, CLEAR_THEME_ARRIVING, or one of %r)" % (theme_arriving, THEME_IDS))
    # The empty string is a third valid write-time value (carry-forward
    # None, set to a real id, or clear via "") - the Frame colours card's
    # "Same as departures" chip submits it, and this gate must accept it.
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
    # theme_arriving's three write-time meanings: sentinel clears to None,
    # any other non-None value sets it, None carries forward.
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
# See seconds_until_quiet_hours_end()'s own docstring for its two
# DST-safety properties.


def seconds_until_quiet_hours_end(now_utc, start_hm, end_hm):
    """Seconds remaining until the daily [start_hm, end_hm) Europe/Paris
    window's end, or None when `now_utc` falls outside it. Wraps midnight
    when `end_hm <= start_hm`; a zero-width window (`start_hm == end_hm`)
    is never active.

    Arithmetic core only, no validation: `now_utc` must be timezone-aware;
    `start_hm`/`end_hm` must already match `_HHMM_RE`.
    stub-server/byos_server.py duplicates this byte-for-byte.

    Two DST-safety properties: (a) the final subtraction converts to UTC
    first (`end_dt.astimezone(timezone.utc) - now_utc`), since two aware
    datetimes sharing a `tzinfo` subtract by wall-clock numerals only,
    which is wrong by an hour across a DST transition; (b) a boundary
    configured inside the 02:00-03:00 transition hour can resolve up to
    an hour off (PEP 495 `fold=0`, accepted, not engineered around).
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
    """`(seconds_remaining, end_hm)`, or `(None, None)` when quiet hours
    aren't enabled or `seconds_until_quiet_hours_end()` returns None.
    `now_epoch` is epoch seconds (float); never raises, even for a
    hostile value.
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
# Every accessor below takes an already-normalised id and never raises
# for a valid, registry-member id.


def theme_background_index(state, theme_id):
    """The theme's background palette index for `state`
    ("departing"/"arriving"). Raises `ValueError` for any other state.
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
    """Whether `theme_id`'s background is dithered rather than flat - see
    THEMES' own comment.
    """
    return THEMES[theme_id]["dithered"]


def theme_weight(theme_id):
    """`theme_id`'s PT Serif weight ("regular"/"bold"); not derivable from
    `theme_dithered()` alone - see THEMES' own comment.
    """
    return THEMES[theme_id]["weight"]


def theme_is_band(theme_id):
    """Whether `theme_id` is a diagonal-band theme - true iff its THEMES
    entry carries the band-only `"band_index"` key.
    """
    return "band_index" in THEMES[theme_id]


def theme_band_index(theme_id):
    """`theme_id`'s diagonal band colour as a panel_format.IDX_* constant,
    or `None` for a non-band theme.
    """
    return THEMES[theme_id].get("band_index")


def theme_band_dithered(theme_id):
    """Whether `theme_id`'s diagonal band is dithered; `False` for a
    non-band theme.
    """
    return THEMES[theme_id].get("band_dithered", False)


def runway_tag_text(runway_id):
    return RUNWAYS[runway_id]["tag_text"]


def runway_empty_heading(runway_id):
    return RUNWAYS[runway_id]["empty_heading"]


def runway_label(runway_id):
    return RUNWAYS[runway_id]["label"]
