#!/usr/bin/env python3
"""Panel renderer for the plane view: departure and arrival cards for the
watched runway, plus an empty state.

Draws onto a "P"-mode canvas with integer palette-index fills, never RGB,
to keep anti-aliasing off flat fills; the per-airline illustrations are
the one full-color, dithered exception.

Layout: flat single-color state background, no dithered gradient.
Illustrations are always nose-left, never mirrored. Two flight cards
share one canvas: current detection (large, upper-center) and the
previous one (smaller, bottom-right, right-aligned to the main
illustration's edge). Text uses PT Serif Bold, except on White (never
dithered, so Regular suffices).

Colour comes from `server/device_config.py`'s `THEMES` registry
(`white` default); not yet calibrated against real glass, only
on-screen previews. The 64px SAFE_BOX margin applies only to the
top-row labels; the frame, illustrations and flight text sit at a
tighter ~2.5%-of-width inset, inside that band.

Usage (manual QA):
    server/.venv/bin/python3 server/plane/render.py --state empty --out /tmp/panel.bin
    server/.venv/bin/python3 server/plane/render.py --state arriving --callsign AF1380 \
        --out /tmp/panel.bin --preview /tmp/panel.preview.png
    server/.venv/bin/python3 server/plane/render.py --state departing --callsign AF1380 \
        --previous-callsign VY1234 --out /tmp/panel.bin --preview /tmp/panel.preview.png
    server/.venv/bin/python3 server/plane/render.py --state arriving --callsign AFR56XX \
        --airline "Compagnie Nationale Royale Air Maroc Express" \
        --city "Santiago de Compostela-Rosalia de Castro" --preview /tmp/longname.png
    server/.venv/bin/python3 server/plane/render.py --calibration-preview /tmp/calib
"""
import argparse
import hashlib
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# Allow both package import and direct script execution: sys.path[0] is
# server/plane/ when run directly, so the repo root must be added by hand.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/plane
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import device_config
from server import panel_format as pf
from server.panel_format import IDX_BLACK, IDX_BLUE, IDX_GREEN, IDX_RED, IDX_WHITE, IDX_YELLOW, WIDTH, HEIGHT
from server.plane import dither, enrich, illustrations, runway_config

# --- Spacing scale ---------------------------------------------------------
SPACE_XS = 8
SPACE_SM = 16
SPACE_MD = 32
SPACE_LG = 64

# MARGIN is the top-row labels' inset, not a blanket margin (see module docstring).
MARGIN = SPACE_LG
SAFE_BOX = (MARGIN, MARGIN, WIDTH - MARGIN, HEIGHT - MARGIN)  # (64, 64, 1136, 1536)

# --- Typography --------------------------------------------------------
FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")
)
PT_SERIF_REGULAR = os.path.join(FONT_DIR, "PTSerif-Regular.ttf")
PT_SERIF_BOLD = os.path.join(FONT_DIR, "PTSerif-Bold.ttf")

# Per-role (font_path, size, weight); weight is documentation only. Bold
# is the base weight (carries legibility against a dithered background);
# `_role_font()`/`_role_fit_text_size()` substitute Regular when
# `bg_idx == IDX_WHITE` (never dithered) - always go through those, never
# these tuples directly.
STATE_LABEL_FONT = (PT_SERIF_BOLD, 20, 700)
TOP_TAG_FONT = (PT_SERIF_BOLD, 18, 700)
MAIN_LINE1_FONT = (PT_SERIF_BOLD, 40, 700)
MAIN_LINE2_FONT = (PT_SERIF_BOLD, 22, 700)
PREVIOUS_LINE1_FONT = (PT_SERIF_BOLD, 28, 700)
PREVIOUS_LINE2_FONT = (PT_SERIF_BOLD, 20, 700)
EMPTY_HEADING_FONT = (PT_SERIF_BOLD, 72, 700)
EMPTY_BODY_FONT = (PT_SERIF_REGULAR, 40, 400)

# Letter-spacing (tracking) applied to the top row's two smallest text roles
# (STATE_LABEL_FONT, TOP_TAG_FONT) via draw_tracked_text() in
# draw_top_labels(). Screen-preview-validated only - never checked against
# real Spectra 6 ink.
LABEL_TRACKING_PX = 6

# Band-theme top-label direction word. Only consulted by draw_top_labels()
# when `band_theme=True`.
_BAND_TOP_LABEL_DIRECTION = {
    runway_config.STATE_DEPARTING: "FROM",
    runway_config.STATE_ARRIVING: "TO",
}

# Overflow floors (fit_text_size()'s per-role minimums) - real city/airline
# names shrink in small steps rather than clipping, wrapping mid-word, or
# overflowing, but never below these named limits.
MAIN_LINE1_MIN_SIZE = 28
MAIN_LINE2_MIN_SIZE = 16
PREVIOUS_LINE1_MIN_SIZE = 18
PREVIOUS_LINE2_MIN_SIZE = 12
# Guard-rail floor for the (short, runway-dependent) empty-state heading;
# not expected to bind in practice.
EMPTY_HEADING_MIN_SIZE = 48
_FIT_STEP_PX = 2

# --- Colour (state-scoped), keyed by runway_config's STATE_* constants. --
#
# STATE_BACKGROUND/STATE_INK are kept as module constants only because
# server/test_render.py reads them directly. New code must call
# state_background_index()/state_ink_index() instead, which resolve
# through device_config.THEMES (the single registry the Config page's
# picker also reads); do not delete these constants.
STATE_BACKGROUND = {
    runway_config.STATE_DEPARTING: device_config.theme_background_index(
        runway_config.STATE_DEPARTING, device_config.DEFAULT_THEME_ID
    ),
    runway_config.STATE_ARRIVING: device_config.theme_background_index(
        runway_config.STATE_ARRIVING, device_config.DEFAULT_THEME_ID
    ),
}
STATE_INK = {
    runway_config.STATE_DEPARTING: device_config.theme_ink_index(device_config.DEFAULT_THEME_ID),
    runway_config.STATE_ARRIVING: device_config.theme_ink_index(device_config.DEFAULT_THEME_ID),
}
STATE_LABEL_TEXT = {
    runway_config.STATE_DEPARTING: "DEPARTING",
    runway_config.STATE_ARRIVING: "ARRIVING",
}


def state_background_index(state, theme_id=device_config.DEFAULT_THEME_ID):
    """Background palette index for `state` under `theme_id`. An
    unrecognised `theme_id` degrades to the default theme; an unrecognised
    `state` is a caller bug and is never normalised.
    """
    theme_id = device_config.normalise_theme_id(theme_id)
    return device_config.theme_background_index(state, theme_id)


def state_ink_index(state, theme_id=device_config.DEFAULT_THEME_ID):
    """Ink (foreground) index for `theme_id`. Same contract as
    state_background_index(); `state` is accepted for call-shape symmetry
    even though ink does not currently vary by state.
    """
    theme_id = device_config.normalise_theme_id(theme_id)
    return device_config.theme_ink_index(theme_id)


def runway_tag_text(runway_id=device_config.DEFAULT_RUNWAY_ID):
    """Top-right tag string for `runway_id`; an unrecognised id degrades
    to the default runway rather than raising.
    """
    runway_id = device_config.normalise_runway_id(runway_id)
    return device_config.runway_tag_text(runway_id)


def empty_heading_text(runway_id=device_config.DEFAULT_RUNWAY_ID):
    """Same contract as runway_tag_text(), for the empty-state heading."""
    runway_id = device_config.normalise_runway_id(runway_id)
    return device_config.runway_empty_heading(runway_id)


# Retained as module constants only because server/test_render.py reads
# them directly; new code should call empty_heading_text()/runway_tag_text().
EMPTY_HEADING_TEXT = empty_heading_text(device_config.DEFAULT_RUNWAY_ID)

# Not theme-dependent - the empty state is always White/Black - so this
# stays a bare constant rather than resolving through state_ink_index().
# The source-fault badge and battery icon share it for the same reason.
EMPTY_INK = IDX_BLACK
# Break falls before "the display", not wherever the measured width
# lands. EMPTY_BODY_TEXT is the joined form the copy is asserted against;
# the builder wraps each sentence separately to honour the break.
EMPTY_BODY_LINES = (
    "No aircraft detected yet.",
    "The display updates the moment one is.",
)
EMPTY_BODY_TEXT = " ".join(EMPTY_BODY_LINES)
TOP_RIGHT_TAG_TEXT = runway_tag_text(device_config.DEFAULT_RUNWAY_ID)
ROUTE_FALLBACK_TEXT = "Route unavailable"

# Locked English copy, matching every other panel string. Do not localise.
QUIET_HOURS_HEADING_TEXT = "QUIET HOURS"
QUIET_HOURS_BODY_TEMPLATE = "Back at %s"

# Locked English copy. A plain string, not a `%`-template: a manual
# toggle has no end time to interpolate. Withholds fault vocabulary
# ("unavailable", "error", ...) - this is an operator action, not a fault.
DISPLAY_OFF_HEADING_TEXT = "DISPLAY OFF"
# Break falls after "page.". Joined form kept for the locked-copy
# equality check; _build_display_off_canvas() wraps each sentence
# separately.
DISPLAY_OFF_BODY_LINES = (
    "Switched off from the companion page.",
    "Turn it back on there anytime.",
)
DISPLAY_OFF_BODY_TEXT = " ".join(DISPLAY_OFF_BODY_LINES)

# Locked English copy, same fixed-string convention as DISPLAY_OFF_* -
# a fixed-string sibling, not a %-template (there is no return time for a
# flat pack). Deliberately no fault vocabulary ("unavailable", "error",
# "offline", "disconnected") - a flat battery is expected, not a
# malfunction - and the second sentence stays true because poll_loop
# resumes the frame on its own once a recovering reading arrives, with no
# user action beyond charging.
BATTERY_EMPTY_HEADING_TEXT = "BATTERY EMPTY"
BATTERY_EMPTY_BODY_LINES = (
    "Charge the frame over USB-C.",
    "It will pick up where it left off.",
)
BATTERY_EMPTY_BODY_TEXT = " ".join(BATTERY_EMPTY_BODY_LINES)

# Locked English copy. The server never renders this screen - the
# firmware draws it on its own (firmware/tools/gen_fault_screen.py bakes
# it into fault_screen_mask.h at build time), so changing either sentence
# requires regenerating that header or server/test_fault_screen_mask.py's
# drift test fails.
NO_CONNECTION_HEADING_TEXT = "NO CONNECTION"
NO_CONNECTION_BODY_LINES = (
    "The frame can't reach its server.",
    "It will try again on its own.",
)
NO_CONNECTION_BODY_TEXT = " ".join(NO_CONNECTION_BODY_LINES)

# --- The dimmed hold composition ------------------------------------------
# Shared by DISPLAY OFF and QUIET HOURS via _build_dimmed_hold_canvas():
# glyph, tracked Bold label over a hairline rule, then body, on a dimmed
# field (Black dithered toward White, white ink). DARK means the frame is
# resting on purpose; WHITE means it is working. Bold, not Regular: thin
# white strokes drown in dither noise.
DIMMED_FIELD_IDX = IDX_BLACK
DIMMED_INK = IDX_WHITE
DIMMED_LABEL_FONT = (PT_SERIF_BOLD, 40, 700)
DIMMED_LABEL_TRACKING_PX = 10
DIMMED_RULE_WIDTH_PX = 120
DIMMED_RULE_HEIGHT_PX = 4
DIMMED_BODY_FONT = EMPTY_BODY_FONT
DIMMED_BODY_LINE_GAP_PX = 6

# Points at the companion page, where an all-sources-down outage is
# diagnosed. Glyph is small so _assert_legal_palette()'s background-
# dominance assertion still holds - see draw_source_fault_badge().
SOURCE_FAULT_TEXT = "ADS-B source unavailable — check the companion page"
SOURCE_FAULT_GLYPH_PX = 28

# --- Frame + layout geometry ------------------------------------------
FRAME_INSET_FRAC = 0.025  # ~2.5% of canvas WIDTH, inset from every edge
FRAME_STROKE_PX = 2

MAIN_ILLUSTRATION_WIDTH_FRAC = 0.87  # of the inner (post-frame-inset) canvas width
# Fraction of canvas height, anchored on the illustration's PAINTED
# content centre, not its source rectangle: top transparent padding
# varies per file (6-124px), which would otherwise drift the visible
# centre by 100+px depending on which airline is flying. Sizing still
# derives from `.rect`; only position follows painted pixels.
MAIN_ILLUSTRATION_CENTER_Y_FRAC = 0.4006
MAIN_LINE_GAP_PX = 8  # gap between main line 1's bottom and line 2's top

PREVIOUS_ILLUSTRATION_WIDTH_FRAC = 0.57  # of the MAIN illustration's own rendered width
# Anchored on painted-pixel centre: the drop-shadow band makes bottom
# padding exceed top padding, so a rectangle-centred anchor would push
# the visible aircraft high by a per-file amount.
PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC = 0.7528
PREVIOUS_LINE_GAP_PX = 34  # line 2's top below line 1's own TOP (not bottom)

# Optical correction: the aircraft's rightmost painted pixel often sits on
# a thin tail-fin tip, not the fuselage mass the eye anchors on, so text
# right-aligned to the true edge reads as floating right of the aircraft.
PREVIOUS_TEXT_LEFT_OFFSET_PX = 20

# --- Aircraft-to-text gaps ---------------------------------------------
# Measured from the OPAQUE-PIXEL bottom edge (`IllustrationPlacement.
# content`), not the source rectangle: the soft drop-shadow band below
# each aircraft varies per file, and `draw_illustration()` never paints
# it (hard-thresholded away).
MAIN_TEXT_GAP_PX = 54  # main text top = main illustration's OPAQUE bottom + this
PREVIOUS_TEXT_GAP_PX = 47  # previous text top = its OPAQUE bottom + this

# --- Diagonal band geometry ---------------------------------------------
# Measured from the reference image via per-row pixel scanning + linear
# regression. A trapezoid: top and bottom edges span different fractions
# of canvas width. `BAND_BOT_LEFT_FRAC` is floored at 0.0 as a guard
# against a negative shift walking the polygon off-canvas.
BAND_SHIFT_FRAC = 0.0
BAND_TOP_LEFT_FRAC = 0.5818 + BAND_SHIFT_FRAC
BAND_TOP_RIGHT_FRAC = 0.8523 + BAND_SHIFT_FRAC
BAND_BOT_LEFT_FRAC = max(0.0, 0.0742 + BAND_SHIFT_FRAC)
BAND_BOT_RIGHT_FRAC = 0.4772 + BAND_SHIFT_FRAC


def draw_diagonal_band(canvas, band_idx, dithered=False):
    """Paint the diagonal trapezoid band onto `canvas` in `band_idx`'s
    colour (flat or dithered toward White). Must be called before any
    text/illustration drawing so the band sits behind them. Geometry: see
    the `BAND_*_FRAC` constants above.
    """
    w, h = canvas.size
    poly = [
        (BAND_TOP_LEFT_FRAC * w, 0), (BAND_TOP_RIGHT_FRAC * w, 0),
        (BAND_BOT_RIGHT_FRAC * w, h), (BAND_BOT_LEFT_FRAC * w, h),
    ]
    if dithered:
        band_fill = dither.dithered_state_background(band_idx)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        canvas.paste(band_fill, (0, 0), mask)
    else:
        ImageDraw.Draw(canvas).polygon(poly, fill=band_idx)


def _band_edges(canvas_y, w):
    """Band's left/right pixel edges at canvas row `y`. Returns
    (left_x, right_x) in pixels.
    """
    f = canvas_y / HEIGHT
    left_frac = BAND_TOP_LEFT_FRAC - (BAND_TOP_LEFT_FRAC - BAND_BOT_LEFT_FRAC) * f
    right_frac = BAND_TOP_RIGHT_FRAC - (BAND_TOP_RIGHT_FRAC - BAND_BOT_RIGHT_FRAC) * f
    return left_frac * w, right_frac * w


def _band_center_x(canvas_y, w):
    """Band's horizontal centre at canvas row `y` (the centreline shifts
    left as `y` increases, so this is not a constant). Compute once per
    text block and reuse for every line - recomputing per line staggers
    the column instead of aligning it.
    """
    left_x, right_x = _band_edges(canvas_y, w)
    return (left_x + right_x) / 2


# --- Battery-low icon geometry ------------------------------------------
# SIZE constants are round(original * 0.7); the original (72x32-nominal)
# glyph read too large on real Spectra 6 glass. Total bounding box is
# (64, 1514, 115, 1536).
BATTERY_ICON_LEFT = MARGIN  # 64 - same left inset as the top-row labels
BATTERY_ICON_BOTTOM = HEIGHT - MARGIN  # 1536 - same bottom inset, mirrored
BATTERY_ICON_BODY_W = 45  # round(SPACE_LG * 0.7) = round(64 * 0.7) = round(44.8)
BATTERY_ICON_BODY_H = 22  # round(SPACE_MD * 0.7) = round(32 * 0.7) = round(22.4)
BATTERY_ICON_NUB_W = 6  # round(SPACE_XS * 0.7) = round(8 * 0.7) = round(5.6)
BATTERY_ICON_NUB_H = 11  # round(SPACE_SM * 0.7) = round(16 * 0.7) = round(11.2) - the odd
# BODY_H - NUB_H leftover (11) puts the nub's vertical centring one pixel low
# (5px gap above, 6px below) rather than exactly symmetric.
BATTERY_ICON_STROKE_PX = 2  # round(3 * 0.7) = round(2.1); now equal to FRAME_STROKE_PX,
# held there as the e-ink legibility floor - the reduction stops here rather
# than continuing toward an illegible 1px hairline.
BATTERY_ICON_FILL_FRAC = 0.22  # bespoke: a fixed "low" glyph, not a live gauge - a ratio, not a pixel size

_font_cache = {}


def _font(spec):
    path, size, _weight = spec
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def fit_text_size(font_path, initial_size, text, max_width, min_size):
    """Largest ImageFont at `font_path` whose rendered `text` width fits
    `max_width`, stepping down from `initial_size`, floored at `min_size`.
    """
    size = initial_size
    while size > min_size:
        font = _font((font_path, size, None))
        if font.getlength(text) <= max_width:
            return font
        size -= _FIT_STEP_PX
    return _font((font_path, min_size, None))


def _tracked_text_width(font, text, tracking):
    """Total rendered advance of `text` at `font`, with `tracking` extra
    pixels between each glyph pair (none trailing). 0.0 for an empty string.
    """
    if not text:
        return 0.0
    return sum(font.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def draw_tracked_text(draw, xy, text, font, fill, tracking=0):
    """Draw `text` glyph-by-glyph with `tracking` extra pixels of advance
    between each glyph (Pillow has no native letter-spacing API). `xy` is
    the top-left origin of the first glyph; right/centre-aligned callers
    should pre-compute width with `_tracked_text_width()`. Returns the
    x-coordinate after the last glyph.
    """
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill, anchor="la")
        x += font.getlength(ch) + tracking
    return x


def _tracked_text_bbox(font, xy, text, tracking):
    """`draw.textbbox()`'s counterpart for tracked text: `ImageDraw.textbbox()`
    measures an untracked run and would under-report the width of a tracked
    one, so `_assert_within_canvas()` must be fed this instead.
    """
    x, y = xy
    width = _tracked_text_width(font, text, tracking)
    ascent, descent = font.getmetrics()
    return (x, y, x + width, y + ascent + descent)


def _role_weight_path(weight):
    """Resolve `weight` ("regular" or "bold") to the matching PT Serif
    static-weight file. Not derivable from `bg_idx` alone: the same
    palette index can back two themes with different weights (e.g.
    `IDX_BLACK` is both flat "black"/Regular and dithered "grey"/Bold).
    """
    if weight == "regular":
        return PT_SERIF_REGULAR
    if weight == "bold":
        return PT_SERIF_BOLD
    raise ValueError("unknown weight %r (expected 'regular' or 'bold')" % (weight,))


def _role_font(role_spec, weight):
    """`_font()` for an active-state role tuple, resolving weight via
    `_role_weight_path()` instead of the tuple's own (always-Bold) path.
    """
    _path, size, role_weight = role_spec
    return _font((_role_weight_path(weight), size, role_weight))


def _role_fit_text_size(role_spec, text, max_width, min_size, weight):
    """`fit_text_size()` for an active-state role tuple, resolving weight
    the same way `_role_font()` does.
    """
    _path, size, _role_weight = role_spec
    return fit_text_size(_role_weight_path(weight), size, text, max_width, min_size)


def _assert_in_safe_box(bbox, label):
    left, top, right, bottom = bbox
    sb_left, sb_top, sb_right, sb_bottom = SAFE_BOX
    assert left >= sb_left and top >= sb_top and right <= sb_right and bottom <= sb_bottom, (
        "%s bounding box %r exceeds the inviolable %dpx safe box %r"
        % (label, bbox, MARGIN, SAFE_BOX)
    )


def _assert_within_canvas(bbox, label):
    """Looser guard than _assert_in_safe_box(): only asserts the element
    stays on the 1200x1600 canvas. Used for the frame, illustrations and
    flight text, which sit inside the old 64px SAFE_BOX band.
    """
    left, top, right, bottom = bbox
    assert left >= 0 and top >= 0 and right <= WIDTH and bottom <= HEIGHT, (
        "%s bounding box %r falls outside the %dx%d canvas" % (label, bbox, WIDTH, HEIGHT)
    )


def _wrap_text(font, text, max_width):
    """Manual word-wrap (Pillow's multiline_text does not word-wrap):
    greedily pack words onto a line while the rendered width fits
    `max_width`.
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


def draw_frame(canvas, ink_idx):
    """A thin `ink_idx`-coloured rectangle outline, `FRAME_STROKE_PX` wide,
    inset `FRAME_INSET_FRAC` of the canvas width from every edge. Returns
    the frame's own bounding box.
    """
    inset = round(WIDTH * FRAME_INSET_FRAC)
    box = (inset, inset, WIDTH - inset, HEIGHT - inset)
    ImageDraw.Draw(canvas).rectangle(box, outline=ink_idx, width=FRAME_STROKE_PX)
    return box


def draw_source_fault_badge(canvas, ink_idx, weight="bold"):
    """Draw a small triangular alert glyph with `SOURCE_FAULT_TEXT`
    beside it, bottom-centre inside the frame. Uses `ink_idx` only, so it
    can never introduce an illegal palette index. Bounding box is kept
    small so `_assert_legal_palette()`'s background-dominance assertion
    still holds.

    Must be driven only by an all-providers-failed classification, never
    merely "no aircraft selected" - see `render_panel()`'s docstring.

    `weight` resolves the caption's PT Serif weight via `_role_font()`
    (Bold reads too heavy on White); defaults to `"bold"` for the
    not-theme-dependent empty-state call site.
    """
    draw = ImageDraw.Draw(canvas)
    frame_inset = round(WIDTH * FRAME_INSET_FRAC)
    frame_bottom = HEIGHT - frame_inset

    caption_font = _role_font(TOP_TAG_FONT, weight)
    glyph_size = SOURCE_FAULT_GLYPH_PX
    gap = SPACE_XS

    bottom = frame_bottom - MARGIN // 2
    top = bottom - glyph_size
    mid_y = (top + bottom) // 2

    # Measure the caption at (0, mid_y) first purely to get its rendered
    # width - the real, final draw position (below) depends on that width
    # to stay horizontally centred.
    probe_bbox = draw.textbbox((0, mid_y), SOURCE_FAULT_TEXT, font=caption_font, anchor="lm")
    caption_w = probe_bbox[2] - probe_bbox[0]

    total_w = glyph_size + gap + caption_w
    left = (WIDTH - total_w) // 2
    text_left = left + glyph_size + gap

    triangle = [
        (left + glyph_size / 2, top),
        (left, bottom),
        (left + glyph_size, bottom),
    ]

    caption_bbox = draw.textbbox((text_left, mid_y), SOURCE_FAULT_TEXT, font=caption_font, anchor="lm")
    combined_bbox = (
        left,
        min(top, caption_bbox[1]),
        caption_bbox[2],
        max(bottom, caption_bbox[3]),
    )
    _assert_within_canvas(combined_bbox, "source-fault badge")

    draw.polygon(triangle, outline=ink_idx)
    stroke_x = left + glyph_size / 2
    draw.line(
        [(stroke_x, top + glyph_size * 0.3), (stroke_x, top + glyph_size * 0.65)],
        fill=ink_idx, width=2,
    )
    # A zero-length ImageDraw.line() paints a single pixel regardless of
    # `width` - Pillow doesn't expand a degenerate segment - so the dot is
    # drawn as a small filled ellipse instead.
    dot_r = 2
    dot_y = top + glyph_size * 0.8
    draw.ellipse(
        [(stroke_x - dot_r, dot_y - dot_r), (stroke_x + dot_r, dot_y + dot_r)],
        fill=ink_idx,
    )
    draw.text((text_left, mid_y), SOURCE_FAULT_TEXT, font=caption_font, fill=ink_idx, anchor="lm")

    return combined_bbox


def draw_battery_icon(canvas, draw, ink_idx):
    """Bottom-left battery glyph: a hollow outlined body with a solid
    terminal nub and a left-aligned solid partial fill, signalling a
    fixed "low" reading, not a live gauge. Geometry derives entirely from
    the BATTERY_ICON_* constants. Box tuples are Pillow's inclusive
    corner coordinates (rendered footprint 52x23px for a nominal 51x22
    box), matching draw_frame()'s convention.

    Returns the icon's total bounding box - (64, 1514, 115, 1536).
    """
    body_top = BATTERY_ICON_BOTTOM - BATTERY_ICON_BODY_H
    body_right = BATTERY_ICON_LEFT + BATTERY_ICON_BODY_W
    body = (BATTERY_ICON_LEFT, body_top, body_right, BATTERY_ICON_BOTTOM)

    nub_top = body_top + (BATTERY_ICON_BODY_H - BATTERY_ICON_NUB_H) // 2
    nub_bottom = nub_top + BATTERY_ICON_NUB_H
    nub_right = body_right + BATTERY_ICON_NUB_W
    nub = (body_right, nub_top, nub_right, nub_bottom)

    interior_left = BATTERY_ICON_LEFT + BATTERY_ICON_STROKE_PX
    interior_top = body_top + BATTERY_ICON_STROKE_PX
    interior_right = body_right - BATTERY_ICON_STROKE_PX
    interior_bottom = BATTERY_ICON_BOTTOM - BATTERY_ICON_STROKE_PX
    fill_w = round((interior_right - interior_left) * BATTERY_ICON_FILL_FRAC)
    fill = (interior_left, interior_top, interior_left + fill_w, interior_bottom)

    total = (BATTERY_ICON_LEFT, body_top, nub_right, BATTERY_ICON_BOTTOM)
    # Looser canvas guard: this sits inside the 64px band, like the frame
    # and both illustrations.
    _assert_within_canvas(total, "battery icon")

    draw.rectangle(body, outline=ink_idx, width=BATTERY_ICON_STROKE_PX)
    draw.rectangle(nub, fill=ink_idx)
    draw.rectangle(fill, fill=ink_idx)
    return total


def draw_top_labels(
    canvas, state, ink_idx, bg_idx, weight, runway_id=device_config.DEFAULT_RUNWAY_ID, band_theme=False
):
    """Top row: state label (top-left) and runway tag (top-right), at
    `MARGIN` inset, tracked with `LABEL_TRACKING_PX`. Screen-preview-
    validated only, never checked against real Spectra 6 ink. Tag's start
    x is pre-computed from `_tracked_text_width()` (no Pillow
    `anchor="ra"` for tracked text) to end flush at `WIDTH - MARGIN`.

    `band_theme`: state label absorbs a direction word plus the tag's
    airport-code half; the tag shrinks to the runway-part half to clear
    the diagonal band. Both halves come from
    `runway_tag_text(runway_id)`'s `.partition(" · ")`.
    """
    draw = ImageDraw.Draw(canvas)
    label_font = _role_font(STATE_LABEL_FONT, weight)
    tag_font = _role_font(TOP_TAG_FONT, weight)
    full_tag = runway_tag_text(runway_id)

    if band_theme:
        airport_code, _sep, runway_part = full_tag.partition(" · ")
        label_text = "%s %s %s" % (STATE_LABEL_TEXT[state], _BAND_TOP_LABEL_DIRECTION[state], airport_code)
        tag_text = runway_part
    else:
        label_text = STATE_LABEL_TEXT[state]
        tag_text = full_tag

    # Looser guard, not the strict safe-box: glyph metrics can carry a
    # 1-2px negative bearing at these small sizes. Uses _tracked_text_bbox(),
    # not draw.textbbox(), which would under-report a tracked run's width.
    label_bbox = _tracked_text_bbox(label_font, (MARGIN, MARGIN), label_text, LABEL_TRACKING_PX)
    _assert_within_canvas(label_bbox, "state label")
    draw_tracked_text(draw, (MARGIN, MARGIN), label_text, label_font, ink_idx, tracking=LABEL_TRACKING_PX)

    tag_width = _tracked_text_width(tag_font, tag_text, LABEL_TRACKING_PX)
    tag_x = WIDTH - MARGIN - tag_width
    tag_bbox = _tracked_text_bbox(tag_font, (tag_x, MARGIN), tag_text, LABEL_TRACKING_PX)
    _assert_within_canvas(tag_bbox, "top-right tag")
    draw_tracked_text(draw, (tag_x, MARGIN), tag_text, tag_font, ink_idx, tracking=LABEL_TRACKING_PX)


def _illustration_over_pixel_cap(path):
    """`True` when `path`'s PNG header declares more than
    `illustrations.ILLUSTRATION_MAX_PIXELS` pixels, or is unreadable.
    Checks only the header (`Image.open()` is lazy), never triggering a
    full decode; checks only pixel count, not the other vendor-time
    quality rules, so a live poll cycle never drops legitimate art. Never
    raises.
    """
    try:
        with Image.open(path) as img:
            width, height = img.size
            return (width * height) > illustrations.ILLUSTRATION_MAX_PIXELS
    except Exception:
        return True


def _load_illustration_safely(path, target_w):
    """Resized RGBA image loaded from `path`, degrading through `path`
    then `illustrations.generic_fallback_path()`, then `None`. Never
    raises, for any input including `None`.
    """
    candidates = []
    for candidate in (path, illustrations.generic_fallback_path()):
        if not candidate or not os.path.isfile(candidate) or candidate in candidates:
            continue
        candidates.append(candidate)

    for candidate in candidates:
        if _illustration_over_pixel_cap(candidate):
            try:
                with Image.open(candidate) as img:
                    pixel_count = img.size[0] * img.size[1]
            except Exception as exc:
                print(
                    "render: skipping illustration %s - header unreadable (%s)"
                    % (candidate, type(exc).__name__),
                    file=sys.stderr,
                )
            else:
                print(
                    "render: skipping illustration %s - %d pixels exceeds the %d-pixel cap"
                    % (candidate, pixel_count, illustrations.ILLUSTRATION_MAX_PIXELS),
                    file=sys.stderr,
                )
            continue
        try:
            return _resize_illustration(candidate, target_w)
        except Exception as exc:
            print(
                "render: skipping illustration %s - %s" % (candidate, type(exc).__name__),
                file=sys.stderr,
            )
            continue
    return None


_illustration_cache = {}
# Bounded so the long-lived companion process cannot grow it without
# limit; past the cap it is flushed and refilled.
_ILLUSTRATION_CACHE_MAX_ENTRIES = 128


def _resize_illustration(path, target_w):
    """Load a vendored per-airline illustration PNG and resize it to
    `target_w` px wide, preserving aspect ratio. Returns a fresh "RGBA"
    image, memoized on (path, mtime_ns, size, target_w).
    """
    try:
        st = os.stat(path)
        cache_key = (path, st.st_mtime_ns, st.st_size, target_w)
    except OSError:
        cache_key = None

    if cache_key is not None:
        cached = _illustration_cache.get(cache_key)
        if cached is not None:
            return cached.copy()

    with Image.open(path) as source:
        rgba = source.convert("RGBA")
        src_w, src_h = rgba.size
        target_h = max(1, round(target_w * src_h / src_w))
        resized = rgba.resize((target_w, target_h), Image.LANCZOS)

    if cache_key is not None:
        if len(_illustration_cache) >= _ILLUSTRATION_CACHE_MAX_ENTRIES:
            _illustration_cache.clear()
        _illustration_cache[cache_key] = resized
    return resized.copy()


ILLUSTRATION_ALPHA_THRESHOLD = 127
"""Alpha strictly greater than this is painted; named so
`_threshold_alpha()` and every opaque-bbox measurement use one number."""


def _threshold_alpha(resized_rgba):
    """`resized_rgba`'s alpha channel hard-thresholded to strictly binary
    (0 or 255) at `ILLUSTRATION_ALPHA_THRESHOLD`. A soft/gradient mask
    would blend palette INDEX INTEGERS during paste(), producing illegal
    in-between indices.
    """
    return resized_rgba.getchannel("A").point(
        lambda p: 255 if p > ILLUSTRATION_ALPHA_THRESHOLD else 0
    )


def _opaque_bbox(resized_rgba):
    """Tight bounding box of the pixels `draw_illustration()` will
    actually paint, in image-local coordinates. Not `Image.getbbox()` on
    the raw alpha channel: that counts the soft drop-shadow band
    (alpha 1..127) the paste threshold erases. Returns `None` when
    nothing would be painted.
    """
    return _threshold_alpha(resized_rgba).getbbox()


class IllustrationPlacement(tuple):
    """`draw_illustration()`'s return value: two absolute canvas bounding
    boxes, deliberately not the same box.

    - `rect`: the full placement rectangle of the resized source PNG,
      including transparent padding. Use for canvas-containment guards.
    - `content`: the tight bbox of pixels actually painted (see
      `_opaque_bbox()`). Use for anything that must line up with the
      aircraft as seen, above all flight-text vertical anchors. Falls
      back to `rect` when nothing is painted.

    Subclasses `tuple` as `(rect, content)` so it unpacks naturally.
    """

    __slots__ = ()

    def __new__(cls, rect, content):
        return super().__new__(cls, (rect, content))

    @property
    def rect(self):
        return self[0]

    @property
    def content(self):
        return self[1]

    def __repr__(self):
        return "IllustrationPlacement(rect=%r, content=%r)" % (self.rect, self.content)


def _left_for_centered_content(resized_rgba, center_x):
    """Paste `left` that puts the illustration's PAINTED horizontal
    midpoint on `center_x`. Not `(WIDTH - w) // 2`: horizontal transparent
    padding is asymmetric per file, which would displace the visible
    aircraft from centre. Falls back to the full rectangle when nothing
    would be painted.
    """
    local = _opaque_bbox(resized_rgba)
    if local is None:
        return round(center_x - resized_rgba.size[0] / 2)
    return round(center_x - (local[0] + local[2]) / 2)


def _left_for_right_aligned_content(resized_rgba, right_x):
    """Paste `left` that puts the illustration's PAINTED right edge on
    `right_x`, so two illustrations share one visible edge regardless of
    differing right padding. Falls back to the full rectangle.
    """
    local = _opaque_bbox(resized_rgba)
    if local is None:
        return round(right_x - resized_rgba.size[0])
    return round(right_x - local[2])


def _top_for_centered_content(resized_rgba, center_y):
    """Paste `top` that puts the illustration's PAINTED vertical midpoint
    on `center_y`. Vertical padding is asymmetric (drop-shadow band makes
    bottom exceed top), so centring the source rectangle would push the
    aircraft high. Falls back to the full rectangle.
    """
    local = _opaque_bbox(resized_rgba)
    if local is None:
        return round(center_y - resized_rgba.size[1] / 2)
    return round(center_y - (local[1] + local[3]) / 2)


def draw_illustration(canvas, resized_rgba, left, top):
    """Composite a resized illustration onto `canvas` at (`left`, `top`),
    dithered to the panel's 6-color palette. Alpha is hard-thresholded to
    strictly binary before paste() (`_threshold_alpha()`). Returns an
    `IllustrationPlacement` (see that class's docstring).
    """
    w, h = resized_rgba.size
    rgb = resized_rgba.convert("RGB")
    quantized = dither.dither_to_full_panel_palette(rgb)
    alpha = _threshold_alpha(resized_rgba)
    canvas.paste(quantized, (int(left), int(top)), mask=alpha)

    rect = (left, top, left + w, top + h)
    local = _opaque_bbox(resized_rgba)
    if local is None:
        # Nothing was painted - there is no visual content to anchor to, so
        # the full rectangle is the only meaningful answer. Never raises.
        content = rect
    else:
        content = (left + local[0], top + local[1], left + local[2], top + local[3])
    return IllustrationPlacement(rect, content)


def _flight_line1_text(flight, state, route):
    """Four-tier content ladder for the main line, evaluated in order:

    - **Tier 1**: identifier + city known -> `"{identifier} to|from {city}"`.
    - **Tier 2**: city only -> `"To|From {city}"` (TITLE-case, starts the line).
    - **Tier 3**: airline known, no city/identifier -> `""` (line 1
      omitted; callers must promote line 2 into its slot).
    - **Tier 4**: nothing usable -> `"Unknown flight"`.

    The raw ADS-B callsign is never reachable at any tier. Never raises;
    a malformed `route` or a hostile `route.get()` degrades a tier
    rather than propagating.
    """
    fallback_word = "Unknown flight"
    if not isinstance(route, dict):
        return fallback_word

    try:
        identifier_raw = route.get("callsign_iata")
    except Exception:
        identifier_raw = None
    identifier = identifier_raw.strip() if isinstance(identifier_raw, str) and identifier_raw.strip() else None

    try:
        city = enrich.city_for_state(route, state)
    except Exception:
        city = None
    if not isinstance(city, str) or not city.strip():
        city = None

    if identifier and city:
        direction_lower = "to" if state == runway_config.STATE_DEPARTING else "from"
        return "%s %s %s" % (identifier, direction_lower, city)
    if city:
        direction_title = "To" if state == runway_config.STATE_DEPARTING else "From"
        return "%s %s" % (direction_title, city)

    try:
        airline_name = route.get("airline_name")
    except Exception:
        airline_name = None
    if isinstance(airline_name, str) and airline_name.strip():
        return ""

    return fallback_word


# Friendly labels for ICAO type designators, so `{airline} · {type}` shows
# a legible label rather than a raw code. A designator absent here
# renders the airline name alone (_flight_line2_text()'s fallback).
_TYPE_DISPLAY_LABELS = {
    # A320 family - familiar designations, neo variants named.
    "A318": "A318", "A319": "A319", "A320": "A320", "A321": "A321",
    "A20N": "A320neo", "A21N": "A321neo",
    # B737 family - commercial model numbers, MAX variants named.
    "B731": "737-100", "B732": "737-200", "B733": "737-300", "B734": "737-400",
    "B735": "737-500", "B736": "737-600", "B737": "737-700", "B738": "737-800",
    "B739": "737-900", "B37M": "737 MAX 7", "B38M": "737 MAX 8",
    "B39M": "737 MAX 9", "B3XM": "737 MAX 10",
    # ATR turboprops.
    "AT43": "ATR 42", "AT44": "ATR 42-500", "AT45": "ATR 42", "AT46": "ATR 42-600",
    "AT72": "ATR 72", "AT73": "ATR 72", "AT75": "ATR 72-500", "AT76": "ATR 72-600",
    # Beechcraft 1900D.
    "BE9L": "Beechcraft 1900D",
    # Embraer E-Jet family - keep the E1xx designations.
    "E135": "E135", "E145": "E145", "E170": "E170", "E75L": "E175",
    "E75S": "E175", "E190": "E190", "E195": "E195", "E290": "E190-E2",
    "E295": "E195-E2",
    # A330 family.
    "A332": "A330-200", "A333": "A330-300", "A339": "A330-900neo",
    # A350 family.
    "A359": "A350-900", "A35K": "A350-1000",
}

# Presentation-only display alias. `enrich.correct_airline_name()` now
# corrects this carrier's name upstream, so this is a defensive no-op for
# any hand-built route dict that still carries the literal stale name.
_AIRLINE_DISPLAY_ALIASES = {
    "CCM Airlines": "Air Corsica",
}


def display_airline_name(airline_name):
    """Presentation-only display name: the aliased brand name when one
    exists, else `airline_name` unchanged. Never raises.
    """
    if not isinstance(airline_name, str) or not airline_name:
        return airline_name
    return _AIRLINE_DISPLAY_ALIASES.get(airline_name, airline_name)


def _flight_line2_text(route, aircraft_type=None):
    """`"{airline} · {friendly type label}"`, via `display_airline_name()`
    and `_TYPE_DISPLAY_LABELS`. Falls back to the display name alone when
    `aircraft_type` has no friendly label, and to `ROUTE_FALLBACK_TEXT`
    only when neither adsbdb nor the callsign-prefix fallback produced an
    airline name. Never raises.
    """
    try:
        airline_name = route.get("airline_name") if isinstance(route, dict) else None
    except Exception:
        airline_name = None
    if not airline_name:
        return ROUTE_FALLBACK_TEXT
    display_name = display_airline_name(airline_name)
    type_key = aircraft_type.strip().upper() if isinstance(aircraft_type, str) and aircraft_type else None
    label = _TYPE_DISPLAY_LABELS.get(type_key) if type_key else None
    if label:
        return "%s · %s" % (display_name, label)
    return "%s" % (display_name,)


# --- Band-only main-card text roles ---------------------------------
# Declared weight ("700"/"400" in the tuple) is never read directly -
# `_role_font()` resolves the real weight from the active theme's `weight`
# field, same mechanism every other active-state role already uses.
BAND_MAIN_NUMBER_FONT = (PT_SERIF_BOLD, 56, 700)
BAND_MAIN_ROUTE_FONT = (PT_SERIF_REGULAR, 22, 400)
BAND_MAIN_AIRLINE_FONT = (PT_SERIF_REGULAR, 20, 400)
BAND_MAIN_DASH_W = 48
BAND_MAIN_DASH_GAP = 10

# Shrink-to-fit floors, roughly the same ~70% ratio MAIN_LINE1_FONT/
# MAIN_LINE2_FONT use, so a long airline/city name never overflows.
BAND_MAIN_NUMBER_MIN_SIZE = 40
BAND_MAIN_ROUTE_MIN_SIZE = 16
BAND_MAIN_AIRLINE_MIN_SIZE = 14


def _role_fit_tracked_text_size(role_spec, text, tracking, max_width, min_size, weight):
    """`_role_fit_text_size()`'s step-down loop, measuring width via
    `_tracked_text_width()` instead of `font.getlength()`, since tracking
    adds pixels `fit_text_size()` alone would miss.
    """
    font_path, size, _role_weight = role_spec
    resolved_path = _role_weight_path(weight)
    while size > min_size:
        font = _font((resolved_path, size, None))
        if _tracked_text_width(font, text, tracking) <= max_width:
            return font
        size -= _FIT_STEP_PX
    return _font((resolved_path, min_size, None))


def draw_main_text_block(canvas, flight, state, route, main_placement, ink_idx, bg_idx, weight, band_idx=None):
    """Main flight text: two centred lines starting `MAIN_TEXT_GAP_PX`
    below the illustration's OPAQUE bottom edge (`.content`, not `.rect`,
    which would vary the gap by 37-174px per file's own padding).

    When line 1 is empty, line 2 is promoted into its slot and the first
    return slot is `None`. `weight` selects PT Serif weight (not
    derivable from `bg_idx` alone; see `_role_weight_path()`). `band_idx`
    `None` draws the plain layout; a band theme instead draws a
    three-tier hierarchy (identifier / dash rule / route line /
    airline·type line) centred inside the band.

    Returns (line1_bbox, line2_bbox).
    """
    if band_idx is None:
        draw = ImageDraw.Draw(canvas)
        center_x = WIDTH // 2
        safe_width = SAFE_BOX[2] - SAFE_BOX[0]

        line1_text = _flight_line1_text(flight, state, route)
        line2_text = _flight_line2_text(route, flight.get("aircraft_type"))

        top_y = main_placement.content[3] + MAIN_TEXT_GAP_PX

        if line1_text:
            line1_font = _role_fit_text_size(MAIN_LINE1_FONT, line1_text, safe_width, MAIN_LINE1_MIN_SIZE, weight)
            line1_bbox = draw.textbbox((center_x, top_y), line1_text, font=line1_font, anchor="ma")
            _assert_within_canvas(line1_bbox, "main flight text line 1")
            draw.text((center_x, top_y), line1_text, font=line1_font, fill=ink_idx, anchor="ma")
            line2_top = line1_bbox[3] + MAIN_LINE_GAP_PX
        else:
            line1_bbox = None
            line2_top = top_y

        line2_font = _role_fit_text_size(MAIN_LINE2_FONT, line2_text, safe_width, MAIN_LINE2_MIN_SIZE, weight)
        line2_bbox = draw.textbbox((center_x, line2_top), line2_text, font=line2_font, anchor="ma")
        _assert_within_canvas(line2_bbox, "main flight text line 2")
        draw.text((center_x, line2_top), line2_text, font=line2_font, fill=ink_idx, anchor="ma")

        return line1_bbox, line2_bbox
    else:
        draw = ImageDraw.Draw(canvas)
        # White-ink override: unconditional for every band theme, since
        # black is illegible on real Spectra 6 ink regardless of band colour.
        effective_ink = IDX_WHITE

        line1_full = _flight_line1_text(flight, state, route)
        line2_full = _flight_line2_text(route, flight.get("aircraft_type"))

        identifier_raw = route.get("callsign_iata") if isinstance(route, dict) else None
        identifier = identifier_raw.strip() if isinstance(identifier_raw, str) and identifier_raw.strip() else None

        # Classify from the real content ladder's own output, never a
        # separate re-derivation.
        if line1_full == "":
            number_text, tracked_text, plain_text = None, None, line2_full
        elif identifier and line1_full.startswith(identifier + " "):
            number_text = identifier
            tracked_text = line1_full[len(identifier) + 1:].upper()
            plain_text = line2_full
        else:
            number_text, tracked_text, plain_text = None, line1_full.upper(), line2_full

        # First-pass fonts, fit against SAFE_BOX's width to get an
        # approximate block height for the midpoint calc below only.
        band_safe_width = SAFE_BOX[2] - SAFE_BOX[0]
        num_font = _role_fit_text_size(BAND_MAIN_NUMBER_FONT, number_text or "", band_safe_width, BAND_MAIN_NUMBER_MIN_SIZE, weight)
        route_font = _role_fit_tracked_text_size(BAND_MAIN_ROUTE_FONT, tracked_text or "", LABEL_TRACKING_PX, band_safe_width, BAND_MAIN_ROUTE_MIN_SIZE, weight)
        airline_font = _role_fit_text_size(BAND_MAIN_AIRLINE_FONT, plain_text, band_safe_width, BAND_MAIN_AIRLINE_MIN_SIZE, weight)

        # center_x is computed ONCE at the block's MIDPOINT and reused for
        # every line (see _band_center_x()) - anchoring at the block's TOP
        # instead would leave lower lines visibly off-centre, since the
        # band's centreline drifts left as y increases.
        y = main_placement.content[3] + MAIN_TEXT_GAP_PX
        measure_y = y
        if number_text:
            num_bbox_m = draw.textbbox((0, measure_y), number_text, font=num_font, anchor="ma")
            dash_y_m = num_bbox_m[3] + BAND_MAIN_DASH_GAP
            measure_y = dash_y_m + BAND_MAIN_DASH_GAP + 4
        if tracked_text:
            tracked_bbox_m = _tracked_text_bbox(route_font, (0, measure_y), tracked_text, LABEL_TRACKING_PX)
            measure_y = tracked_bbox_m[3] + 12
        plain_bbox_m = draw.textbbox((0, measure_y), plain_text, font=airline_font, anchor="ma")
        block_bottom_y = plain_bbox_m[3]
        center_x = _band_center_x((y + block_bottom_y) / 2, WIDTH)
        first_bbox = None

        # Re-fit each line against the band's own width at its actual y
        # (not SAFE_BOX's width): white ink is only visible ON the band,
        # so an overhang lands on White and silently vanishes.
        if number_text:
            band_left, band_right = _band_edges(y, WIDTH)
            num_max_w = 2 * min(center_x - band_left, band_right - center_x)
            num_font = _role_fit_text_size(BAND_MAIN_NUMBER_FONT, number_text, num_max_w, BAND_MAIN_NUMBER_MIN_SIZE, weight)
            num_bbox = draw.textbbox((center_x, y), number_text, font=num_font, anchor="ma")
            _assert_within_canvas(num_bbox, "band main flight number")
            draw.text((center_x, y), number_text, font=num_font, fill=effective_ink, anchor="ma")
            first_bbox = num_bbox
            dash_y = num_bbox[3] + BAND_MAIN_DASH_GAP
            draw.line(
                [(center_x - BAND_MAIN_DASH_W / 2, dash_y), (center_x + BAND_MAIN_DASH_W / 2, dash_y)],
                fill=effective_ink, width=2,
            )
            y = dash_y + BAND_MAIN_DASH_GAP + 4

        if tracked_text:
            band_left, band_right = _band_edges(y, WIDTH)
            tracked_max_w = 2 * min(center_x - band_left, band_right - center_x)
            route_font = _role_fit_tracked_text_size(
                BAND_MAIN_ROUTE_FONT, tracked_text, LABEL_TRACKING_PX, tracked_max_w, BAND_MAIN_ROUTE_MIN_SIZE, weight
            )
            tracked_w = _tracked_text_width(route_font, tracked_text, LABEL_TRACKING_PX)
            tracked_x = center_x - tracked_w / 2
            tracked_bbox = _tracked_text_bbox(route_font, (tracked_x, y), tracked_text, LABEL_TRACKING_PX)
            _assert_within_canvas(tracked_bbox, "band main flight tracked route line")
            draw_tracked_text(draw, (tracked_x, y), tracked_text, route_font, effective_ink, tracking=LABEL_TRACKING_PX)
            if first_bbox is None:
                first_bbox = tracked_bbox
            y = tracked_bbox[3] + 12

        band_left, band_right = _band_edges(y, WIDTH)
        airline_max_w = 2 * min(center_x - band_left, band_right - center_x)
        airline_font = _role_fit_text_size(BAND_MAIN_AIRLINE_FONT, plain_text, airline_max_w, BAND_MAIN_AIRLINE_MIN_SIZE, weight)
        plain_bbox = draw.textbbox((center_x, y), plain_text, font=airline_font, anchor="ma")
        _assert_within_canvas(plain_bbox, "band main flight airline·type line")
        draw.text((center_x, y), plain_text, font=airline_font, fill=effective_ink, anchor="ma")
        if first_bbox is None:
            first_bbox = plain_bbox

        return first_bbox, plain_bbox


# --- Band-only previous-card text roles ---------------------------------
# The same right-aligned three-tier hierarchy as the main card, at the
# previous card's existing ~57% scale.
BAND_PREV_NUMBER_FONT = (PT_SERIF_BOLD, 32, 700)
BAND_PREV_ROUTE_FONT = (PT_SERIF_REGULAR, 16, 400)
BAND_PREV_AIRLINE_FONT = (PT_SERIF_REGULAR, 14, 400)
BAND_PREV_DASH_W = 16
BAND_PREV_DASH_GAP = 6

# Same real-glass long-name finding as BAND_MAIN_*_MIN_SIZE above - the
# previous card's band roles were equally fixed-size with no
# shrink-to-fit.
BAND_PREV_NUMBER_MIN_SIZE = 23
BAND_PREV_ROUTE_MIN_SIZE = 12
BAND_PREV_AIRLINE_MIN_SIZE = 10


def draw_previous_text_block(canvas, flight, state, route, prev_placement, ink_idx, bg_idx, weight, band_idx=None):
    """Previous flight text: two right-aligned lines, positioned from
    `prev_placement.content` (not `.rect`) like `draw_main_text_block()`.
    Right edge is `.content[2]` minus `PREVIOUS_TEXT_LEFT_OFFSET_PX`, so
    the main/previous aircraft and this text share one reference line.
    Line 2 sits below line 1's TOP, not bottom; when line 1 is empty,
    line 2 is promoted and the first return slot is `None`.

    `band_idx` `None` draws the plain layout; a band theme draws a
    right-aligned hierarchy in the caller's plain `ink_idx` (no ink
    override here, unlike the main card).

    Returns (line1_bbox, line2_bbox).
    """
    if band_idx is None:
        draw = ImageDraw.Draw(canvas)
        right_x = prev_placement.content[2] - PREVIOUS_TEXT_LEFT_OFFSET_PX
        available_width = right_x - SAFE_BOX[0]

        line1_text = _flight_line1_text(flight, state, route)
        line2_text = _flight_line2_text(route, (flight or {}).get("aircraft_type"))

        top_y = prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX

        if line1_text:
            line1_font = _role_fit_text_size(PREVIOUS_LINE1_FONT, line1_text, available_width, PREVIOUS_LINE1_MIN_SIZE, weight)
            line1_bbox = draw.textbbox((right_x, top_y), line1_text, font=line1_font, anchor="ra")
            _assert_within_canvas(line1_bbox, "previous flight text line 1")
            draw.text((right_x, top_y), line1_text, font=line1_font, fill=ink_idx, anchor="ra")
            line2_top = line1_bbox[1] + PREVIOUS_LINE_GAP_PX
        else:
            line1_bbox = None
            line2_top = top_y

        line2_font = _role_fit_text_size(PREVIOUS_LINE2_FONT, line2_text, available_width, PREVIOUS_LINE2_MIN_SIZE, weight)
        line2_bbox = draw.textbbox((right_x, line2_top), line2_text, font=line2_font, anchor="ra")
        _assert_within_canvas(line2_bbox, "previous flight text line 2")
        draw.text((right_x, line2_top), line2_text, font=line2_font, fill=ink_idx, anchor="ra")

        return line1_bbox, line2_bbox
    else:
        draw = ImageDraw.Draw(canvas)
        right_x = prev_placement.content[2] - PREVIOUS_TEXT_LEFT_OFFSET_PX

        line1_full = _flight_line1_text(flight, state, route)
        line2_full = _flight_line2_text(route, (flight or {}).get("aircraft_type"))

        identifier_raw = route.get("callsign_iata") if isinstance(route, dict) else None
        identifier = identifier_raw.strip() if isinstance(identifier_raw, str) and identifier_raw.strip() else None

        if line1_full == "":
            number_text, tracked_text, plain_text = None, None, line2_full
        elif identifier and line1_full.startswith(identifier + " "):
            number_text = identifier
            tracked_text = line1_full[len(identifier) + 1:].upper()
            plain_text = line2_full
        else:
            number_text, tracked_text, plain_text = None, line1_full.upper(), line2_full

        band_available_width = right_x - SAFE_BOX[0]
        num_font = _role_fit_text_size(BAND_PREV_NUMBER_FONT, number_text or "", band_available_width, BAND_PREV_NUMBER_MIN_SIZE, weight)
        route_font = _role_fit_tracked_text_size(BAND_PREV_ROUTE_FONT, tracked_text or "", LABEL_TRACKING_PX, band_available_width, BAND_PREV_ROUTE_MIN_SIZE, weight)
        airline_font = _role_fit_text_size(BAND_PREV_AIRLINE_FONT, plain_text, band_available_width, BAND_PREV_AIRLINE_MIN_SIZE, weight)

        y = prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX
        first_bbox = None

        if number_text:
            num_bbox = draw.textbbox((right_x, y), number_text, font=num_font, anchor="ra")
            _assert_within_canvas(num_bbox, "band previous flight number")
            draw.text((right_x, y), number_text, font=num_font, fill=ink_idx, anchor="ra")
            first_bbox = num_bbox
            dash_y = num_bbox[3] + BAND_PREV_DASH_GAP
            draw.line([(right_x - BAND_PREV_DASH_W, dash_y), (right_x, dash_y)], fill=ink_idx, width=2)
            y = dash_y + BAND_PREV_DASH_GAP + 3

        if tracked_text:
            tracked_w = _tracked_text_width(route_font, tracked_text, LABEL_TRACKING_PX)
            tracked_x = right_x - tracked_w
            tracked_bbox = _tracked_text_bbox(route_font, (tracked_x, y), tracked_text, LABEL_TRACKING_PX)
            _assert_within_canvas(tracked_bbox, "band previous flight tracked route line")
            draw_tracked_text(draw, (tracked_x, y), tracked_text, route_font, ink_idx, tracking=LABEL_TRACKING_PX)
            if first_bbox is None:
                first_bbox = tracked_bbox
            y = tracked_bbox[3] + 8

        plain_bbox = draw.textbbox((right_x, y), plain_text, font=airline_font, anchor="ra")
        _assert_within_canvas(plain_bbox, "band previous flight airline·type line")
        draw.text((right_x, y), plain_text, font=airline_font, fill=ink_idx, anchor="ra")
        if first_bbox is None:
            first_bbox = plain_bbox

        return first_bbox, plain_bbox


def _build_empty_canvas(runway_id=device_config.DEFAULT_RUNWAY_ID, source_fault=False, battery_low=False):
    """Build the empty-state canvas ("Watching Runway 3" by default; the
    heading follows `runway_id`). Uses the shared hold composition
    (`_build_hold_canvas()`, white variant), the one white hold screen -
    the frame is working here, not resting.

    `battery_low`/`source_fault`: independent device/server-health
    indicators, both drawn in EMPTY_INK when True.
    """
    # Heading is upper-cased at draw time only; EMPTY_HEADING_TEXT and
    # empty_heading_text() stay untouched.
    return _build_hold_canvas(
        draw_runway_icon,
        RUNWAY_ICON_HEIGHT_PX,
        empty_heading_text(runway_id).upper(),
        EMPTY_BODY_LINES,
        IDX_WHITE,
        EMPTY_INK,
        False,
        source_fault=source_fault,
        battery_low=battery_low,
    )


def _build_quiet_hours_canvas(quiet_hours_until=None, source_fault=False, battery_low=False):
    """Build the scheduled-quiet-hours canvas via the shared dimmed hold
    composition (crescent mark, white ink on a dithered dark field) -
    always White/Black regardless of the configured theme.

    `quiet_hours_until` is the "HH:MM" end-time string from
    `device_config.seconds_until_quiet_hours_end()`; when missing, empty
    or non-string, the body line is omitted rather than showing
    "Back at None".

    `battery_low`/`source_fault`: as `_build_empty_canvas()`, drawn in
    DIMMED_INK.
    """
    if isinstance(quiet_hours_until, str) and quiet_hours_until:
        sentences = (QUIET_HOURS_BODY_TEMPLATE % quiet_hours_until,)
    else:
        sentences = ()
    return _build_dimmed_hold_canvas(
        draw_moon_icon,
        MOON_ICON_DIAMETER_PX,
        QUIET_HOURS_HEADING_TEXT,
        sentences,
        source_fault=source_fault,
        battery_low=battery_low,
    )


def _build_display_off_canvas(source_fault=False, battery_low=False):
    """Build the remote display-off canvas via the shared dimmed hold
    composition (power-ring mark), always White/Black. Unlike the
    quiet-hours screen, `DISPLAY_OFF_BODY_TEXT` is a fixed constant with
    no interpolated value, so the body is always drawn.

    `battery_low`/`source_fault`: as `_build_empty_canvas()`, drawn in
    DIMMED_INK.
    """
    return _build_dimmed_hold_canvas(
        draw_power_icon,
        POWER_ICON_BAR_RISE_PX + POWER_ICON_DIAMETER_PX,
        DISPLAY_OFF_HEADING_TEXT,
        DISPLAY_OFF_BODY_LINES,
        source_fault=source_fault,
        battery_low=battery_low,
    )


def _build_battery_empty_canvas():
    """Build the BATTERY EMPTY hold canvas via the shared
    `_build_dimmed_hold_canvas()` composition. poll_loop.py latches this
    state once pack voltage crosses BATTERY_CRITICAL_MV.

    Accepts no `theme_id`/`battery_low`/`source_fault`: the image's bytes
    (and sha256 hash) must stay constant for the whole parked episode, so
    every hourly byos check-in is a hash-skip, never a redraw.
    """
    return _build_dimmed_hold_canvas(
        draw_empty_battery_icon,
        EMPTY_BATTERY_ICON_HEIGHT_PX,
        BATTERY_EMPTY_HEADING_TEXT,
        BATTERY_EMPTY_BODY_LINES,
    )


def _build_no_connection_canvas(flat=False):
    """Build the NO CONNECTION hold canvas via `_build_hold_canvas()`.
    Never reached by `build_canvas()`: the device draws this screen
    entirely on its own in firmware, from a generated ink mask
    (`firmware/tools/gen_fault_screen.py` ->
    `firmware/main/fault_screen_mask.h`); this function is that mask's
    one source of truth on the Python side.

    `flat=True` (used only by `gen_fault_screen.py`) returns a flat
    two-colour canvas with no dither noise, so its ink-mask extraction
    (`pixel == IDX_WHITE`) is exact.
    """
    return _build_hold_canvas(
        draw_alert_icon,
        ALERT_ICON_HEIGHT_PX,
        NO_CONNECTION_HEADING_TEXT,
        NO_CONNECTION_BODY_LINES,
        DIMMED_FIELD_IDX,
        DIMMED_INK,
        not flat,
    )


# --- Display-off power glyph --------------------------------------------
# Drawn from primitives, no vendored asset. A power mark, not a moon or
# "Zzz" (QUIET HOURS' own register), in white ink with an 8px Bold-class
# stroke safe against the dither.
POWER_ICON_DIAMETER_PX = 76
POWER_ICON_STROKE_PX = 8
POWER_ICON_GAP_DEGREES = 64  # the ring's opening, centred on 12 o'clock
POWER_ICON_BAR_RISE_PX = 10  # how far the bar stands above the ring
POWER_ICON_BAR_DROP_PX = 34  # how far it reaches down into the ring


def draw_power_icon(draw, center_x, top_y, ink_idx):
    """Draw the power mark centred on `center_x`, topmost pixel at
    `top_y`; returns the glyph's total height. `ImageDraw.arc()`'s angles
    run clockwise from 3 o'clock (12 o'clock = 270); drawing the long way
    round from `270 + half_gap` to `270 - half_gap` leaves the opening at
    the top.
    """
    radius = POWER_ICON_DIAMETER_PX // 2
    ring_top = top_y + POWER_ICON_BAR_RISE_PX
    ring_box = (
        center_x - radius,
        ring_top,
        center_x + radius,
        ring_top + POWER_ICON_DIAMETER_PX,
    )
    half_gap = POWER_ICON_GAP_DEGREES / 2.0
    draw.arc(ring_box, 270 + half_gap, 270 - half_gap, fill=ink_idx, width=POWER_ICON_STROKE_PX)

    bar_left = center_x - POWER_ICON_STROKE_PX // 2
    draw.rectangle(
        (bar_left, top_y, bar_left + POWER_ICON_STROKE_PX - 1, ring_top + POWER_ICON_BAR_DROP_PX),
        fill=ink_idx,
    )
    return POWER_ICON_BAR_RISE_PX + POWER_ICON_DIAMETER_PX


# --- Quiet-hours crescent glyph ------------------------------------------
# Same 76px footprint and Bold-class white as the power ring, differing
# only by mark. Filled, not outlined: an outline's bite would paint a
# solid patch over the dithered field.
MOON_ICON_DIAMETER_PX = 76
MOON_ICON_BITE_DIAMETER_PX = 68
MOON_ICON_BITE_OFFSET_PX = 20  # the bite's centre, right of the disc's centre
MOON_ICON_SAMPLES = 180


def draw_moon_icon(draw, center_x, top_y, ink_idx):
    """Draw a filled crescent (points inside the main disc, outside the
    bite disc) centred on `center_x`, topmost pixel at `top_y`. Returns
    the glyph's height.
    """
    radius = MOON_ICON_DIAMETER_PX / 2.0
    bite_radius = MOON_ICON_BITE_DIAMETER_PX / 2.0
    cx = float(center_x)
    cy = top_y + radius
    bx = cx + MOON_ICON_BITE_OFFSET_PX

    outer = []
    for i in range(MOON_ICON_SAMPLES):
        a = 2.0 * math.pi * i / MOON_ICON_SAMPLES
        px, py = cx + radius * math.cos(a), cy + radius * math.sin(a)
        if math.hypot(px - bx, py - cy) >= bite_radius:
            outer.append((a, (px, py)))
    inner = []
    for i in range(MOON_ICON_SAMPLES):
        a = 2.0 * math.pi * i / MOON_ICON_SAMPLES
        px, py = bx + bite_radius * math.cos(a), cy + bite_radius * math.sin(a)
        if math.hypot(px - cx, py - cy) <= radius:
            inner.append((a, (px, py)))

    # Sampled angles straddle pi; unwrap so the run is contiguous.
    def _unwrap(run):
        run = sorted(run, key=lambda t: t[0])
        gap_at = max(range(1, len(run)), key=lambda k: run[k][0] - run[k - 1][0], default=0)
        if gap_at and run[gap_at][0] - run[gap_at - 1][0] > math.pi:
            run = run[gap_at:] + run[:gap_at]
        return [p for _a, p in run]

    points = _unwrap(outer) + list(reversed(_unwrap(inner)))
    draw.polygon(points, fill=ink_idx)
    return MOON_ICON_DIAMETER_PX


# --- Battery-empty glyph --------------------------------------------------
# Upright hollow battery, at the family's shared 76px height and the
# runway strip's 48px width. Stroke-only outline, hollow interior so the
# dithered field shows through - an empty battery has nothing inside to show.
EMPTY_BATTERY_ICON_HEIGHT_PX = 76
EMPTY_BATTERY_ICON_WIDTH_PX = 48
EMPTY_BATTERY_NUB_W_PX = 20
EMPTY_BATTERY_NUB_H_PX = 8
EMPTY_BATTERY_ICON_STROKE_PX = POWER_ICON_STROKE_PX  # same Bold-class 8px stroke as the ring


def draw_empty_battery_icon(draw, center_x, top_y, ink_idx):
    """Draw the battery-empty mark (solid terminal nub, then a
    stroke-only outlined body below it, hollow) centred on `center_x`,
    topmost pixel at `top_y`. Uses the inclusive-corner `right - 1` /
    `bottom - 1` convention so the rendered footprint matches the nominal
    width/height exactly (contrast draw_battery_icon()'s one-pixel-wider
    convention). Returns the glyph's total height.
    """
    nub_left = center_x - EMPTY_BATTERY_NUB_W_PX // 2
    nub_right = nub_left + EMPTY_BATTERY_NUB_W_PX
    draw.rectangle((nub_left, top_y, nub_right - 1, top_y + EMPTY_BATTERY_NUB_H_PX - 1), fill=ink_idx)

    body_top = top_y + EMPTY_BATTERY_NUB_H_PX
    body_left = center_x - EMPTY_BATTERY_ICON_WIDTH_PX // 2
    body_right = body_left + EMPTY_BATTERY_ICON_WIDTH_PX
    body_bottom = top_y + EMPTY_BATTERY_ICON_HEIGHT_PX
    draw.rectangle(
        (body_left, body_top, body_right - 1, body_bottom - 1),
        outline=ink_idx,
        width=EMPTY_BATTERY_ICON_STROKE_PX,
    )
    return EMPTY_BATTERY_ICON_HEIGHT_PX


# --- No-connection alert glyph -------------------------------------------
# Same shape family as `draw_source_fault_badge()`'s triangular alert
# mark, scaled to the 76px hold-glyph family; a sibling glyph, not a
# shared call. Stroke matches POWER_ICON_STROKE_PX - thin strokes drown
# in dither noise.
ALERT_ICON_HEIGHT_PX = 76
ALERT_ICON_WIDTH_PX = 88
ALERT_ICON_STROKE_PX = POWER_ICON_STROKE_PX


def draw_alert_icon(draw, center_x, top_y, ink_idx):
    """Draw the no-connection alert mark (outline triangle, exclamation
    stroke, and a filled-ellipse dot - not a zero-length line, which
    paints only a single pixel) centred on `center_x`, apex at `top_y`.
    Returns the glyph's total height.
    """
    half_w = ALERT_ICON_WIDTH_PX / 2.0
    apex = (center_x, top_y)
    base_left = (center_x - half_w, top_y + ALERT_ICON_HEIGHT_PX - 1)
    base_right = (center_x + half_w, top_y + ALERT_ICON_HEIGHT_PX - 1)
    draw.polygon([apex, base_left, base_right], outline=ink_idx, width=ALERT_ICON_STROKE_PX)

    stroke_top = top_y + ALERT_ICON_HEIGHT_PX * 0.35
    stroke_bottom = top_y + ALERT_ICON_HEIGHT_PX * 0.65
    draw.line([(center_x, stroke_top), (center_x, stroke_bottom)], fill=ink_idx, width=ALERT_ICON_STROKE_PX)

    dot_r = 5
    dot_y = top_y + ALERT_ICON_HEIGHT_PX * 0.8
    draw.ellipse(
        [(center_x - dot_r, dot_y - dot_r), (center_x + dot_r, dot_y + dot_r)],
        fill=ink_idx,
    )
    return ALERT_ICON_HEIGHT_PX


def _build_hold_canvas(glyph_draw, glyph_height, label_text, sentences, field_idx, ink, dithered, source_fault=False, battery_low=False):
    """Shared hold-screen composition: a field (`field_idx` dithered
    toward White when `dithered`, else flat) with a vertically-centred
    block in `ink` - glyph, tracked Bold label, short rule, body.
    `sentences` are wrapped one by one so an authored line break is
    honoured; an empty tuple omits the body entirely.

    `battery_low`/`source_fault`: device/server-health indicators drawn
    in the screen's own `ink`.
    """
    canvas = dither.dithered_state_background(field_idx) if dithered else pf.new_canvas(field_idx)
    draw = ImageDraw.Draw(canvas)
    center_x = WIDTH // 2
    safe_width = SAFE_BOX[2] - SAFE_BOX[0]

    label_font = _font(DIMMED_LABEL_FONT)
    tracking = DIMMED_LABEL_TRACKING_PX
    label_width = sum(label_font.getlength(ch) for ch in label_text) + tracking * (len(label_text) - 1)
    label_ascent, label_descent = label_font.getmetrics()
    label_height = label_ascent + label_descent

    body_font = _font(DIMMED_BODY_FONT)
    body_lines = []
    for sentence in sentences:
        body_lines.extend(_wrap_text(body_font, sentence, safe_width))
    body_ascent, body_descent = body_font.getmetrics()
    body_line_height = body_ascent + body_descent + DIMMED_BODY_LINE_GAP_PX

    total_height = (
        glyph_height
        + SPACE_MD
        + label_height
        + SPACE_MD
        + DIMMED_RULE_HEIGHT_PX
        + (SPACE_MD + len(body_lines) * body_line_height if body_lines else 0)
    )
    start_y = (HEIGHT - total_height) // 2

    half = max(POWER_ICON_DIAMETER_PX, MOON_ICON_DIAMETER_PX) // 2
    _assert_in_safe_box((center_x - half, start_y, center_x + half, start_y + glyph_height), "dimmed-hold glyph")
    glyph_draw(draw, center_x, start_y, ink)

    label_y = start_y + glyph_height + SPACE_MD
    label_left = round(center_x - label_width / 2)
    _assert_in_safe_box((label_left, label_y, round(label_left + label_width), label_y + label_height), "dimmed-hold label")
    draw_tracked_text(draw, (label_left, label_y), label_text, label_font, ink, tracking=tracking)

    rule_y = label_y + label_height + SPACE_MD
    rule_left = center_x - DIMMED_RULE_WIDTH_PX // 2
    draw.rectangle((rule_left, rule_y, rule_left + DIMMED_RULE_WIDTH_PX, rule_y + DIMMED_RULE_HEIGHT_PX - 1), fill=ink)

    y = rule_y + DIMMED_RULE_HEIGHT_PX + SPACE_MD
    for line in body_lines:
        line_bbox = draw.textbbox((center_x, y), line, font=body_font, anchor="ma")
        _assert_in_safe_box(line_bbox, "dimmed-hold body line")
        draw.text((center_x, y), line, font=body_font, fill=ink, anchor="ma")
        y += body_line_height

    if source_fault:
        draw_source_fault_badge(canvas, ink, weight="bold")

    if battery_low:
        draw_battery_icon(canvas, draw, ink)

    return canvas


def _build_dimmed_hold_canvas(glyph_draw, glyph_height, label_text, sentences, source_fault=False, battery_low=False):
    """Dimmed variant of `_build_hold_canvas()`: DIMMED_FIELD_IDX
    dithered toward White, DIMMED_INK for everything drawn on it."""
    return _build_hold_canvas(
        glyph_draw, glyph_height, label_text, sentences,
        DIMMED_FIELD_IDX, DIMMED_INK, True,
        source_fault=source_fault, battery_low=battery_low,
    )


# --- Empty-state runway glyph ---------------------------------------------
# A runway seen from above: a strip with a dashed centreline and a
# threshold bar at each end. Same 76px height as the ring and crescent.
RUNWAY_ICON_HEIGHT_PX = 76
RUNWAY_ICON_WIDTH_PX = 48
RUNWAY_ICON_STROKE_PX = 4
RUNWAY_ICON_DASH_PX = 6
RUNWAY_ICON_DASH_GAP_PX = 5
RUNWAY_ICON_KEY_PX = 10  # the threshold "piano key" bars' height
RUNWAY_ICON_KEY_W_PX = 4  # ... and width; two per end, either side of the centreline


def draw_runway_icon(draw, center_x, top_y, ink_idx):
    """Draw the runway mark (threshold "piano keys" either side of a
    dashed centreline - a solid bar alone reads as a battery at glyph
    size) centred on `center_x`, top edge at `top_y`. Returns its height.
    """
    left = center_x - RUNWAY_ICON_WIDTH_PX // 2
    right = left + RUNWAY_ICON_WIDTH_PX
    bottom = top_y + RUNWAY_ICON_HEIGHT_PX
    s = RUNWAY_ICON_STROKE_PX
    draw.rectangle((left, top_y, right - 1, bottom - 1), outline=ink_idx, width=s)

    inner_top = top_y + s + 3
    inner_bottom = bottom - s - 3
    key_w = RUNWAY_ICON_KEY_W_PX
    key_h = RUNWAY_ICON_KEY_PX
    for kx in (center_x - 9 - key_w, center_x + 9):
        draw.rectangle((kx, inner_top, kx + key_w - 1, inner_top + key_h - 1), fill=ink_idx)
        draw.rectangle((kx, inner_bottom - key_h + 1, kx + key_w - 1, inner_bottom), fill=ink_idx)

    dash_w = 4
    span_top = inner_top + key_h + RUNWAY_ICON_DASH_GAP_PX
    span_bottom = inner_bottom - key_h - RUNWAY_ICON_DASH_GAP_PX
    step = RUNWAY_ICON_DASH_PX + RUNWAY_ICON_DASH_GAP_PX
    n = max(1, (span_bottom - span_top + 1 + RUNWAY_ICON_DASH_GAP_PX) // step)
    used = n * step - RUNWAY_ICON_DASH_GAP_PX
    y = span_top + (span_bottom - span_top + 1 - used) // 2
    for _ in range(n):
        draw.rectangle((center_x - dash_w // 2, y, center_x + dash_w // 2 - 1, y + RUNWAY_ICON_DASH_PX - 1), fill=ink_idx)
        y += step
    return RUNWAY_ICON_HEIGHT_PX


_LEGAL_PANEL_INDICES = {IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN}


def _assert_legal_palette(canvas, bg_idx):
    """Guard rail: every index anywhere on the panel is one of the 6 legal
    Spectra 6 panel indices, and `bg_idx` (the state's flat background
    fill) is the single most common index on the panel.

    A real illustration's own livery colors may legitimately use every
    other legal index anywhere on the canvas, so the contract is just "no
    illegal index anywhere, and the flat field is provably dominant" - not
    a spatially-scoped check.
    """
    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    illegal = idx_set - _LEGAL_PANEL_INDICES
    assert not illegal, (
        "canvas (bg_idx=%r) contains illegal palette index(es) %r - expected a subset of the 6 legal panel indices %r"
        % (bg_idx, sorted(illegal), sorted(_LEGAL_PANEL_INDICES))
    )

    counts = {value: count for count, value in colors} if colors else {}
    bg_count = counts.get(bg_idx, 0)
    other_max = max((count for value, count in counts.items() if value != bg_idx), default=0)
    assert bg_count >= other_max, (
        "canvas's state index bg_idx=%r has %d pixels, not >= the next most common index's %d pixels - "
        "the flat background field is not dominant" % (bg_idx, bg_count, other_max)
    )


def _build_active_canvas(
    flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False,
):
    """Build the departing/arriving two-flight poster canvas.

    `battery_low`/`source_fault`: when True, draw the bottom-left
    battery-low icon / bottom-centre source-fault badge in the state's
    own ink, via `state_ink_index()` so neither can use an illegal index.
    """
    if state not in STATE_BACKGROUND:
        raise ValueError("unknown state %r (expected 'departing', 'arriving', or 'empty')" % (state,))
    bg_idx = state_background_index(state, theme_id=theme_id)
    fg_idx = state_ink_index(state, theme_id=theme_id)

    # Dithering and text weight are theme properties, not derivable from
    # bg_idx alone - see THEMES' own comment in device_config.py.
    normalised_theme_id = device_config.normalise_theme_id(theme_id)
    theme_dithered = device_config.theme_dithered(normalised_theme_id)
    weight = device_config.theme_weight(normalised_theme_id)

    is_band_theme = device_config.theme_is_band(normalised_theme_id)
    band_idx = device_config.theme_band_index(normalised_theme_id) if is_band_theme else None
    band_dithered_flag = device_config.theme_band_dithered(normalised_theme_id) if is_band_theme else False

    # Dithering toward White is the only way to lighten a fixed physical
    # ink that reads too dark/saturated at full-panel coverage; themes
    # with `dithered: False` get a flat fill instead.
    canvas = dither.dithered_state_background(bg_idx) if theme_dithered else pf.new_canvas(bg_idx)

    # Band painted first so illustrations occlude it naturally.
    if is_band_theme:
        draw_diagonal_band(canvas, band_idx, dithered=band_dithered_flag)

    # The frame outline is no longer drawn, but FRAME_INSET_FRAC still
    # feeds inner_width and draw_source_fault_badge()'s bottom anchor.

    draw_top_labels(canvas, state, fg_idx, bg_idx, weight, runway_id=runway_id, band_theme=is_band_theme)

    # Main flight: current detection, always nose-left.
    inner_width = WIDTH * (1 - 2 * FRAME_INSET_FRAC)
    main_w = round(inner_width * MAIN_ILLUSTRATION_WIDTH_FRAC)

    main_path = illustrations.select_illustration(route, flight.get("aircraft_type"))
    main_placement = None
    main_resized = _load_illustration_safely(main_path, main_w)
    if main_resized is not None:
        main_left = _left_for_centered_content(main_resized, WIDTH / 2)
        main_top = _top_for_centered_content(main_resized, HEIGHT * MAIN_ILLUSTRATION_CENTER_Y_FRAC)
        main_placement = draw_illustration(canvas, main_resized, main_left, main_top)
        _assert_within_canvas(main_placement.rect, "main aircraft illustration")
        draw_main_text_block(canvas, flight, state, route, main_placement, fg_idx, bg_idx, weight, band_idx=band_idx)

    # Previous flight: the detection immediately preceding this one.
    if previous_flight is not None and main_placement is not None:
        prev_path = illustrations.select_illustration(previous_route, (previous_flight or {}).get("aircraft_type"))
        # SIZE derives from `.rect` (constant per file), not `.content`,
        # so it does not depend on which airline is in the main slot.
        main_rect = main_placement.rect
        prev_w = round((main_rect[2] - main_rect[0]) * PREVIOUS_ILLUSTRATION_WIDTH_FRAC)
        prev_resized = _load_illustration_safely(prev_path, prev_w)
        if prev_resized is not None:
            # POSITION is anchored to painted pixels: right-aligned to
            # the main illustration's visible right edge, centred on
            # PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC.
            prev_left = _left_for_right_aligned_content(prev_resized, main_placement.content[2])
            prev_top = _top_for_centered_content(prev_resized, HEIGHT * PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC)
            prev_placement = draw_illustration(canvas, prev_resized, prev_left, prev_top)
            _assert_within_canvas(prev_placement.rect, "previous aircraft illustration")
            draw_previous_text_block(canvas, previous_flight, previous_state, previous_route, prev_placement, fg_idx, bg_idx, weight, band_idx=band_idx)

    # The source-fault badge, drawn last so it sits on top of everything
    # else, using the state's own resolved ink index.
    if source_fault:
        draw_source_fault_badge(canvas, fg_idx, weight=weight)

    if battery_low:
        draw_battery_icon(canvas, ImageDraw.Draw(canvas), fg_idx)

    # Guard rail: every index on the panel is legal, and the flat
    # background field is provably dominant.
    _assert_legal_palette(canvas, bg_idx)

    return canvas


def build_canvas(
    flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False, quiet_hours_until=None,
):
    """Pre-pack "P"-mode canvas for `flight` in `state` ("departing" /
    "arriving" / "empty" / "quiet_hours" / "display_off" /
    "battery_empty"). Public so callers never reach into private render
    state.

    `route`: a full or airline-only route, `None` on a miss or for the
    empty state. `theme_id`/`runway_id`: registry ids, degrading to the
    default when unrecognised. `source_fault`: only when every ADS-B
    source has failed. `quiet_hours_until` ("HH:MM") applies only to
    `state == "quiet_hours"`.

    `"display_off"`/`"quiet_hours"`/`"empty"` are always White/Black.
    `"battery_empty"` ignores every other argument: its bytes/hash must
    stay constant for the whole parked episode.
    """
    if state == "battery_empty":
        return _build_battery_empty_canvas()
    if state == "display_off":
        return _build_display_off_canvas(source_fault=source_fault, battery_low=battery_low)
    if state == "quiet_hours":
        return _build_quiet_hours_canvas(
            quiet_hours_until=quiet_hours_until, source_fault=source_fault, battery_low=battery_low)
    if flight is None or state == "empty":
        return _build_empty_canvas(
            runway_id=runway_id, source_fault=source_fault, battery_low=battery_low)
    return _build_active_canvas(
        flight,
        state,
        route=route,
        previous_flight=previous_flight,
        previous_route=previous_route,
        previous_state=previous_state,
        theme_id=theme_id,
        runway_id=runway_id,
        source_fault=source_fault,
        battery_low=battery_low,
    )


def render_panel(
    flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False, quiet_hours_until=None,
):
    """Return a packed 960,000-byte panel for `flight` in `state`
    ("departing" / "arriving" / "empty" / "quiet_hours" / "display_off" /
    "battery_empty"). All other arguments pass straight through to
    `build_canvas()` - see its docstring for the full contract.
    """
    canvas = build_canvas(
        flight,
        state,
        route=route,
        previous_flight=previous_flight,
        previous_route=previous_route,
        previous_state=previous_state,
        theme_id=theme_id,
        runway_id=runway_id,
        source_fault=source_fault,
        battery_low=battery_low,
        quiet_hours_until=quiet_hours_until,
    )
    return pf.pack_panel(canvas)


# Manual-QA-only sample routes - server/plane/render.py's CLI has no live
# enrichment lookup of its own (that's poll_loop.py's job); these are
# plausible-looking hits so `--preview` without `--no-route` shows the
# resolved-route text layout rather than always previewing the fallback.
# `callsign_iata` is a synthetic sample value in both dicts, in each
# route's own airline's real IATA prefix - not a real adsbdb-resolved
# identifier - so a plain preview exercises tier 1 end to end.
_PREVIEW_ROUTE = {
    "airline_name": "Air France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "JFK",
    "destination_city": "New York",
    "callsign_iata": "AF1006",
}
_PREVIEW_PREVIOUS_ROUTE = {
    "airline_name": "Vueling Airlines",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "BCN",
    "destination_city": "Barcelona",
    "callsign_iata": "VY1234",
}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state",
        choices=["departing", "arriving", "empty", "quiet_hours", "display_off", "battery_empty"],
        default="empty",
    )
    parser.add_argument("--callsign", default=None, help="Manual QA only: fake callsign for a departing/arriving preview.")
    parser.add_argument("--hex", default="000000", help="Manual QA only: fake ICAO hex (used if --callsign is omitted).")
    parser.add_argument(
        "--previous-callsign",
        default=None,
        help="Manual QA only (D-26): fake callsign for the previous-flight card. Omit to preview a single-flight panel.",
    )
    parser.add_argument(
        "--previous-hex", default="111111", help="Manual QA only: fake ICAO hex for the previous flight."
    )
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
    parser.add_argument(
        "--airline",
        metavar="NAME",
        default=None,
        help="Manual QA only (D-04, Phase 7 07-01): override _PREVIEW_ROUTE's airline_name for a "
             "departing/arriving preview, so a long/real airline name is a flag rather than a "
             "hand-built dict. Ignored when --no-route is also given.",
    )
    parser.add_argument(
        "--city",
        metavar="NAME",
        default=None,
        help="Manual QA only (D-04, Phase 7 07-01): override the state-appropriate city in "
             "_PREVIEW_ROUTE (destination_city for --state departing, origin_city for --state "
             "arriving) for a departing/arriving preview. Ignored when --no-route is also given.",
    )
    parser.add_argument(
        "--calibration-preview",
        metavar="DIR",
        default=None,
        help="D-13 (Phase 7 07-01): write dither.write_calibration_preview(DIR)'s single "
             "palette-swatches.png monitor-side calibration artifact into DIR, print its path, and "
             "exit - no panel is rendered when this flag is given.",
    )
    parser.add_argument(
        "--preview-airline-only",
        action="store_true",
        help="Manual QA only (D-06, quick task 260827-hyy; tier updated Phase 8 08-04 D-10): preview "
             "the airline-only intermediate render state (airline known via the callsign's ICAO "
             "prefix, destination genuinely unknown - line 1 is omitted entirely (D-10 tier 3), only "
             "'{airline} · {type}' is drawn, at the airline's own illustration). Takes precedence "
             "over --no-route when both are given.",
    )
    parser.add_argument(
        "--no-identifier",
        action="store_true",
        help="Manual QA only (D-10 tier 2, Phase 8 08-04): strip the preview route's callsign_iata "
             "identifier so a departing/arriving preview forces tier 2 (title-case direction word + "
             "city, no identifier) instead of the default tier 1. No effect when the route is "
             "already None (--no-route won) or when --preview-airline-only is also given (that route "
             "has no cities and lands on tier 3 regardless) - both combinations are harmless no-ops.",
    )
    parser.add_argument(
        "--theme", choices=device_config.THEME_IDS, default=device_config.DEFAULT_THEME_ID,
        help="CFG-01: theme id from server/device_config.py's THEMES registry.",
    )
    parser.add_argument(
        "--runway", choices=device_config.RUNWAY_IDS, default=device_config.DEFAULT_RUNWAY_ID,
        help="CFG-12: tracked-runway id from server/device_config.py's RUNWAYS registry.",
    )
    parser.add_argument(
        "--source-fault", action="store_true",
        help="Manual QA only (CFG-05): preview the source-fault alert badge, as if every ADS-B "
             "provider had failed.",
    )
    parser.add_argument(
        "--battery-low",
        action="store_true",
        help="Manual QA only (D-04/D-06): preview the low-battery icon in the panel's bottom-left corner.",
    )
    parser.add_argument(
        "--quiet-hours-until",
        default=device_config.DEFAULT_QUIET_HOURS_END,
        help="Manual QA only (D-05/D-06): the local Europe/Paris wall-clock end time the "
             "--state quiet_hours preview's 'Back at' line shows. Ignored for every other --state, "
             "including --state display_off, which never shows a return-time value (D-03/D-04).",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.calibration_preview:
        # A standalone diagnostic action, not mixed with a panel render -
        # no --state/--out/--preview handling below is reached.
        for path in dither.write_calibration_preview(args.calibration_preview):
            print("wrote %s" % path)
        return 0

    flight = None
    route = None
    previous_flight = None
    previous_route = None
    previous_state = None
    # The quiet-hours state has no flight to enrich, exactly like empty -
    # test membership against the two real aircraft states rather than a
    # second negative list (`!= "empty"`) that a future third non-flight
    # state would have to be remembered into.
    if args.state in (runway_config.STATE_DEPARTING, runway_config.STATE_ARRIVING):
        flight = {"hex": args.hex, "callsign": args.callsign}
        # --preview-airline-only takes precedence over --no-route when both
        # are given (documented in --preview-airline-only's own help text
        # above).
        if args.preview_airline_only:
            route = enrich.airline_only_route(_PREVIEW_ROUTE["airline_name"])
        elif args.no_route:
            route = None
        else:
            route = _PREVIEW_ROUTE
        # --no-identifier strips callsign_iata so a departing/arriving
        # preview forces tier 2. No-op when route is already None
        # (--no-route won, nothing to strip) or when it is the
        # airline-only route (--preview-airline-only won; that route's
        # callsign_iata is already None and it has no cities regardless, so
        # stripping it again changes nothing). Never mutates _PREVIEW_ROUTE
        # itself.
        if args.no_identifier and route is not None:
            route = dict(route)
            route["callsign_iata"] = None
        # --airline/--city override _PREVIEW_ROUTE's own fields so a
        # long/real name is a flag rather than a hand-built dict.
        # --no-route continues to win over both - route is already None above
        # and stays None here. Never mutates _PREVIEW_ROUTE itself.
        if route is not None and (args.airline or args.city):
            route = dict(route)
            if args.airline:
                route["airline_name"] = args.airline
            if args.city:
                city_field = (
                    "destination_city" if args.state == runway_config.STATE_DEPARTING
                    else "origin_city"
                )
                route[city_field] = args.city
        if args.previous_callsign:
            previous_flight = {"hex": args.previous_hex, "callsign": args.previous_callsign}
            if args.preview_airline_only:
                previous_route = enrich.airline_only_route(_PREVIEW_PREVIOUS_ROUTE["airline_name"])
            elif args.no_route:
                previous_route = None
            else:
                previous_route = _PREVIEW_PREVIOUS_ROUTE
            if args.no_identifier and previous_route is not None:
                previous_route = dict(previous_route)
                previous_route["callsign_iata"] = None
            previous_state = runway_config.STATE_ARRIVING if args.state == runway_config.STATE_DEPARTING else runway_config.STATE_DEPARTING

    canvas = build_canvas(
        flight,
        args.state,
        route=route,
        previous_flight=previous_flight,
        previous_route=previous_route,
        previous_state=previous_state,
        theme_id=args.theme,
        runway_id=args.runway,
        source_fault=args.source_fault,
        battery_low=args.battery_low,
        quiet_hours_until=args.quiet_hours_until,
    )
    data = pf.pack_panel(canvas)
    if len(data) != pf.IMAGE_BYTES:
        sys.exit("internal error: generated %d bytes, expected %d" % (len(data), pf.IMAGE_BYTES))

    if args.out:
        with open(args.out, "wb") as fh:
            fh.write(data)
        digest = hashlib.sha256(data).hexdigest()
        print("wrote %s (%d bytes, state=%s)" % (args.out, len(data), args.state))
        print("sha256 %s" % digest)
        # A forced render's most common failure is a human forgetting to
        # restart skypane-poll.timer afterward - the tool doing the
        # forcing is the right place to say so. The unit is
        # deploy/skypane-poll.timer.
        if args.airline or args.city or args.no_route:
            print(
                "REMINDER: this panel is SYNTHETIC (--airline/--city/--no-route was used) - "
                "restart skypane-poll.timer after testing, or the frame stays frozen on this "
                "test image indefinitely."
            )

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
