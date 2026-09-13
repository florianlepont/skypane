#!/usr/bin/env python3
"""companion/theme_preview.py — on-demand, disk-cached rendered theme
previews for the Settings theme picker (phase 06.6.4.1.1, D-03/D-04/D-05/
D-06/D-07).

Three things a future reader needs and cannot infer from the code alone:

1. **This is the D-04 decision.** The audit's own text proposed a cheap
   CSS/SVG approximation of each theme (colour swatches only); the
   developer explicitly asked for a genuine render through
   `server.plane.render.build_canvas()` instead, accepting new rendering
   and caching infrastructure cost over the cheaper mockup. Nothing in
   this module may be replaced with a CSS/SVG stand-in without reopening
   that decision.

2. **The chip grid still renders the FIXED, fictional scene (D-06) — this
   still matters, unchanged, for the same original reason: the 18 chips
   must all render the SAME scene so they stay comparable side by side,
   which is the entire point of a side-by-side theme picker.**
   `THEME_PREVIEW_FLIGHT`/`THEME_PREVIEW_ROUTE`/
   `THEME_PREVIEW_PREVIOUS_FLIGHT`/`THEME_PREVIEW_PREVIOUS_ROUTE` below
   remain module-level constants, never derived from `server.history_db`,
   `server.poll_loop`'s in-memory state, or any request parameter, for
   every call that omits `live_event`. D-23 (phase 20) adds exactly ONE
   live variant on top of this: `preview_png_bytes()`/
   `cached_preview_bytes()` accept an optional `live_event` (a
   `runway_events` row), rendered instead of the fixture ONLY when a
   caller explicitly passes one — this never happens for the 18-chip
   grid, only for the single large live preview above it. The live
   render's cache key (`cache_path()`/`preview_signature()`'s new
   `live_event_id` axis) is folded from the event's own row id, so a
   newer flight is a cache MISS, never a stale hit served forever
   (Pitfall 7) — this is what makes the live variant safe to add without
   reopening D-05's on-demand-cached-to-disk design: the cache still
   grows by exactly one file per (theme, event) pair, never re-rendered
   on every poll cycle.

3. **`build_canvas()` is called, not `render_panel()`.** This module needs
   a viewable Pillow image to crop and downscale for a `<img>` tag, not
   `render_panel()`'s packed 960,000-byte wire format for the physical
   e-paper controller.

Deliberate naming departure from precedent: `companion/pages/config_page.py`
defines `RUNWAY_IMAGE_ROUTE_PREFIX` in the *emitter* (the page module that
renders the `<img>` tags), and `companion/app.py` rebinds it from there.
Here the prefix instead lives with the *mechanism* (this module), and both
`companion/app.py` and (in a later plan) `companion/pages/config_page.py`
rebind `THEME_PREVIEW_ROUTE_PREFIX` from this one definition site. Same
one-definition-site discipline as the runway-image precedent, different
home — chosen because the render/cache mechanism, not any one page, is the
natural owner of a route that will soon be referenced from two page
modules.
"""
import hashlib
import io
import os

from PIL import Image

from server import device_config, panel_format
from server.plane import render

THEME_PREVIEW_ROUTE_PREFIX = "/theme-preview/"
THEME_PREVIEW_ALT_TEMPLATE = "Sample panel rendered in the %s theme"

# The fixed scene (D-06). `server/plane/render.py` has no train renderer —
# the panel engine only ever composes a main flight card plus a previous
# flight card (D-25/D-26 in render.py's own module docstring) — so "a
# fictional departing flight + a fictional arriving train" is realised here
# as a departing main flight with an arriving previous flight, the richest
# two-block composition today's engine can produce. A future reader should
# not go hunting for a train render path; there isn't one yet.
#
# These are this module's OWN fixture constants, deliberately not imported
# from render.py's private `_PREVIEW_ROUTE`/`_PREVIEW_PREVIOUS_ROUTE`
# manual-QA fixtures — those are free to change without notice (they carry
# no stability contract), and this module's 16 previews must all render
# against the exact same scene every time, forever, independent of
# render.py's own CLI fixtures drifting.
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

# Full canvas width, a 450px-tall horizontal slice of the panel's
# colour-bearing illustration band. Exactly 8:3 (1200:450), matching
# THEME_PREVIEW_SIZE below so the final resize never distorts the crop.
#
# TWO PROPERTIES ARE LOAD-BEARING and must both survive any future change
# to this constant: the exact 8:3 ratio, and a PAIRWISE-DISTINCT mean RGB
# across every registered theme (so no two themes can render identical
# chips). Measured (2026-09-03) against 16 themes, re-confirmed
# (2026-09-05) against the widened 18-theme set (quick task 260905-e04's
# two tone-on-tone band_*_field themes), and re-measured again below.
#
# B6 (22-AUDIT.md, 22-10-PLAN.md Task 2): the box was (0, 420, 1200, 870)
# and sliced the render's own caption mid-glyph — "AF1789 to New York"
# cut horizontally — at every chip size and in the large live preview. A
# sliced glyph reads as a rendering bug rather than as a crop.
#
# The fix EXCLUDES the caption entirely rather than including it: a
# 160x108 chip (104px compact after X6) cannot render legible caption
# text at any crop, and the chip's job is to show the theme's COLOURS —
# its illustration band plus its two real-palette swatch dots. Measured
# ink bands in the 1200x1600 fixed-scene render (rows carrying any
# non-background pixel): 70-84 the top labels, 489-792 the main aircraft,
# 859-888 the caption, 904-919 the airline sub-caption, 1122+ the
# previous-flight card. render.py anchors the main text block at
# `main_placement.content[3] + MAIN_TEXT_GAP_PX` = 847 for every theme,
# band themes included, so 847 is the theme-independent ceiling.
#
# This box is 390..840: it clears the top labels by 305px, contains the
# whole main illustration, and ends 7px above the text block's own anchor
# and 19px above the caption's first inked row. Re-measured (2026-09-13)
# across all 18 registered themes: still pairwise-distinct, minimum
# per-channel-sum separation 14.845 (the box it replaces measured 14.968
# on the same metric — an unchanged margin, not a newly-narrow one).
#
# NOT a CSS `object-fit` workaround: this is a server-side constant, and
# the PNG it produces is served to the chips, the live preview and every
# other consumer. Fixing it in the stylesheet would leave the image wrong
# for all of them. `preview_signature()` below folds this constant into
# the cache digest, so changing it is a clean cache MISS with no purge
# step — THEME_PREVIEW_CACHE_VERSION did not need bumping.
THEME_PREVIEW_CROP_BOX = (0, 390, 1200, 840)

# 2x D-07's ~160x60 figure, so the chip's 160px-wide band stays crisp on a
# 2x (Retina-class) display. The panel is DOWNscaled here (1200 -> 320,
# LANCZOS) — the opposite of UIR-09's upscaled-thumbnail defect — and must
# stay that way; do not grow this past the source crop's resolution.
THEME_PREVIEW_SIZE = (320, 120)

THEME_PREVIEW_CACHE_DIRNAME = "theme_previews"
# Bumping this is the manual escape hatch for a change preview_signature()
# cannot see on its own — a render-geometry change inside render.py itself
# (e.g. a relayout that shifts what THEME_PREVIEW_CROP_BOX actually
# captures). See preview_signature()'s own docstring for the full scheme.
THEME_PREVIEW_CACHE_VERSION = 1


# D-23: the two `confirmed_state` values `build_canvas()` accepts that a
# runway_events row can legitimately carry ("empty" is never recorded to
# this table — history_db.record_runway_event() is only ever called with
# a real detection, never the empty state).
_LIVE_EVENT_VALID_STATES = ("departing", "arriving")


def _live_flight_route_state(live_event):
    """Map one `runway_events` row (a dict shaped like
    `server.history_db.recent_runway_events()`'s own return value) onto
    `build_canvas()`'s `flight`/`route`/`state` arguments (D-23), falling
    back field by field to this module's own fixed fixture constants for
    anything the row does not carry — so a partial row (a stale schema,
    a route-enrichment miss, a falsy column) can never raise.

    `runway_events` has no city-name or IATA-callsign columns at all
    (`server/history_db.py`'s own `CREATE TABLE` schema) — this function
    never invents them; `origin_city`/`destination_city`/`callsign_iata`
    always come from `THEME_PREVIEW_ROUTE`. Only `hex`/`callsign` (for
    `flight`), `airline`/`origin`/`destination` (for `route`), and
    `confirmed_state` (for `state`) are ever read from `live_event`, and
    each still degrades to the matching fixture value when falsy or, for
    `confirmed_state`, not one of the two legal values.
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
    """Render either the fixed scene (`live_event=None`, byte-identical
    to before this function grew a second argument) or `live_event` (a
    `runway_events` row, D-23) through `render.build_canvas()` in
    `theme_id`, crop to `THEME_PREVIEW_CROP_BOX`, downscale to
    `THEME_PREVIEW_SIZE`, and return PNG bytes.

    A live render omits the previous-flight card entirely
    (`previous_flight=None`/`previous_route=None`/`previous_state=None`,
    all optional per `build_canvas()`'s own signature) — a live render
    has no "previous detection" fixture to pair it with, unlike the fixed
    scene's own `THEME_PREVIEW_PREVIOUS_*` constants.

    Ordering is load-bearing: `.convert("RGB")` happens BEFORE crop/resize.
    `build_canvas()` returns a "P"-mode (palette-indexed) image; resampling
    a "P"-mode image during `.resize()` interpolates palette *indices*,
    not colours — producing pixel values that are not even in the panel's
    6-color palette. Converting to RGB first makes the LANCZOS resize
    interpolate real colour values, exactly like `render.py`'s own CLI
    `--preview` path (`canvas.convert("RGB").save(...)`) does before
    writing a viewable file. This ordering is unchanged by `live_event`.
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
    """A 12-hex-character cache-key discriminator for `theme_id` — the
    concrete answer to D-05's "confirm the cache scheme during planning"
    instruction.

    Keying a cache filename on the theme id ALONE would go stale silently
    the moment the panel ink is ever re-tuned again — which this project
    has already done once, on real glass (07-01's Blue/Green correction;
    see `panel_format.PALETTE_RGB`'s own comment block and
    `config_page._palette_hex()`'s docstring, which promises a re-tune
    "automatically updates every swatch"). Folding the theme's own THEMES
    entry AND `panel_format.PALETTE_RGB` into the signature makes a
    re-tune a cache MISS (a new signature, a new filename) instead of a
    stale image silently served forever, with no purge step for anyone to
    remember. `THEME_PREVIEW_CROP_BOX`/`THEME_PREVIEW_SIZE` are folded in
    too so a future change to either of those constants also misses
    cleanly. `THEME_PREVIEW_CACHE_VERSION` is the remaining manual escape
    hatch, for a change this signature cannot see on its own — a
    render-geometry change inside render.py itself that alters what the
    crop box captures without changing any of the above.

    D-23 (phase 20, Pitfall 7): `live_event_id` is folded into the digest
    too, so a newer flight (a different row id) is a cache MISS, never a
    stale hit served forever — the reason the live theme preview needed
    a cache-key change at all. `cache_path()` below is the only caller
    that ever passes a non-`None` value here, and only after coercing it
    to `int` (or `None` on any coercion failure) — this function never
    validates `live_event_id` itself; it is opaque digest input either
    way, never a path component.
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
    `state_dir` is falsy OR `theme_id` is not a real key of
    `device_config.THEMES`.

    This membership guard is at the boundary itself, deliberately
    duplicating the route handler's own check rather than trusting it —
    exactly the discipline `illustrations.override_path_for_key()` carries
    (T-v26-01-01): no path component here is ever built from an id that is
    not a literal key of the registry, whether or not a caller upstream
    already validated it.

    D-23 (phase 20, T-20-14): `live_event_id` is coerced to `int()` inside
    a `try`/`except` — ANY failure (a non-numeric string, a
    path-traversal-shaped value, `None`) degrades to the fixed literal
    discriminator `"sample"`, so no string field from a `runway_events`
    row can EVER reach a path component here; only a genuine integer row
    id, or the literal "sample", ever does. The same (coerced) value is
    threaded into `preview_signature()`'s digest too, so the filename and
    the signature can never disagree about which event this cache entry
    is for.
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


def cached_preview_bytes(state_dir, theme_id, live_event=None):
    """Return `theme_id`'s preview PNG bytes, reading the disk cache on a
    hit and rendering + writing it on a miss. Returns `None` for anything
    `cache_path()` refuses (a falsy `state_dir` or an unknown `theme_id`).

    D-23: `live_event` (a `runway_events` row, or `None`) is threaded
    through twice — its `"id"` reaches `cache_path()`/`preview_signature()`
    as the cache-key discriminator, and the row itself reaches
    `preview_png_bytes()` to actually render it. `live_event=None`
    (the default) is byte-identical to this function's pre-D-23 contract:
    same cache path, same rendered bytes, same cold/warm-cache behaviour.

    Writes are atomic-rename, same discipline as
    `Handler._handle_illustration_replace()`'s own temp-file dance: render
    to a temp file inside the cache directory, named from the
    already-validated key plus this process's pid (never from anything a
    caller supplies), then `os.replace()` onto the final path. This is
    what lets two concurrent `ThreadingHTTPServer` worker threads race the
    same cold theme without either ever serving a half-written PNG — the
    loser's `os.replace()` still lands a complete, valid file, just
    slightly after the winner's.

    `OSError` propagates to the caller uncaught — the route handles it —
    matching `illustration_normalize.cached_normalized_png_bytes()`'s own
    documented contract.
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
    tmp_path = os.path.join(
        directory, ".%s.%d.tmp" % (theme_id, os.getpid()))
    with open(tmp_path, "wb") as fh:
        fh.write(payload)
    os.replace(tmp_path, path)
    return payload
