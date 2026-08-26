#!/usr/bin/env python3
"""Minimal-but-real panel renderer for the plane view (PLANE-01/02/03).

Implements the state field, state label, flight-number caption, and bottom
static tag - 02-03 adds the silhouette centrepiece, 02-04 adds the route
and airline lines. Every draw call goes directly onto a "P"-mode canvas
(built via panel_format's flat-fill canvas constructor, or - since 03-02 -
the dithered mood-background builder below) with an integer palette-index
fill, never an RGB tuple and never an RGB compose-then-quantize step
(02-RESEARCH.md Architecture Pattern 1) - this is the mechanism that
satisfies 02-UI-SPEC.md's binding "disable anti-aliasing" rule for free.

02-02 (this slice) adds the full-bleed departing/arriving colour field
(STATE_BACKGROUND) and the DEPARTING/ARRIVING state label (glyph + tracked
text, STATE_INK) driven by real server.plane.runway_config inference -
replacing 02-01's placeholder colour-only rendering. The vendored Lucide
plane-takeoff/plane-landing glyphs are pre-rasterized PNG alpha masks
(server/assets/icons/, see VENDOR.md) - no SVG parser is a runtime
dependency (02-RESEARCH.md's "Don't Hand-Roll" table). Every resized mask
is hard-thresholded back to strictly binary before compositing
(load_binary_mask(), 02-RESEARCH.md Architecture Pattern 2) - this is what
keeps the exactly-two-palette-indices anti-aliasing guarantee intact even
though the glyph asset itself was resized.

03-02 (D-17, D-18) replaces the active states' flat STATE_BACKGROUND fill
with server.plane.dither.build_mood_background() - a deterministic,
Floyd-Steinberg-dithered, two-tone gradient in the state's own hue. Every
text-bearing zone (state label, flight-number caption, route/airline
lines, bottom tag) now draws a flat "quiet-zone" rectangle of the state's
background index (draw_quiet_zone()) *before* its own text, so no glyph
ever sits directly on a dithered pixel - the whole-canvas "exactly two
palette indices" guard rail is replaced by the spatially-scoped
_assert_palette_contract() for the same reason. Pillow's built-in
text-outline drawing arguments (see 03-RESEARCH.md Pitfall 7 for their
exact names) must never be used anywhere in this file, for any font, in
any state - they leak illegal palette indices through anti-aliased
stroke-edge blending even on a flat background.

Usage (manual QA):
    server/.venv/bin/python3 server/plane/render.py --state empty --out /tmp/panel.bin
    server/.venv/bin/python3 server/plane/render.py --state arriving --callsign AF1380 \
        --out /tmp/panel.bin --preview /tmp/panel.preview.png
"""
import argparse
import hashlib
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# Allow both `import server.plane.render` (package import, REPO_ROOT already
# on sys.path per the caller) and direct script execution
# (`python3 server/plane/render.py`, where sys.path[0] is server/plane/ and
# the repo root must be added by hand before the `server.panel_format`
# absolute import below can resolve).
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/plane
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import panel_format as pf
from server.panel_format import IDX_BLACK, IDX_BLUE, IDX_GREEN, IDX_RED, IDX_WHITE, IDX_YELLOW, WIDTH, HEIGHT
from server.plane import dither, enrich, runway_config

# --- UI-SPEC Spacing Scale (02-UI-SPEC.md, unchanged since Revision 1) ----
SPACE_XS = 8
SPACE_SM = 16
SPACE_MD = 32
SPACE_LG = 64
SPACE_XL = 96
SPACE_2XL = 128
SPACE_3XL = 192

# MARGIN is inviolable on all four edges regardless of content length -
# nothing may render under the physical bezel (02-UI-SPEC.md Spacing Scale
# "Exceptions").
MARGIN = SPACE_LG
SAFE_BOX = (MARGIN, MARGIN, WIDTH - MARGIN, HEIGHT - MARGIN)  # (64, 64, 1136, 1536)

# 03-UI-SPEC.md "Quiet-zone text compositing": every text-bearing element in
# the Departing/Arriving states sits on a flat plate of the state's
# background index, sized to the text's own bounding box plus this much
# padding on every side. Reuses the existing SPACE_XS token - no new
# spacing token is introduced (03-02-PLAN.md's locked-decisions note).
QUIET_ZONE_PAD = SPACE_XS

# --- UI-SPEC Typography (03-UI-SPEC.md Revision 3, supersedes 02-UI-SPEC.md's
# three-role Inter sans-serif scale) -----------------------------------------
FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")
)
_ZILLA_SEMIBOLD = os.path.join(FONT_DIR, "ZillaSlab-SemiBold.ttf")
_ZILLA_BOLD = os.path.join(FONT_DIR, "ZillaSlab-Bold.ttf")

# D-15/D-16 (locked, 03-CONTEXT.md): this block is a declared UI-SPEC
# contract, not free parameters - exactly four roles, exactly two weights.
# Only the SemiBold (600) and Bold (700) Zilla Slab cuts may ever be
# referenced here (Regular/Light cuts reintroduce the e-ink hairline risk
# a slab serif was chosen to structurally avoid). (font_path, size, weight)
# per role - weight is documentation only (the path already selects the
# correct static weight file).
LABEL_FONT = (_ZILLA_BOLD, 36, 700)
CAPTION_FONT = (_ZILLA_SEMIBOLD, 40, 600)
DESTINATION_FONT = (_ZILLA_SEMIBOLD, 64, 600)
FLIGHT_NUMBER_FONT = (_ZILLA_BOLD, 72, 700)

# Label role is uppercase with widened letter-spacing (Pillow has no native
# tracking API - UI-SPEC's Typography note calls for manual per-glyph
# advance widening, see draw_tracked_text()). D-15 widens this from Phase
# 2's 4px to 6px ("wide letter-spacing" instruction, resolved by
# 03-UI-SPEC.md's Typography table).
LABEL_TRACKING_PX = 6

# --- 02-UI-SPEC.md Colour section, Revision 2 (state-scoped, not one fixed
# global table) -------------------------------------------------------------
# Keyed by runway_config's STATE_* constants (not bare string literals) so
# the two modules cannot drift apart - reading this one dict is what makes
# the Colour section's reservation contract ("Blue/Green is the background
# field only; White is foreground content only") enforceable.
STATE_BACKGROUND = {
    runway_config.STATE_DEPARTING: IDX_BLUE,
    runway_config.STATE_ARRIVING: IDX_GREEN,
}
STATE_INK = {
    runway_config.STATE_DEPARTING: IDX_WHITE,
    runway_config.STATE_ARRIVING: IDX_WHITE,
}
STATE_LABEL_TEXT = {
    runway_config.STATE_DEPARTING: "DEPARTING",
    runway_config.STATE_ARRIVING: "ARRIVING",
}

# Vendored Lucide glyphs (server/assets/icons/, see VENDOR.md) - pre-
# rasterized PNG alpha masks, never an SVG parsed at runtime.
ICON_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "icons")
)
STATE_GLYPH_PATH = {
    runway_config.STATE_DEPARTING: os.path.join(ICON_DIR, "plane-takeoff.png"),
    runway_config.STATE_ARRIVING: os.path.join(ICON_DIR, "plane-landing.png"),
}

# Vendored CC0 aircraft silhouette centrepiece (02-03, see VENDOR.md's
# aircraft-silhouette entry for full provenance and the cleanup pipeline
# that turned the source line-art into a flat solid mask). Pre-rasterized
# PNG alpha mask, never an SVG parsed at runtime, same convention as
# STATE_GLYPH_PATH above.
SILHOUETTE_PATH = os.path.join(ICON_DIR, "aircraft-silhouette.png")

# The vendored master's cockpit/nose renders on the LEFT of the asset
# (recorded in VENDOR.md's "Source nose orientation" note) - this is read
# here, not guessed, so draw_silhouette() below can compute whether to
# mirror per state instead of hardcoding a flip that would silently go
# wrong if the asset were ever re-rasterized mirrored.
SILHOUETTE_SOURCE_NOSE = "left"

EMPTY_HEADING_TEXT = "Watching Runway 3"
EMPTY_BODY_TEXT = "No aircraft detected yet — the display updates the moment one is."
BOTTOM_TAG_TEXT = "ORY · RWY 3"

# Reserved vertical footprint for zone 3 (silhouette, filled by 02-03) so
# the flight-number caption (zone 5) lands where 02-UI-SPEC.md's Layout &
# Composition puts it and 02-03/02-04 can slot their content in above it
# without ever moving what this plan already renders. Zone 1 (state label)
# is now drawn by this plan (draw_state_label()) within this same reserved
# footprint.
ZONE1_STATE_LABEL_HEIGHT = 96  # "roughly the same vertical footprint... ~96px" (UI-SPEC zone 1)

# UI-SPEC zone 3 geometry, named per 02-03-PLAN.md Task 2 so
# test_render.py's assertions reference the exact numbers the renderer
# uses instead of re-deriving them. UI-SPEC's own "~900px wide / ~220-
# 260px tall" is a fit-within box, not a fixed size - draw_silhouette()
# below preserves the source aspect ratio and lets whichever of the two
# caps (width or height) binds first determine the actual rendered size.
# The vendored asset's ~2.22:1 aspect ratio means the 260px height cap
# binds well before the 900px width cap is reached (see VENDOR.md).
SILHOUETTE_TARGET_W = 900  # UI-SPEC zone 3: "max ~900px wide"
SILHOUETTE_MAX_H = 260  # UI-SPEC zone 3: "~220-260px tall"
SILHOUETTE_ZONE_TOP = MARGIN + ZONE1_STATE_LABEL_HEIGHT + SPACE_2XL  # = 288
SILHOUETTE_ZONE_HEIGHT = SPACE_3XL + SILHOUETTE_MAX_H + SPACE_3XL  # 3xl padding both sides = 644

FLIGHT_NUMBER_TOP_Y = (
    SILHOUETTE_ZONE_TOP
    + SILHOUETTE_ZONE_HEIGHT
    + SPACE_XL
)  # = 1028

# --- 02-04: Route line (zone 7) / Airline line (zone 9) ---------------------
# 02-UI-SPEC.md zones 5-9: flight number -> sm gap -> route line -> md gap ->
# airline line. On an enrichment miss, zone 7 (route line) and zone 8 (its
# preceding md gap) are both omitted, and the airline line's fallback copy
# sits at *exactly* the same absolute position the airline line normally
# occupies - not "one gap lower" and with no blank line reserved above it
# (02-UI-SPEC.md Copywriting Contract, N-02-04-01). This is guaranteed by
# computing the airline line's top Y from *fixed font-metric constants*
# (never from an actually-rendered, possibly-blank route line's measured
# bbox) - the vertical cursor for zone 9 is a pure function of font sizes,
# not of whether zone 7 drew anything this render.
ROUTE_PREFIX_DEPARTING = "TO"
ROUTE_PREFIX_ARRIVING = "FROM"
ROUTE_PREFIX_TEXT = {
    runway_config.STATE_DEPARTING: ROUTE_PREFIX_DEPARTING,
    runway_config.STATE_ARRIVING: ROUTE_PREFIX_ARRIVING,
}
ROUTE_FALLBACK_TEXT = "Route unavailable"

# Overflow floor (02-UI-SPEC.md's inviolable 64px margin): city/airline runs
# shrink in small steps rather than clipping, wrapping mid-word, or
# overflowing under the bezel - but never below this point size, so the
# behaviour has an inspectable, named limit.
MIN_CAPTION_FONT_SIZE = 28
_FIT_STEP_PX = 2

# Small fixed gap between the route line's tracked Label-role prefix
# ("TO"/"FROM") and its Body-role city run - not itself a named UI-SPEC
# token, so pinned to the smallest spacing-scale value (SPACE_XS).
ROUTE_PREFIX_GAP_PX = SPACE_XS

_font_cache = {}


def _font(spec):
    path, size, _weight = spec
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def fit_text_size(font_path, initial_size, text, max_width, min_size=MIN_CAPTION_FONT_SIZE, tracking=0):
    """Return the largest ImageFont at `font_path`, stepping down from
    `initial_size` in `_FIT_STEP_PX`-point decrements, whose rendered width
    for `text` (including `tracking` extra px/glyph, if any) fits within
    `max_width` - floored at `min_size` (MIN_CAPTION_FONT_SIZE). Never
    clips, wraps mid-word, or overflows the safe box; the caller still
    asserts the final bbox with `_assert_in_safe_box` as a guard rail.
    """
    size = initial_size
    while size > min_size:
        font = _font((font_path, size, None))
        width = _tracked_text_width(font, text, tracking) if tracking else font.getlength(text)
        if width <= max_width:
            return font
        size -= _FIT_STEP_PX
    return _font((font_path, min_size, None))


def _assert_in_safe_box(bbox, label):
    left, top, right, bottom = bbox
    sb_left, sb_top, sb_right, sb_bottom = SAFE_BOX
    assert left >= sb_left and top >= sb_top and right <= sb_right and bottom <= sb_bottom, (
        "%s bounding box %r exceeds the inviolable %dpx safe box %r"
        % (label, bbox, MARGIN, SAFE_BOX)
    )


def draw_quiet_zone(canvas, bbox, bg_idx, pad=QUIET_ZONE_PAD):
    """Draw a flat `bg_idx`-coloured rectangle behind a text-bearing zone so
    no glyph is ever drawn directly on a dithered pixel (03-UI-SPEC.md
    "Quiet-zone text compositing"). Expands `bbox` by `pad` on all four
    sides, clamps the result to SAFE_BOX (the bottom static tag's own
    bounding box already ends exactly on the safe-box bottom edge, so an
    unclamped pad would breach the inviolable margin - clamping is
    required here, not defensive), asserts the clamped rectangle still
    fully contains the unexpanded `bbox`, and draws it with hard corners
    (no rounding). Returns the clamped rectangle so the caller can hand it
    to _assert_palette_contract().
    """
    left, top, right, bottom = bbox
    sb_left, sb_top, sb_right, sb_bottom = SAFE_BOX
    clamped = (
        max(sb_left, left - pad),
        max(sb_top, top - pad),
        min(sb_right, right + pad),
        min(sb_bottom, bottom + pad),
    )
    c_left, c_top, c_right, c_bottom = clamped
    assert c_left <= left and c_top <= top and c_right >= right and c_bottom >= bottom, (
        "quiet zone %r clamped to %r no longer fully contains its own text bbox %r"
        % ((left - pad, top - pad, right + pad, bottom + pad), clamped, bbox)
    )
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(clamped, fill=bg_idx)
    return clamped


def _wrap_text(font, text, max_width):
    """Manual word-wrap: split on spaces, greedily pack words onto a line
    while the line's rendered width (font.getlength) stays within
    max_width. UI-SPEC has no automatic reflow API to rely on (Pillow's
    ImageDraw.multiline_text does not word-wrap), so the empty-state body
    copy is wrapped by hand to fit the 1072px safe-box width.
    """
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if not current or font.getlength(candidate) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _tracked_text_width(font, text, tracking):
    if not text:
        return 0.0
    return sum(font.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def draw_tracked_text(draw, xy, text, font, fill, tracking=0):
    """Draw `text` glyph-by-glyph with `tracking` extra pixels of advance
    between each glyph - Pillow has no native letter-spacing/tracking API,
    per 02-UI-SPEC.md's Typography note. `xy` is the top-left origin of the
    first glyph; callers wanting centred tracked text should pre-compute
    the block width with _tracked_text_width() and offset xy accordingly.
    Returns the x-coordinate immediately after the last glyph drawn.
    """
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + tracking
    return x


def _tracked_text_bbox(font, xy, text, tracking):
    x, y = xy
    width = _tracked_text_width(font, text, tracking)
    ascent, descent = font.getmetrics()
    return (x, y, x + width, y + ascent + descent)


def load_binary_mask(path, size):
    """Load a vendored PNG glyph asset (server/assets/icons/) as a strictly
    binary "L"-mode mask at `size` (width, height).

    02-RESEARCH.md Architecture Pattern 2 (verified this session): resizing
    a mask reintroduces anti-aliased grey edge pixels (up to 150+ distinct
    grey levels observed for a simple test shape) - these must be hard-
    thresholded back to strictly binary with .point() before paste(), or
    the resize's grey edges alpha-blend into intermediate colours and break
    the exactly-two-palette-indices rule this render pipeline depends on.
    """
    mask = Image.open(path).convert("L")
    mask = mask.resize(size, Image.LANCZOS)
    mask = mask.point(lambda p: 255 if p > 127 else 0)
    return mask


def paste_mask(canvas, mask_path, box, fill_index, mirror=False):
    """Composite a vendored PNG mask asset onto `canvas` as a flat
    `fill_index`-coloured shape - the single shared call site for
    02-RESEARCH.md Architecture Pattern 2's full ordering (load ->
    resize -> hard-threshold -> optional mirror -> paste-with-mask),
    used by both the state-label glyph and the silhouette centrepiece so
    neither call site can accidentally skip the threshold step.

    `box` is (left, top, width, height) in canvas pixel coordinates.
    Returns the composited element's absolute bounding box
    (left, top, right, bottom) for the caller's own safe-box assertion.
    """
    left, top, w, h = box
    mask = load_binary_mask(mask_path, (w, h))
    if mirror:
        mask = mask.transpose(Image.FLIP_LEFT_RIGHT)
    canvas.paste(fill_index, (int(left), int(top)), mask=mask)
    return (left, top, left + w, top + h)


def draw_state_label(canvas, state, ink_idx, bg_idx):
    """Draw UI-SPEC zone 1 - the state label row: the plane-takeoff/
    plane-landing glyph (filled `ink_idx`) + SPACE_XS gap + tracked
    uppercase Label-role text (`STATE_LABEL_TEXT[state]`), horizontally
    centred, top-anchored within the 96px zone-1 band already reserved by
    FLIGHT_NUMBER_TOP_Y's zone stacking. 03-02: a single flat quiet-zone
    rectangle (`bg_idx`) is drawn behind the *combined* glyph-plus-text
    block - both geometries are measured first, the quiet zone is drawn
    before either the glyph is pasted or the text is drawn, so neither
    ever sits directly on the dithered mood background.

    Called only for the active (departing/arriving) states - the Empty
    state renders no state label and no glyph at all (nothing detected yet,
    nothing to depict).

    Returns the drawn quiet-zone rectangle.
    """
    draw = ImageDraw.Draw(canvas)
    label_font = _font(LABEL_FONT)
    text = STATE_LABEL_TEXT[state]

    # Size the glyph to the Label role's cap height, per 02-02-PLAN.md Task 3.
    cap_bbox = label_font.getbbox("H")
    cap_height = cap_bbox[3] - cap_bbox[1]

    label_ascent, label_descent = label_font.getmetrics()
    text_height = label_ascent + label_descent
    text_width = _tracked_text_width(label_font, text, LABEL_TRACKING_PX)

    row_height = max(cap_height, text_height)
    block_width = cap_height + SPACE_XS + text_width

    center_x = WIDTH // 2
    zone1_top = MARGIN
    row_top = zone1_top + (ZONE1_STATE_LABEL_HEIGHT - row_height) // 2
    block_left = center_x - block_width / 2

    icon_x = block_left
    icon_y = row_top + (row_height - cap_height) // 2
    icon_geom_bbox = (icon_x, icon_y, icon_x + cap_height, icon_y + cap_height)

    text_x = icon_x + cap_height + SPACE_XS
    text_y = row_top + (row_height - text_height) // 2
    text_bbox = _tracked_text_bbox(label_font, (text_x, text_y), text, LABEL_TRACKING_PX)

    combined_bbox = (
        min(icon_geom_bbox[0], text_bbox[0]),
        min(icon_geom_bbox[1], text_bbox[1]),
        max(icon_geom_bbox[2], text_bbox[2]),
        max(icon_geom_bbox[3], text_bbox[3]),
    )
    quiet_rect = draw_quiet_zone(canvas, combined_bbox, bg_idx)

    icon_bbox = paste_mask(canvas, STATE_GLYPH_PATH[state], (icon_x, icon_y, cap_height, cap_height), ink_idx)
    _assert_in_safe_box(icon_bbox, "state label glyph")

    _assert_in_safe_box(text_bbox, "state label text")
    draw_tracked_text(draw, (text_x, text_y), text, label_font, ink_idx, tracking=LABEL_TRACKING_PX)

    return quiet_rect


def draw_silhouette(canvas, state, ink_idx):
    """Draw UI-SPEC zone 3 - the aircraft silhouette centrepiece: a flat
    `ink_idx`-coloured fill of the vendored CC0 aircraft silhouette,
    horizontally centred within SILHOUETTE_ZONE_TOP..+SILHOUETTE_ZONE_HEIGHT
    with at least SPACE_3XL of clear field above/below its own bounding
    box, mirrored by state so the nose points right for `departing`
    (climbing away) and left for `arriving` (descending in) - a second,
    non-colour-dependent state cue (02-UI-SPEC.md Layout & Composition
    zone 3).

    Sized to fit within both the ~SILHOUETTE_TARGET_W width cap and the
    SILHOUETTE_MAX_H height cap while preserving the vendored asset's own
    aspect ratio - whichever cap binds first governs the actual size (see
    VENDOR.md: the source's ~2.22:1 aspect ratio means the height cap
    binds well before the width cap is reached).

    Called only for the active (departing/arriving) states - the Empty
    state draws no silhouette at all (D-04/UI-SPEC: nothing detected yet,
    nothing to depict).

    Returns the silhouette's absolute bounding box (left, top, right,
    bottom) for the caller's own guard-rail assertions.
    """
    with Image.open(SILHOUETTE_PATH) as probe:
        src_w, src_h = probe.size
    aspect = src_w / src_h

    sil_w = SILHOUETTE_TARGET_W
    sil_h = round(sil_w / aspect)
    if sil_h > SILHOUETTE_MAX_H:
        sil_h = SILHOUETTE_MAX_H
        sil_w = round(sil_h * aspect)

    center_x = WIDTH // 2
    left = center_x - sil_w // 2
    top = SILHOUETTE_ZONE_TOP + SPACE_3XL

    required_nose = "right" if state == runway_config.STATE_DEPARTING else "left"
    mirror = required_nose != SILHOUETTE_SOURCE_NOSE

    bbox = paste_mask(canvas, SILHOUETTE_PATH, (left, top, sil_w, sil_h), ink_idx, mirror=mirror)
    _assert_in_safe_box(bbox, "aircraft silhouette")
    assert bbox[1] >= SILHOUETTE_ZONE_TOP, (
        "silhouette top %r overlaps the state-label band (SILHOUETTE_ZONE_TOP=%d)" % (bbox[1], SILHOUETTE_ZONE_TOP)
    )
    assert bbox[3] <= SILHOUETTE_ZONE_TOP + SILHOUETTE_ZONE_HEIGHT, (
        "silhouette bottom %r overflows its reserved zone-3 footprint" % (bbox[3],)
    )
    return bbox


def _route_line_reserved_height():
    """The route line's (zone 7) row height: the two runs share one
    baseline row, so the row height is the max of the Label-role prefix's
    and the Destination/Origin hero-secondary role's font-metric line
    heights. Pure function of the fixed LABEL_FONT/DESTINATION_FONT sizes
    only - never of any rendered text - which is what lets the airline
    line's top Y stay identical whether or not the route line actually
    draws (see the 02-04 module note above FLIGHT_NUMBER_TOP_Y).
    """
    label_ascent, label_descent = _font(LABEL_FONT).getmetrics()
    dest_ascent, dest_descent = _font(DESTINATION_FONT).getmetrics()
    return max(label_ascent + label_descent, dest_ascent + dest_descent)


def draw_route_line(canvas, state, ink_idx, city_text, top_y, bg_idx):
    """Draw UI-SPEC zone 7: an uppercase, letter-spaced Label-role prefix
    (`ROUTE_PREFIX_TEXT[state]` - "TO" for departing, "FROM" for arriving)
    followed by a Body-role city name (sentence case), horizontally centred
    as one composite line at `top_y`. Both runs are measured before either
    is drawn so the pair reads as one centred line, not two independently
    centred fragments. The city run shrinks via `fit_text_size()` rather
    than clipping if it would cross the safe box on its own. 03-02: a
    single quiet-zone rectangle covers the combined prefix-plus-city bbox
    (not two separate plates), drawn before either run.

    Returns `(quiet_rect, bbox)` - the drawn quiet-zone rectangle and the
    composite line's own absolute bounding box.
    """
    draw = ImageDraw.Draw(canvas)
    prefix = ROUTE_PREFIX_TEXT[state]
    label_font = _font(LABEL_FONT)
    safe_width = SAFE_BOX[2] - SAFE_BOX[0]

    prefix_width = _tracked_text_width(label_font, prefix, LABEL_TRACKING_PX)
    city_max_width = max(1, safe_width - prefix_width - ROUTE_PREFIX_GAP_PX)
    dest_font = fit_text_size(_ZILLA_SEMIBOLD, DESTINATION_FONT[1], city_text, city_max_width)
    city_width = dest_font.getlength(city_text)

    total_width = prefix_width + ROUTE_PREFIX_GAP_PX + city_width
    center_x = WIDTH // 2
    left = center_x - total_width / 2

    row_height = _route_line_reserved_height()
    label_ascent, label_descent = label_font.getmetrics()
    dest_ascent, dest_descent = dest_font.getmetrics()
    prefix_y = top_y + (row_height - (label_ascent + label_descent)) // 2
    city_y = top_y + (row_height - (dest_ascent + dest_descent)) // 2

    bbox = (left, top_y, left + total_width, top_y + row_height)
    _assert_in_safe_box(bbox, "route line")
    quiet_rect = draw_quiet_zone(canvas, bbox, bg_idx)

    prefix_end_x = draw_tracked_text(draw, (left, prefix_y), prefix, label_font, ink_idx, tracking=LABEL_TRACKING_PX)
    city_x = prefix_end_x + ROUTE_PREFIX_GAP_PX
    draw.text((city_x, city_y), city_text, font=dest_font, fill=ink_idx)

    return quiet_rect, bbox


def draw_airline_line(canvas, ink_idx, text, top_y, bg_idx):
    """Draw UI-SPEC zone 9: a single Body-role, regular-weight run
    (the airline name, or `ROUTE_FALLBACK_TEXT` on an enrichment miss),
    horizontally centred, top-anchored at `top_y`. Shrinks via
    `fit_text_size()` rather than clipping if it would cross the safe box.
    03-02: the measured bbox gets a quiet-zone rectangle before the text
    itself is drawn.

    `top_y` is always the caller's fixed airline-line position - identical
    whether or not the route line rendered this call - so this function
    never needs to know why it was invoked, only where to draw.

    Returns the drawn quiet-zone rectangle.
    """
    draw = ImageDraw.Draw(canvas)
    safe_width = SAFE_BOX[2] - SAFE_BOX[0]
    font = fit_text_size(_ZILLA_SEMIBOLD, CAPTION_FONT[1], text, safe_width)
    center_x = WIDTH // 2
    bbox = draw.textbbox((center_x, top_y), text, font=font, anchor="ma")
    _assert_in_safe_box(bbox, "airline line")
    quiet_rect = draw_quiet_zone(canvas, bbox, bg_idx)
    draw.text((center_x, top_y), text, font=font, fill=ink_idx, anchor="ma")
    return quiet_rect


def _build_empty_canvas():
    canvas = pf.new_canvas(IDX_WHITE)
    draw = ImageDraw.Draw(canvas)
    heading_font = _font(FLIGHT_NUMBER_FONT)
    body_font = _font(CAPTION_FONT)
    center_x = WIDTH // 2
    safe_width = SAFE_BOX[2] - SAFE_BOX[0]

    heading_ascent, heading_descent = heading_font.getmetrics()
    heading_height = heading_ascent + heading_descent

    body_lines = _wrap_text(body_font, EMPTY_BODY_TEXT, safe_width)
    body_ascent, body_descent = body_font.getmetrics()
    body_line_height = body_ascent + body_descent

    total_height = heading_height + SPACE_SM + len(body_lines) * body_line_height
    start_y = (HEIGHT - total_height) // 2

    heading_bbox = draw.textbbox((center_x, start_y), EMPTY_HEADING_TEXT, font=heading_font, anchor="ma")
    _assert_in_safe_box(heading_bbox, "empty-state heading")
    draw.text((center_x, start_y), EMPTY_HEADING_TEXT, font=heading_font, fill=IDX_BLACK, anchor="ma")

    y = start_y + heading_height + SPACE_SM
    for line in body_lines:
        line_bbox = draw.textbbox((center_x, y), line, font=body_font, anchor="ma")
        _assert_in_safe_box(line_bbox, "empty-state body line")
        draw.text((center_x, y), line, font=body_font, fill=IDX_BLACK, anchor="ma")
        y += body_line_height

    return canvas


_LEGAL_PANEL_INDICES = {IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN}

# Out-of-band sentinel used by _assert_palette_contract() to blank the
# illustration bbox on a scratch copy of the canvas before checking the
# rest of the panel - legal as a Pillow palette index (0..255), never
# packed to the wire (pack_panel() only ever sees canvases built without
# this sentinel), and cheap to fill because it happens at C speed via
# ImageDraw.rectangle(), not a 1.92-million-element Python getdata() loop.
_ILLUSTRATION_SENTINEL_IDX = 255


def _assert_palette_contract(canvas, bg_idx, quiet_rects, illustration_bbox=None):
    """Spatially-scoped replacement for the old whole-canvas "exactly 2
    distinct palette indices" guard rail (03-RESEARCH.md Pitfall 1: a bug
    painting the flight number Yellow would sail through a naive
    `len(colors) <= 6` raised-ceiling check). Asserts, in order:

    1. Every index present anywhere on the canvas is one of the 6 legal
       panel indices.
    2. Each rectangle in `quiet_rects` contains only `{bg_idx, IDX_WHITE}`,
       and both are actually present (a quiet zone containing only bg_idx
       means the text failed to draw).
    3. Outside `illustration_bbox` (via a C-speed sentinel-rectangle fill on
       a scratch copy, not a Python-level getdata()/mask zip), the index
       set is exactly `{bg_idx, IDX_WHITE}` - or, when `illustration_bbox`
       is None (this plan's state, before 03-03 wires the illustration),
       the *whole* canvas's index set must be exactly `{bg_idx, IDX_WHITE}`.
    4. `bg_idx` accounts for more pixels than IDX_WHITE does, so the panel
       is provably hue-dominant rather than a mostly-white field.

    Every assertion message names the state's background index, the
    offending index/region, so an on-glass failure is diagnosable from a
    log line rather than by eye.
    """
    colors = canvas.getcolors()
    # Pillow's getcolors() returns (count, value) pairs - count first.
    whole_idx_set = {value for _count, value in colors} if colors else set()
    illegal = whole_idx_set - _LEGAL_PANEL_INDICES
    assert not illegal, (
        "canvas (bg_idx=%r) contains illegal palette index(es) %r - expected a subset of the 6 legal panel indices %r"
        % (bg_idx, sorted(illegal), sorted(_LEGAL_PANEL_INDICES))
    )

    allowed_quiet = {bg_idx, IDX_WHITE}
    for rect in quiet_rects:
        left, top, right, bottom = (int(v) for v in rect)
        crop = canvas.crop((left, top, right, bottom))
        crop_colors = crop.getcolors()
        crop_idx_set = {value for _count, value in crop_colors} if crop_colors else set()
        illegal_in_zone = crop_idx_set - allowed_quiet
        assert not illegal_in_zone, (
            "quiet zone %r (bg_idx=%r) contains illegal index(es) %r - expected a subset of %r"
            % (rect, bg_idx, sorted(illegal_in_zone), sorted(allowed_quiet))
        )
        assert allowed_quiet.issubset(crop_idx_set), (
            "quiet zone %r (bg_idx=%r) is missing one of %r (found %r) - the text may have failed to draw"
            % (rect, bg_idx, sorted(allowed_quiet), sorted(crop_idx_set))
        )

    outside_canvas = canvas.copy()
    if illustration_bbox is not None:
        ImageDraw.Draw(outside_canvas).rectangle(illustration_bbox, fill=_ILLUSTRATION_SENTINEL_IDX)
        expected_outside = {bg_idx, IDX_WHITE, _ILLUSTRATION_SENTINEL_IDX}
    else:
        expected_outside = {bg_idx, IDX_WHITE}
    outside_colors = outside_canvas.getcolors()
    outside_idx_set = {value for _count, value in outside_colors} if outside_colors else set()
    assert outside_idx_set == expected_outside, (
        "canvas outside the illustration bbox (bg_idx=%r, illustration_bbox=%r) has index set %r, expected exactly %r"
        % (bg_idx, illustration_bbox, sorted(outside_idx_set), sorted(expected_outside))
    )

    counts = {value: count for count, value in colors} if colors else {}
    bg_count = counts.get(bg_idx, 0)
    white_count = counts.get(IDX_WHITE, 0)
    assert bg_count > white_count, (
        "canvas's state index bg_idx=%r has %d pixels vs IDX_WHITE's %d - panel is not hue-dominant"
        % (bg_idx, bg_count, white_count)
    )


def _build_active_canvas(flight, state, route=None):
    if state not in STATE_BACKGROUND:
        raise ValueError("unknown state %r (expected 'departing', 'arriving', or 'empty')" % (state,))
    bg_idx = STATE_BACKGROUND[state]
    fg_idx = STATE_INK[state]

    # 03-02 (D-17): the flat pf.new_canvas(bg_idx) fill is replaced by a
    # deterministic, Floyd-Steinberg-dithered, two-tone mood gradient in
    # the state's own hue. build_mood_background() already returns a
    # fresh, palette-padded copy, so no further preparation is needed here.
    canvas = dither.build_mood_background(state)
    draw = ImageDraw.Draw(canvas)
    center_x = WIDTH // 2
    quiet_rects = []

    # UI-SPEC zone 1: state label - plane-takeoff/plane-landing glyph +
    # tracked DEPARTING/ARRIVING text, backed by its own quiet-zone
    # rectangle now that the background is dithered, not flat (03-02).
    quiet_rects.append(draw_state_label(canvas, state, fg_idx, bg_idx))

    # UI-SPEC zone 3: the aircraft silhouette centrepiece, mirrored by
    # state (02-03) - the panel's primary visual anchor, drawn before the
    # flight-number caption below it so the visual reading order in code
    # matches the visual reading order on the panel. Still a flat fg_idx
    # (White) fill via load_binary_mask()'s hard threshold - no quiet zone
    # needed (it is not text), and no multi-colour illustration exception
    # yet (that is 03-03's job; illustration_bbox stays None until then).
    draw_silhouette(canvas, state, fg_idx)

    # UI-SPEC zone 5: flight-number caption, hero-primary size (D-16),
    # horizontally centred, defensively fitted through fit_text_size() the
    # same way the other roles are (ICAO-format callsigns are short and
    # fixed-pattern, so this path is expected to rarely trigger, but the
    # safe-box assertion must still hold for any input). Falls back to the
    # aircraft's hex uppercased when no callsign was recovered, so the
    # panel never renders an empty hero line. 03-02: quiet-zoned before the
    # text itself is drawn.
    callsign = flight.get("callsign") or (flight.get("hex") or "").upper() or "?"
    safe_width = SAFE_BOX[2] - SAFE_BOX[0]
    heading_font = fit_text_size(_ZILLA_BOLD, FLIGHT_NUMBER_FONT[1], callsign, safe_width)
    heading_bbox = draw.textbbox((center_x, FLIGHT_NUMBER_TOP_Y), callsign, font=heading_font, anchor="ma")
    _assert_in_safe_box(heading_bbox, "flight number caption")
    quiet_rects.append(draw_quiet_zone(canvas, heading_bbox, bg_idx))
    draw.text((center_x, FLIGHT_NUMBER_TOP_Y), callsign, font=heading_font, fill=fg_idx, anchor="ma")

    # UI-SPEC zones 5-9: route line (7) + airline line (9), 02-04
    # (PLANE-01/02). The airline line's top Y is computed from fixed font
    # metrics only (never from a rendered route line's bbox), so it lands
    # at the exact same absolute position whether or not zone 7 draws this
    # call - see the module note above ROUTE_PREFIX_DEPARTING.
    route_line_top_y = heading_bbox[3] + SPACE_SM
    airline_line_top_y = route_line_top_y + _route_line_reserved_height() + SPACE_MD

    city_text = enrich.city_for_state(route, state) if route is not None else None
    airline_text = route.get("airline_name") if route is not None else None
    if city_text and airline_text:
        route_quiet_rect, _route_bbox = draw_route_line(canvas, state, fg_idx, city_text, route_line_top_y, bg_idx)
        quiet_rects.append(route_quiet_rect)
        quiet_rects.append(draw_airline_line(canvas, fg_idx, airline_text, airline_line_top_y, bg_idx))
    else:
        # No route, or (defensively) an incomplete one - enrich.lookup_route
        # never returns a half-resolved route (UI-SPEC has no partial
        # state), so this also covers that impossible case safely.
        quiet_rects.append(draw_airline_line(canvas, fg_idx, ROUTE_FALLBACK_TEXT, airline_line_top_y, bg_idx))

    # UI-SPEC zone 11: bottom-anchored static tag, Label size, tracked
    # letter-spacing, White. 03-02: quiet-zoned before the text is drawn -
    # this zone's own bounding box already ends exactly on the safe-box
    # bottom edge, so draw_quiet_zone()'s clamping is what keeps the
    # padded rectangle from breaching the inviolable margin.
    label_font = _font(LABEL_FONT)
    tag_width = _tracked_text_width(label_font, BOTTOM_TAG_TEXT, LABEL_TRACKING_PX)
    label_ascent, label_descent = label_font.getmetrics()
    tag_line_height = label_ascent + label_descent
    tag_x = center_x - tag_width / 2
    tag_y = HEIGHT - MARGIN - tag_line_height
    tag_bbox = (tag_x, tag_y, tag_x + tag_width, tag_y + tag_line_height)
    _assert_in_safe_box(tag_bbox, "bottom static tag")
    quiet_rects.append(draw_quiet_zone(canvas, tag_bbox, bg_idx))
    draw_tracked_text(draw, (tag_x, tag_y), BOTTOM_TAG_TEXT, label_font, fg_idx, tracking=LABEL_TRACKING_PX)

    # Guard rail (03-02, replacing the old whole-canvas "exactly 2 distinct
    # palette indices" check): a spatially-scoped palette contract - every
    # quiet zone is {bg_idx, IDX_WHITE} only, and (with no illustration bbox
    # wired yet) the whole canvas is too. Failing loudly here is better
    # than shipping a subtly wrong panel to the glass, where the failure is
    # only visible by eye.
    _assert_palette_contract(canvas, bg_idx, quiet_rects, illustration_bbox=None)

    return canvas


def build_canvas(flight, state, route=None):
    """Return the pre-pack "P"-mode canvas for `flight` in `state`
    ("departing" / "arriving" / "empty"). Public (not `_build_canvas`) so
    callers - notably server/test_render.py's anti-aliasing assertions,
    which read Image.getcolors() directly - never have to reach into
    private render state.

    `route` is the normalised dict from server.plane.enrich.lookup_route()
    (or None on an enrichment miss / for the empty state) - drives zones 7
    ("route line") and 9 ("airline line"), 02-04 (PLANE-01/02). Ignored for
    the empty state, which has no flight to enrich.
    """
    if flight is None or state == "empty":
        return _build_empty_canvas()
    return _build_active_canvas(flight, state, route=route)


def render_panel(flight, state, route=None):
    """Return a packed 960,000-byte panel for `flight` (the normalised dict
    from detect.select_runway3_aircraft(), or None) in `state`
    ("departing" / "arriving" / "empty").

    `state` is the return value of a server.plane.runway_config call
    (poll_loop.py never hardcodes it) - server.plane.runway_config.py's
    STATE_DEPARTING/STATE_ARRIVING constants are the exact strings
    "departing"/"arriving" this function and build_canvas() key their
    per-state dicts on.

    `route` is the normalised dict from server.plane.enrich.lookup_route()
    (or None), passed straight through to build_canvas() (02-04).
    """
    canvas = build_canvas(flight, state, route=route)
    return pf.pack_panel(canvas)


# Manual-QA-only sample route (02-04) - server/plane/render.py's CLI has no
# live enrichment lookup of its own (that's poll_loop.py's job); this is
# just a plausible-looking hit so `--preview` without `--no-route` shows
# zones 7/9's resolved-route layout rather than always previewing the
# fallback.
_PREVIEW_ROUTE = {
    "airline_name": "Air France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "JFK",
    "destination_city": "New York",
}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=["departing", "arriving", "empty"], default="empty")
    parser.add_argument("--callsign", default=None, help="Manual QA only: fake callsign for a departing/arriving preview.")
    parser.add_argument("--hex", default="000000", help="Manual QA only: fake ICAO hex (used if --callsign is omitted).")
    parser.add_argument("--out", help="Write the packed 960,000-byte .bin to this path.")
    parser.add_argument(
        "--preview",
        metavar="PATH",
        help="Also write a viewable PNG preview. WARNING (D-P2-03): preview colours "
             "are nominal render-internal RGB triples, not a colour-accurate panel preview.",
    )
    parser.add_argument(
        "--no-route",
        action="store_true",
        help="Manual QA only (02-04): preview the enrichment-miss fallback ('Route unavailable') "
             "instead of the default sample resolved-route preview.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    flight = None
    route = None
    if args.state != "empty":
        flight = {"hex": args.hex, "callsign": args.callsign}
        route = None if args.no_route else _PREVIEW_ROUTE

    canvas = build_canvas(flight, args.state, route=route)
    data = pf.pack_panel(canvas)
    if len(data) != pf.IMAGE_BYTES:
        sys.exit("internal error: generated %d bytes, expected %d" % (len(data), pf.IMAGE_BYTES))

    if args.out:
        with open(args.out, "wb") as fh:
            fh.write(data)
        digest = hashlib.sha256(data).hexdigest()
        print("wrote %s (%d bytes, state=%s)" % (args.out, len(data), args.state))
        print("sha256 %s" % digest)

    if args.preview:
        print(
            "WARNING: preview colours are nominal render-internal RGB triples "
            "(D-P2-03) - not a colour-accurate preview of the physical panel."
        )
        canvas.convert("RGB").save(args.preview)
        print("wrote preview %s" % args.preview)

    if not args.out and not args.preview:
        digest = hashlib.sha256(data).hexdigest()
        print("rendered %d bytes (state=%s), sha256 %s (pass --out/--preview to write a file)"
              % (len(data), args.state, digest))

    return 0


if __name__ == "__main__":
    sys.exit(main())
