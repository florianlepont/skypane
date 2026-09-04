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

2. **The scene is FIXED and fictional (D-06) and must never be wired to
   live flight data.** `THEME_PREVIEW_FLIGHT`/`THEME_PREVIEW_ROUTE`/
   `THEME_PREVIEW_PREVIOUS_FLIGHT`/`THEME_PREVIEW_PREVIOUS_ROUTE` below are
   module-level constants, not derived from `server.history_db`, not from
   `server.poll_loop`'s in-memory state, and not from any request
   parameter. Live data would invalidate the cache on every poll cycle
   (defeating D-05's on-demand-cached-to-disk design) and would make the
   16 previews non-comparable against each other, defeating the entire
   point of a side-by-side theme picker.

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

# Full canvas width, a 450px-tall horizontal slice starting a little past
# the top-row labels. Exactly 8:3 (1200:450), matching THEME_PREVIEW_SIZE
# below so the final resize never distorts the crop. Measured (2026-09-03)
# against all 16 registered themes to yield a pairwise-distinct mean RGB —
# it spans the main illustration/text block and, for the five band themes,
# the diagonal band's own crossing, so every theme paints something
# different inside this box. D-07's "thin band across the top third of the
# chip, cropped from the real 1200x1600 render" is what this constant
# implements.
THEME_PREVIEW_CROP_BOX = (0, 420, 1200, 870)

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


def preview_png_bytes(theme_id):
    """Render the fixed scene through `render.build_canvas()` in
    `theme_id`, crop to `THEME_PREVIEW_CROP_BOX`, downscale to
    `THEME_PREVIEW_SIZE`, and return PNG bytes.

    Ordering is load-bearing: `.convert("RGB")` happens BEFORE crop/resize.
    `build_canvas()` returns a "P"-mode (palette-indexed) image; resampling
    a "P"-mode image during `.resize()` interpolates palette *indices*,
    not colours — producing pixel values that are not even in the panel's
    6-color palette. Converting to RGB first makes the LANCZOS resize
    interpolate real colour values, exactly like `render.py`'s own CLI
    `--preview` path (`canvas.convert("RGB").save(...)`) does before
    writing a viewable file.
    """
    canvas = render.build_canvas(
        THEME_PREVIEW_FLIGHT,
        THEME_PREVIEW_STATE,
        route=THEME_PREVIEW_ROUTE,
        previous_flight=THEME_PREVIEW_PREVIOUS_FLIGHT,
        previous_route=THEME_PREVIEW_PREVIOUS_ROUTE,
        previous_state=THEME_PREVIEW_PREVIOUS_STATE,
        theme_id=theme_id,
    )
    rgb = canvas.convert("RGB")
    cropped = rgb.crop(THEME_PREVIEW_CROP_BOX)
    resized = cropped.resize(THEME_PREVIEW_SIZE, Image.LANCZOS)
    buffer = io.BytesIO()
    resized.save(buffer, format="PNG")
    return buffer.getvalue()


def preview_signature(theme_id):
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
    """
    digest_input = repr((
        device_config.THEMES[theme_id],
        panel_format.PALETTE_RGB,
        THEME_PREVIEW_CROP_BOX,
        THEME_PREVIEW_SIZE,
        THEME_PREVIEW_CACHE_VERSION,
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


def cache_path(state_dir, theme_id):
    """The on-disk cache path for `theme_id`'s preview, or `None` when
    `state_dir` is falsy OR `theme_id` is not a real key of
    `device_config.THEMES`.

    This membership guard is at the boundary itself, deliberately
    duplicating the route handler's own check rather than trusting it —
    exactly the discipline `illustrations.override_path_for_key()` carries
    (T-v26-01-01): no path component here is ever built from an id that is
    not a literal key of the registry, whether or not a caller upstream
    already validated it.
    """
    if not state_dir or theme_id not in device_config.THEMES:
        return None
    directory = cache_dir(state_dir)
    filename = "%s-%s.png" % (theme_id, preview_signature(theme_id))
    return os.path.join(directory, filename)


def cached_preview_bytes(state_dir, theme_id):
    """Return `theme_id`'s preview PNG bytes, reading the disk cache on a
    hit and rendering + writing it on a miss. Returns `None` for anything
    `cache_path()` refuses (a falsy `state_dir` or an unknown `theme_id`).

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
    path = cache_path(state_dir, theme_id)
    if path is None:
        return None
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        pass
    directory = cache_dir(state_dir)
    os.makedirs(directory, exist_ok=True)
    payload = preview_png_bytes(theme_id)
    tmp_path = os.path.join(
        directory, ".%s.%d.tmp" % (theme_id, os.getpid()))
    with open(tmp_path, "wb") as fh:
        fh.write(payload)
    os.replace(tmp_path, path)
    return payload
