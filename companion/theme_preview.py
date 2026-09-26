#!/usr/bin/env python3
"""On-demand, disk-cached rendered theme previews for the Settings theme
picker. Renders through `server.plane.render.build_canvas()` (a real
Pillow image to crop/downscale), not a cheap CSS/SVG mockup and not
`render_panel()`'s packed wire format.

The 18-chip grid always renders the same fixed fictional scene, so the
chips stay comparable side by side. The single large preview can
instead render a live `runway_events` row when the caller passes
`live_event`; its cache key folds in the event's row id so a newer
flight is a cache miss, never a stale hit.
"""
import hashlib
import io
import os
import re

from PIL import Image

from server import atomic_io, device_config, panel_format
from server.plane import render

THEME_PREVIEW_ROUTE_PREFIX = "/theme-preview/"
THEME_PREVIEW_ALT_TEMPLATE = "Sample panel rendered in the %s theme"

# The fixed scene: a departing main flight + an arriving previous
# flight, the richest two-block composition the panel engine can
# produce (there is no train renderer). These are this module's own
# fixture constants, not render.py's private CLI fixtures — those carry
# no stability contract and must not drift these previews.
THEME_PREVIEW_FLIGHT = {"hex": "3946a1", "callsign": "AFR1789"}
THEME_PREVIEW_ROUTE = {
    "airline_name": "Air France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "JFK",
    "destination_city": "New York",
    "callsign_iata": "AF1789",
}
THEME_PREVIEW_PREVIOUS_FLIGHT = {"hex": "3466ab", "callsign": "VLG1523"}
THEME_PREVIEW_PREVIOUS_ROUTE = {
    "airline_name": "Vueling Airlines",
    "origin_iata": "BCN",
    "origin_city": "Barcelona",
    "destination_iata": "ORY",
    "destination_city": "Paris",
    "callsign_iata": "VY1523",
}
THEME_PREVIEW_STATE = "departing"
THEME_PREVIEW_PREVIOUS_STATE = "arriving"

# A 450px-tall slice of the illustration band, 8:3 to match
# THEME_PREVIEW_SIZE. Excludes the caption (a 160x108 chip can't render
# it legibly, and an earlier box that included it sliced a glyph
# mid-caption); still pairwise-distinct across all 18 themes' mean RGB.
THEME_PREVIEW_CROP_BOX = (0, 390, 1200, 840)

# 2x the chip's ~160x60 display size, so it stays crisp on Retina-class
# displays. Downscaled (1200 -> 320, LANCZOS); never grow past the
# source crop's resolution — an upscaled thumbnail looks worse.
THEME_PREVIEW_SIZE = (320, 120)

THEME_PREVIEW_CACHE_DIRNAME = "theme_previews"
# Manual escape hatch for a render-geometry change inside render.py
# that preview_signature() cannot see on its own.
THEME_PREVIEW_CACHE_VERSION = 1

# Bound on the cache directory's total file count, oldest evicted first -
# 18 themes x a handful of concurrently-live_event previews stays well
# under this; a much larger number would only ever accumulate from a
# runway with many distinct live events, not from normal Settings-page
# browsing.
THEME_PREVIEW_CACHE_MAX_FILES = 64

# Matches cached_preview_bytes()'s own filename shape: a stable
# "<theme>-<event or 'sample'>" prefix followed by exactly the 12-hex
# signature suffix preview_signature() produces. Anchored full-match only
# (never a startswith/substring check), so a theme id that is itself a
# prefix of another theme id (or of another theme's event-qualified name)
# can never match that other theme's files - the exact prefix plus
# exactly 12 hex characters plus ".png" is the only shape this accepts.
_PREVIEW_FILENAME_RE = re.compile(r"(?P<prefix>.+)-[0-9a-f]{12}\.png\Z")


# "empty" is never recorded to runway_events — only a real detection is.
_LIVE_EVENT_VALID_STATES = ("departing", "arriving")


def _live_flight_route_state(live_event):
    """Map one `runway_events` row onto `build_canvas()`'s `flight`/
    `route`/`state` arguments, falling back field by field to this
    module's fixture constants for anything the row doesn't carry, so a
    partial row can never raise. `runway_events` has no city-name or
    IATA-callsign columns, so those always come from the fixture.
    """
    flight = {
        "hex": live_event.get("hex") or THEME_PREVIEW_FLIGHT["hex"],
        "callsign": live_event.get("callsign") or THEME_PREVIEW_FLIGHT["callsign"],
    }
    route = {
        "airline_name": (
            live_event.get("airline") or THEME_PREVIEW_ROUTE["airline_name"]),
        "origin_iata": (
            live_event.get("origin") or THEME_PREVIEW_ROUTE["origin_iata"]),
        "destination_iata": (
            live_event.get("destination") or THEME_PREVIEW_ROUTE["destination_iata"]),
        "origin_city": THEME_PREVIEW_ROUTE["origin_city"],
        "destination_city": THEME_PREVIEW_ROUTE["destination_city"],
        "callsign_iata": THEME_PREVIEW_ROUTE["callsign_iata"],
    }
    state = live_event.get("confirmed_state")
    if state not in _LIVE_EVENT_VALID_STATES:
        state = THEME_PREVIEW_STATE
    return flight, route, state


def preview_png_bytes(theme_id, live_event=None):
    """Render the fixed scene, or `live_event` (a `runway_events` row)
    when given, through `render.build_canvas()`, crop, downscale, and
    return PNG bytes. A live render omits the previous-flight card.

    `.convert("RGB")` happens before crop/resize, deliberately:
    `build_canvas()` returns a "P"-mode image, and resizing a "P"-mode
    image interpolates palette indices, not colours.
    """
    if live_event is None:
        canvas = render.build_canvas(
            THEME_PREVIEW_FLIGHT,
            THEME_PREVIEW_STATE,
            route=THEME_PREVIEW_ROUTE,
            previous_flight=THEME_PREVIEW_PREVIOUS_FLIGHT,
            previous_route=THEME_PREVIEW_PREVIOUS_ROUTE,
            previous_state=THEME_PREVIEW_PREVIOUS_STATE,
            theme_id=theme_id,
        )
    else:
        flight, route, state = _live_flight_route_state(live_event)
        canvas = render.build_canvas(
            flight, state, route=route, theme_id=theme_id,
        )
    rgb = canvas.convert("RGB")
    cropped = rgb.crop(THEME_PREVIEW_CROP_BOX)
    resized = cropped.resize(THEME_PREVIEW_SIZE, Image.LANCZOS)
    buffer = io.BytesIO()
    resized.save(buffer, format="PNG")
    return buffer.getvalue()


def preview_signature(theme_id, live_event_id=None):
    """A 12-hex-character cache-key discriminator for `theme_id`.
    Folds in the theme's palette (so a real-glass ink re-tune is a
    cache miss, not a stale image forever), the crop/size constants,
    `THEME_PREVIEW_CACHE_VERSION` (the manual escape hatch for a
    render-geometry change this signature can't otherwise see), and
    `live_event_id` (opaque digest input, never a path component).
    """
    digest_input = repr((
        device_config.THEMES[theme_id],
        panel_format.PALETTE_RGB,
        THEME_PREVIEW_CROP_BOX,
        THEME_PREVIEW_SIZE,
        THEME_PREVIEW_CACHE_VERSION,
        live_event_id,
    )).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()[:12]


def cache_dir(state_dir):
    """`{state_dir}/THEME_PREVIEW_CACHE_DIRNAME`, or `None` for a falsy
    `state_dir`. Never creates the directory — read-only computation,
    matching `illustrations.override_dir_for_state_dir()`'s own contract.
    """
    if not state_dir:
        return None
    return os.path.join(state_dir, THEME_PREVIEW_CACHE_DIRNAME)


def cache_path(state_dir, theme_id, live_event_id=None):
    """The on-disk cache path for `theme_id`'s preview, or `None` when
    `state_dir` is falsy or `theme_id` is not a real THEMES key —
    validated at the boundary itself, never trusting an upstream check.

    `live_event_id` is coerced to `int()`; any failure degrades to the
    fixed literal `"sample"`, so no string field from a `runway_events`
    row can ever reach a path component.
    """
    if not state_dir or theme_id not in device_config.THEMES:
        return None
    try:
        event_id = int(live_event_id)
    except (TypeError, ValueError):
        event_id = None
    signature = preview_signature(theme_id, event_id)
    directory = cache_dir(state_dir)
    filename = "%s-%s-%s.png" % (
        theme_id, event_id if event_id is not None else "sample", signature)
    return os.path.join(directory, filename)


def _prune_preview_cache(directory, keep_path):
    """Best-effort cache maintenance after a fresh write to `keep_path`:
    never raises (an `OSError` anywhere below is swallowed - a maintenance
    step must never fail the request the write it follows is serving).

    1. Stale-signature removal: any other file sharing `keep_path`'s exact
       `<theme>-<event or 'sample'>` prefix but a different 12-hex
       signature is removed (a theme re-tune or a render-geometry bump
       leaves the old image behind otherwise, forever).
    2. Bound: if more than `THEME_PREVIEW_CACHE_MAX_FILES` `*.png` files
       (skipping any dotfile) remain, the oldest by mtime are removed
       until the count is back at the bound. `keep_path` is never removed
       by this step.
    """
    try:
        keep_name = os.path.basename(keep_path)
        match = _PREVIEW_FILENAME_RE.fullmatch(keep_name)
        if match:
            stale_re = re.compile(
                r"%s-[0-9a-f]{12}\.png\Z" % re.escape(match.group("prefix")))
            for name in os.listdir(directory):
                if name == keep_name or name.startswith("."):
                    continue
                if stale_re.fullmatch(name):
                    try:
                        os.remove(os.path.join(directory, name))
                    except OSError:
                        pass

        entries = []
        for name in os.listdir(directory):
            if name.startswith(".") or not name.endswith(".png"):
                continue
            candidate = os.path.join(directory, name)
            try:
                mtime = os.stat(candidate).st_mtime
            except OSError:
                continue
            entries.append((mtime, candidate))

        overflow = len(entries) - THEME_PREVIEW_CACHE_MAX_FILES
        if overflow > 0:
            entries.sort(key=lambda entry: entry[0])
            removed = 0
            for _mtime, candidate in entries:
                if removed >= overflow:
                    break
                if candidate == keep_path:
                    continue
                try:
                    os.remove(candidate)
                    removed += 1
                except OSError:
                    pass
    except OSError:
        pass


def cached_preview_bytes(state_dir, theme_id, live_event=None):
    """Return `theme_id`'s preview PNG bytes: disk cache on a hit,
    render + write on a miss. `None` for anything `cache_path()` refuses.

    A miss writes through `atomic_io.atomic_write` (unique per-call temp
    name, so two concurrent worker threads racing the same cold theme
    never serve a half-written PNG, and never collide on the same temp
    file), then prunes the cache via `_prune_preview_cache()` - stale
    signatures for this theme+event are removed and the directory is
    bounded to `THEME_PREVIEW_CACHE_MAX_FILES`. A hit neither writes nor
    prunes. `OSError` propagates to the caller uncaught.
    """
    live_event_id = live_event.get("id") if isinstance(live_event, dict) else None
    path = cache_path(state_dir, theme_id, live_event_id)
    if path is None:
        return None
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        pass
    directory = cache_dir(state_dir)
    os.makedirs(directory, exist_ok=True)
    payload = preview_png_bytes(theme_id, live_event)
    atomic_io.atomic_write(path, payload)
    _prune_preview_cache(directory, path)
    return payload
