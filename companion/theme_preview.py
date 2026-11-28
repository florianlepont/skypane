#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
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
import math
import os
import re

from PIL import Image

import companion.device_scope as device_scope
import companion.i18n as i18n
from server import atomic_io, device_config, hardware, panel_format, screen_layouts
from server.plane import illustrations, render

THEME_PREVIEW_ROUTE_PREFIX = "/theme-preview/"
THEME_PREVIEW_ALT_TEMPLATE = i18n.msg(
    "display.sample_panel_rendered_in_the_theme",
    "Sample panel rendered in the %s theme")

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

# The landscape frame's chip crop, in its 800x480 canvas: 300px tall, the
# same 8:3 shape as THEME_PREVIEW_SIZE so the chip is never distorted. The
# rendered card keeps its status line and runway tag in the top 90px and
# is empty below y=390; this box keeps the aircraft illustration and the
# flight text (callsign, destination, airline) and drops the header
# strip, which a 160x60 chip cannot show legibly. The look of this crop is
# for the owner to confirm in the companion walk-through.
THEME_PREVIEW_CROP_BOX_LANDSCAPE = (0, 90, 800, 390)

# 2x the chip's ~160x60 display size, so it stays crisp on Retina-class
# displays. Downscaled (1200 -> 320, LANCZOS); never grow past the
# source crop's resolution — an upscaled thumbnail looks worse.
THEME_PREVIEW_SIZE = (320, 120)

THEME_PREVIEW_CACHE_DIRNAME = "theme_previews"
# Manual escape hatch for a render-geometry change inside render.py
# that preview_signature() cannot see on its own.
THEME_PREVIEW_CACHE_VERSION = 2

# Bound on the cache directory's total file count, oldest evicted first -
# every theme's sample for every layout plus a couple of concurrently-live_event
# previews each stays under this, and it grows with the registry; a much larger
# number would only ever accumulate from a runway with many distinct live
# events, not from normal Settings-page browsing.
THEME_PREVIEW_CACHE_MAX_FILES = 3 * len(device_config.THEMES) * len(screen_layouts.LAYOUT_IDS)

# Cache keys and file names carry a layout segment; `None` (the caller
# did not choose one) is the classic picture.
DEFAULT_PREVIEW_LAYOUT = screen_layouts.CLASSIC_LAYOUT_ID


def _is_legacy_profile(profile):
    """True for `None` and the legacy portrait profile."""
    return profile is None or profile.key == hardware.LEGACY_KEY


def _is_portrait_canvas(profile):
    """True when `profile`'s canvas is the portrait 1200x1600 one (a
    simulated clone of the legacy frame has it too): such a frame keeps the
    portrait crop box, reduction factors and picture sizes."""
    return profile is None or (profile.width, profile.height) == FRAME_PREVIEW_CANVAS_SIZE


def _canvas_profile(profile):
    """The `profile` argument for `render.build_canvas()`: `None` (its
    unchanged legacy path) for the legacy profile, else the profile."""
    return None if _is_legacy_profile(profile) else profile


def _profile_segment(profile):
    """The text a non-legacy profile adds to cache keys and file names,
    or `None` for the legacy profile (whose names never changed) and for
    anything that is not a registry profile. Only a registry key, which
    is `[a-z0-9-]`, can reach a path."""
    if _is_legacy_profile(profile):
        return None
    if hardware.REGISTRY.get(profile.key) is not profile:
        return False
    window = profile.visible_window
    if window is None:
        return profile.key
    # A window changes the picture, so it is part of the name: previews drawn
    # before it was set, or before they were cut to it, are not reused.
    return "%s-v%d-%d-%d-%d" % (profile.key, window.x, window.y, window.width, window.height)


def _visible_box(profile):
    """The (left, top, right, bottom) of the part of `profile`'s canvas that
    its mat leaves visible, or `None` when it has no window. Previews show
    only this part: the strips the mat hides repeat the screen's edge and
    would look like artefacts."""
    window = None if _is_legacy_profile(profile) else profile.visible_window
    if window is None:
        return None
    return (window.x, window.y, window.x + window.width, window.y + window.height)


def visible_part_png(payload, profile):
    """`payload` (PNG bytes of a full panel image) cut to the part of the
    panel `profile`'s mat leaves visible. Returned unchanged for a profile
    without a window, for an image that is not the panel's size (an older
    archive from another hardware type) and for bytes that are not an image."""
    box = _visible_box(profile)
    if box is None:
        return payload
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.size != (profile.width, profile.height):
                return payload
            buffer = io.BytesIO()
            image.convert("RGB").crop(box).save(buffer, format="PNG")
            return buffer.getvalue()
    except Exception:
        return payload


def chip_crop_box(profile=None):
    """The theme chip's crop box inside `profile`'s canvas. With a window it
    is as wide as the window and keeps the chip's shape, centred on the same
    row as the unwindowed box."""
    if _is_portrait_canvas(profile):
        return THEME_PREVIEW_CROP_BOX
    box = THEME_PREVIEW_CROP_BOX_LANDSCAPE
    visible = _visible_box(profile)
    if visible is None:
        return box
    chip_w, chip_h = THEME_PREVIEW_SIZE
    step = chip_w // math.gcd(chip_w, chip_h)
    width = (visible[2] - visible[0]) // step * step
    height = width // step * (chip_h // math.gcd(chip_w, chip_h))
    left = visible[0] + (visible[2] - visible[0] - width) // 2
    top = (box[1] + box[3]) // 2 - height // 2
    top = max(visible[1], min(top, visible[3] - height))
    return (left, top, left + width, top + height)


def layout_key(layout):
    """The allow-listed layout id for `layout`: `None` is classic, a known
    id is itself, anything else is `None` (the caller refuses it). The
    result is the only layout text that may reach a cache path.
    """
    if layout is None:
        return DEFAULT_PREVIEW_LAYOUT
    if isinstance(layout, str) and layout in screen_layouts.LAYOUT_IDS:
        return layout
    return None

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


def preview_png_bytes(theme_id, live_event=None, layout=None, profile=None, state_dir=None):
    """Render the fixed scene, or `live_event` (a `runway_events` row)
    when given, through `render.build_canvas()`, crop, downscale, and
    return PNG bytes. A live render omits the previous-flight card.
    `layout` is a screen layout id (`None` is classic). `profile` is the
    frame's hardware profile (`None` is the legacy portrait frame).
    `state_dir` is the frame's state directory: an illustration override
    uploaded for the fleet is drawn in place of the vendored picture.

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
            layout=layout_key(layout),
            profile=_canvas_profile(profile),
            state_dir=state_dir,
        )
    else:
        flight, route, state = _live_flight_route_state(live_event)
        canvas = render.build_canvas(
            flight, state, route=route, theme_id=theme_id,
            layout=layout_key(layout), profile=_canvas_profile(profile),
            state_dir=state_dir,
        )
    rgb = canvas.convert("RGB")
    cropped = rgb.crop(chip_crop_box(profile))
    resized = cropped.resize(THEME_PREVIEW_SIZE, Image.LANCZOS)
    buffer = io.BytesIO()
    resized.save(buffer, format="PNG")
    return buffer.getvalue()


def artwork_stamp(state_dir, scenes):
    """What the pictures a preview draws are made of: for each `(route,
    flight)` scene, the file `illustrations.select_illustration()` resolves
    (an uploaded override first, else the vendored one) with its size and,
    for an override, its modification time. Replacing, adding or removing an illustration changes
    the stamp, so a cached preview of the old artwork is never served for the
    new one. Never raises; a scene with no readable file stamps as `None`."""
    stamp = []
    for route, flight in scenes:
        try:
            path = illustrations.select_illustration(
                route, (flight or {}).get("aircraft_type"), state_dir=state_dir)
            info = os.stat(path) if path else None
        except (OSError, TypeError, ValueError):
            info = path = None
        if info is None:
            stamp.append(None)
        elif os.path.dirname(path) == illustrations.override_dir_for_state_dir(state_dir):
            stamp.append((os.path.basename(path), info.st_size, info.st_mtime_ns))
        else:
            # A vendored picture changes with a deploy, whose checkout times
            # say nothing about the picture: name and size stand for it.
            stamp.append((os.path.basename(path), info.st_size))
    return tuple(stamp)


def _fixed_scenes():
    """The two flights the fixed scene draws, whichever state it shows."""
    return (
        (THEME_PREVIEW_ROUTE, THEME_PREVIEW_FLIGHT),
        (THEME_PREVIEW_PREVIOUS_ROUTE, THEME_PREVIEW_PREVIOUS_FLIGHT))


def _chip_scenes(live_event):
    if not isinstance(live_event, dict):
        return _fixed_scenes()
    flight, route, _state = _live_flight_route_state(live_event)
    return ((route, flight),)


def preview_signature(theme_id, live_event_id=None, layout=None, profile=None, artwork=None):
    """A 12-hex-character cache-key discriminator for `theme_id`.
    Folds in the theme's palette (so a real-glass ink re-tune is a
    cache miss, not a stale image forever), the crop/size constants,
    `THEME_PREVIEW_CACHE_VERSION` (the manual escape hatch for a
    render-geometry change this signature can't otherwise see), and
    `live_event_id` (opaque digest input, never a path component) and
    the layout, so one theme's pictures for two layouts never collide. A
    non-legacy `profile` adds its key (and its own crop box); the legacy
    profile leaves the digest as it always was. `artwork` is an
    `artwork_stamp()`: a different stamp is a different picture.
    """
    parts = (
        device_config.THEMES[theme_id],
        panel_format.PALETTE_RGB,
        THEME_PREVIEW_CROP_BOX,
        THEME_PREVIEW_SIZE,
        THEME_PREVIEW_CACHE_VERSION,
        live_event_id,
        layout_key(layout),
    )
    segment = _profile_segment(profile)
    if segment:
        parts += (segment, chip_crop_box(profile))
    if artwork:
        parts += (artwork,)
    digest_input = repr(parts).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()[:12]


def cache_dir(state_dir):
    """`{state_dir}/THEME_PREVIEW_CACHE_DIRNAME`, or `None` for a falsy
    `state_dir`. Never creates the directory — read-only computation,
    matching `illustrations.override_dir_for_state_dir()`'s own contract.
    """
    if not state_dir:
        return None
    return os.path.join(state_dir, THEME_PREVIEW_CACHE_DIRNAME)


def cache_path(state_dir, theme_id, live_event_id=None, layout=None, profile=None, live_event=None):
    """The on-disk cache path for `theme_id`'s preview, or `None` when
    `state_dir` is falsy or `theme_id` is not a real THEMES key —
    validated at the boundary itself, never trusting an upstream check.
    A `layout` outside the allow-list is refused the same way, and so is a
    `profile` that is not a registry profile. A non-legacy profile adds its
    key to the file name; the legacy name is unchanged.

    `live_event_id` is coerced to `int()`; any failure degrades to the
    fixed literal `"sample"`, so no string field from a `runway_events`
    row can ever reach a path component. `live_event` is the row itself,
    read only for the illustration it draws (the cache key's artwork stamp).
    """
    layout_id = layout_key(layout)
    segment = _profile_segment(profile)
    if (not state_dir or theme_id not in device_config.THEMES or layout_id is None
            or segment is False):
        return None
    try:
        event_id = int(live_event_id)
    except (TypeError, ValueError):
        event_id = None
    signature = preview_signature(
        theme_id, event_id, layout_id, profile,
        artwork=artwork_stamp(state_dir, _chip_scenes(live_event)))
    directory = cache_dir(state_dir)
    filename = "%s-%s-%s-%s%s.png" % (
        theme_id, event_id if event_id is not None else "sample", layout_id,
        "%s-" % segment if segment else "", signature)
    return os.path.join(directory, filename)


def _prune_preview_cache(directory, keep_path, max_files=THEME_PREVIEW_CACHE_MAX_FILES):
    """Best-effort cache maintenance after a fresh write to `keep_path`:
    never raises (an `OSError` anywhere below is swallowed - a maintenance
    step must never fail the request the write it follows is serving).

    1. Stale-signature removal: any other file sharing `keep_path`'s exact
       `<theme>-<event or 'sample'>` prefix but a different 12-hex
       signature is removed (a theme re-tune or a render-geometry bump
       leaves the old image behind otherwise, forever).
    2. Bound: if more than `max_files` `*.png` files
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

        overflow = len(entries) - max_files
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


# --- Full-frame previews ---------------------------------------------
#
# The Display page's large pictures and the Special looks list's mini
# renders show the whole 1200x1600 canvas, not the chip grid's band crop.
# They always render the fixed fictional scene, so the same theme looks
# the same everywhere on the page: a departing main flight with an
# arriving previous card, or the mirror image for the arrivals picture.
# The overhead picture is the departing scene's flight drawn as a level
# aircraft over the frame.
FRAME_PREVIEW_ROUTE_PREFIX = "/frame-preview/"
FRAME_PREVIEW_STATE_DEPARTING = "departing"
FRAME_PREVIEW_STATE_ARRIVING = "arriving"
FRAME_PREVIEW_STATE_OVERHEAD = "overhead"
FRAME_PREVIEW_STATES = (
    FRAME_PREVIEW_STATE_DEPARTING, FRAME_PREVIEW_STATE_ARRIVING, FRAME_PREVIEW_STATE_OVERHEAD)
FRAME_PREVIEW_SIZE_LARGE = "large"
FRAME_PREVIEW_SIZE_SMALL = "small"
# Integer box-reduction factors of the 1200x1600 canvas. A box filter
# averages the panel's dither into the tint the eye sees from a step
# away; LANCZOS would ring on the dither instead and triple the PNG size.
FRAME_PREVIEW_REDUCE_FACTORS = {
    FRAME_PREVIEW_SIZE_LARGE: 2,
    FRAME_PREVIEW_SIZE_SMALL: 10,
}
FRAME_PREVIEW_SIZES = tuple(FRAME_PREVIEW_REDUCE_FACTORS)
FRAME_PREVIEW_CANVAS_SIZE = (1200, 1600)
FRAME_PREVIEW_PIXEL_SIZES = {
    size: (FRAME_PREVIEW_CANVAS_SIZE[0] // factor, FRAME_PREVIEW_CANVAS_SIZE[1] // factor)
    for size, factor in FRAME_PREVIEW_REDUCE_FACTORS.items()
}
# The landscape frame's own reduction factors: 800x480 reduces to 400x240
# (large) and 160x96 (small); a factor of 10 would leave a 80x48 thumbnail.
FRAME_PREVIEW_REDUCE_FACTORS_LANDSCAPE = {
    FRAME_PREVIEW_SIZE_LARGE: 2,
    FRAME_PREVIEW_SIZE_SMALL: 5,
}
FRAME_PREVIEW_CACHE_DIRNAME = "frame_previews"
# Every reachable file is one of themes x 3 states x 2 sizes x layouts x
# hardware profiles; the bound follows the registries, so adding a theme or
# a profile never evicts live previews.
FRAME_PREVIEW_CACHE_MAX_FILES = (
    len(device_config.THEMES) * len(FRAME_PREVIEW_STATES) * len(FRAME_PREVIEW_SIZES)
    * len(screen_layouts.LAYOUT_IDS) * len(hardware.REGISTRY))
FRAME_PREVIEW_CACHE_VERSION = 2


def frame_preview_reduce_factor(profile, size):
    """The box-reduction factor of `size` for `profile`'s canvas."""
    if _is_portrait_canvas(profile):
        return FRAME_PREVIEW_REDUCE_FACTORS[size]
    return FRAME_PREVIEW_REDUCE_FACTORS_LANDSCAPE[size]


def frame_preview_pixel_size(profile, size):
    """The (width, height) of the `size` frame preview for `profile`
    (`None` is the legacy portrait frame): the profile's canvas divided by
    its reduction factor. For a portrait-canvas profile this is exactly
    `FRAME_PREVIEW_PIXEL_SIZES[size]`."""
    if _is_portrait_canvas(profile):
        return FRAME_PREVIEW_PIXEL_SIZES[size]
    factor = frame_preview_reduce_factor(profile, size)
    visible = _visible_box(profile)
    if visible is not None:
        # Image.reduce() rounds up.
        return (-(-(visible[2] - visible[0]) // factor), -(-(visible[3] - visible[1]) // factor))
    return (profile.width // factor, profile.height // factor)


def frame_preview_png_bytes(theme_id, state, size, layout=None, profile=None, state_dir=None):
    """The whole canvas for `theme_id` with the fixed scene's main flight
    in `state`, box-reduced to `size`, as PNG bytes. The arriving
    variant swaps the two fixture flights, so each picture shows a
    flight that really arrives at (or leaves) Orly. `layout` is a screen
    layout id (`None` is classic). `profile` is the frame's hardware
    profile (`None` is the legacy portrait frame). `state_dir` is the
    frame's state directory: an uploaded illustration override is drawn in
    place of the vendored picture.
    """
    if state == FRAME_PREVIEW_STATE_ARRIVING:
        main_flight, main_route = THEME_PREVIEW_PREVIOUS_FLIGHT, THEME_PREVIEW_PREVIOUS_ROUTE
        previous_flight, previous_route = THEME_PREVIEW_FLIGHT, THEME_PREVIEW_ROUTE
        previous_state = FRAME_PREVIEW_STATE_DEPARTING
    else:
        main_flight, main_route = THEME_PREVIEW_FLIGHT, THEME_PREVIEW_ROUTE
        previous_flight, previous_route = THEME_PREVIEW_PREVIOUS_FLIGHT, THEME_PREVIEW_PREVIOUS_ROUTE
        previous_state = FRAME_PREVIEW_STATE_ARRIVING
    canvas = render.build_canvas(
        main_flight, state, route=main_route,
        previous_flight=previous_flight, previous_route=previous_route,
        previous_state=previous_state, theme_id=theme_id,
        layout=layout_key(layout), profile=_canvas_profile(profile),
        state_dir=state_dir,
    )
    # RGB before reducing, for the same reason preview_png_bytes() gives.
    rgb = canvas.convert("RGB")
    visible = _visible_box(profile)
    if visible is not None:
        rgb = rgb.crop(visible)
    reduced = rgb.reduce(frame_preview_reduce_factor(profile, size))
    buffer = io.BytesIO()
    reduced.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def frame_preview_signature(theme_id, state, size, layout=None, profile=None, artwork=None):
    """Like `preview_signature()`, for one full-frame variant."""
    parts = (
        device_config.THEMES[theme_id],
        panel_format.PALETTE_RGB,
        state,
        frame_preview_reduce_factor(None, size),
        FRAME_PREVIEW_CACHE_VERSION,
        layout_key(layout),
    )
    segment = _profile_segment(profile)
    if segment:
        parts += (segment, frame_preview_reduce_factor(profile, size))
    if artwork:
        parts += (artwork,)
    digest_input = repr(parts).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()[:12]


def frame_cache_path(state_dir, theme_id, state, size, layout=None, profile=None):
    """The on-disk cache path for one full-frame variant, or `None` when
    any of the four values is outside its allow-list, `profile` is not a
    registry profile, or `state_dir` is falsy. Every path component comes
    from an allow-list member, never from request text. A non-legacy
    profile adds its key to the file name; the legacy name is unchanged.
    """
    layout_id = layout_key(layout)
    segment = _profile_segment(profile)
    if (not state_dir or theme_id not in device_config.THEMES
            or state not in FRAME_PREVIEW_STATES or size not in FRAME_PREVIEW_SIZES
            or layout_id is None or segment is False):
        return None
    filename = "%s-%s-%s-%s-%s%s.png" % (
        theme_id, state, size, layout_id,
        "%s-" % segment if segment else "",
        frame_preview_signature(
            theme_id, state, size, layout_id, profile,
            artwork_stamp(state_dir, _fixed_scenes())))
    return os.path.join(state_dir, FRAME_PREVIEW_CACHE_DIRNAME, filename)


def cached_frame_preview_bytes(state_dir, theme_id, state, size, layout=None, profile=None):
    """`cached_preview_bytes()`'s contract for one full-frame variant:
    disk hit, or render, atomic write and prune on a miss. `None` for
    anything `frame_cache_path()` refuses.
    """
    path = frame_cache_path(state_dir, theme_id, state, size, layout, profile)
    if path is None:
        return None
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        pass
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    if _is_legacy_profile(profile):
        payload = frame_preview_png_bytes(theme_id, state, size, layout, state_dir=state_dir)
    else:
        payload = frame_preview_png_bytes(
            theme_id, state, size, layout, profile, state_dir=state_dir)
    atomic_io.atomic_write(path, payload)
    _prune_preview_cache(directory, path, max_files=FRAME_PREVIEW_CACHE_MAX_FILES)
    return payload


def current_frame_preview_pixel_size(size):
    """`frame_preview_pixel_size()` for the frame this request is about:
    its profile from the request scope. No frame in scope, or a frame
    whose type is unknown or switched off, reads as the legacy portrait
    frame."""
    return frame_preview_pixel_size(
        device_scope.profile_for(device_scope.current_device()), size)


def frame_preview_src(theme_id, state=FRAME_PREVIEW_STATE_DEPARTING, size=FRAME_PREVIEW_SIZE_LARGE, layout=None):
    """The page-side URL for one full-frame variant. Callers pass
    registry ids only; the route re-validates every part anyway. A
    `layout` adds the `layout` query parameter; `None` leaves the URL as
    it always was.
    """
    url = "%s%s.png?state=%s&size=%s" % (FRAME_PREVIEW_ROUTE_PREFIX, theme_id, state, size)
    if layout is not None:
        url += "&layout=%s" % layout
    version = frame_preview_version(theme_id, state, size, layout)
    if version:
        url += "&v=%s" % version
    return device_scope.scoped(url)


def frame_preview_version(theme_id, state, size, layout=None, profile=None, state_dir=None):
    """The content address of one full-frame variant: the signature of every input
    that changes its pixels, for the current frame's profile unless `profile` is
    given, and the artwork of `state_dir` (the current frame's unless given). `None` for a placeholder or unknown value, which gets no address. The
    route answers a URL whose `v` matches with a cache entry that never expires,
    so an unchanged preview is not fetched again when the owner moves between tabs.
    """
    if (theme_id not in device_config.THEMES or state not in FRAME_PREVIEW_STATES
            or size not in FRAME_PREVIEW_SIZES or layout_key(layout) is None):
        return None
    device = device_scope.current_device()
    if profile is None:
        profile = device_scope.profile_for(device)
    if _profile_segment(profile) is False:
        return None
    if state_dir is None and device is not None:
        state_dir = device.state_dir
    return frame_preview_signature(
        theme_id, state, size, layout, profile,
        artwork_stamp(state_dir, _fixed_scenes()) if state_dir else None)


def cached_preview_bytes(state_dir, theme_id, live_event=None, layout=None, profile=None):
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
    path = cache_path(state_dir, theme_id, live_event_id, layout, profile, live_event)
    if path is None:
        return None
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        pass
    directory = cache_dir(state_dir)
    os.makedirs(directory, exist_ok=True)
    if _is_legacy_profile(profile):
        payload = preview_png_bytes(theme_id, live_event, layout, state_dir=state_dir)
    else:
        payload = preview_png_bytes(theme_id, live_event, layout, profile, state_dir=state_dir)
    atomic_io.atomic_write(path, payload)
    _prune_preview_cache(directory, path)
    return payload
