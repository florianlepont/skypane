#!/usr/bin/env python3
"""Minimal-but-real panel renderer for the plane view (PLANE-01/02/03).

Every draw call goes directly onto a "P"-mode canvas with an integer
palette-index fill, never an RGB tuple and never an RGB compose-then-
quantize step for flat fills (02-RESEARCH.md Architecture Pattern 1) - this
is the mechanism that satisfies the "disable anti-aliasing" rule for free
everywhere except the real per-airline illustrations below, which are
deliberately full-color and dithered (D-25).

Phase 3, final confirmed layout (D-21/D-24/D-25/D-26/D-27, 03-CONTEXT.md
addenda 2-3) - supersedes every earlier Phase-3 iteration (the dithered
mood background, quiet-zone text compositing, the single mirrored flat
silhouette, Zilla Slab):

- **D-21**: the active-state background is a flat single-color fill
  (`panel_format.new_canvas(bg_idx)`) - no dithered gradient. The old
  `server.plane.dither.build_mood_background()` recipe was retired; only
  `dither.dither_to_full_panel_palette()` (the full-6-color illustration
  quantizer) survives from that module.
- **D-24**: aircraft illustrations are never mirrored. Every vendored
  illustration file is nose-left by convention
  (`illustrations.ILLUSTRATION_SOURCE_NOSE`) and is drawn exactly as
  vendored, in both departing and arriving states - real, detailed,
  full-color art does not mirror convincingly the way the old flat CC0
  silhouette did (confirmed via a real on-glass-preview A/B test this
  session). The background color and the state label text are the only
  remaining departing/arriving cues.
- **D-25/D-26**: two real flight cards on one canvas - the current
  detection (large, upper-center) and the immediately-preceding detection
  (smaller, bottom-right, right-aligned to the main illustration's own
  right edge). Both use their own real per-airline illustration file
  (`illustrations.select_illustration()`), full-color, Floyd-Steinberg-
  dithered to the panel's 6-color palette via
  `dither.dither_to_full_panel_palette()` - never simplified to a flat
  silhouette. No quiet-zone rectangles anywhere: D-21's flat background
  needs no protection against text sitting on a dithered pixel.
- **D-27**: every text role uses PT Serif **Regular**, not Bold -
  deliberately reintroduces a thin-hairline e-ink legibility risk not yet
  verified on real glass (see `server/assets/fonts/VENDOR.md`'s "Known
  risk" note; Wave 4's on-glass checkpoint must re-check this).

**Colour and CFG-01 (D-09/D-10/D-11, 06-CONTEXT.md)**: the panel's
DEPARTING/ARRIVING background and ink colours have never been calibrated
against real glass - they are the same on-screen-only-confirmed values
D-21 recorded (`server/panel_format.py`'s "confirmed against on-screen
previews only" note). Phase 7's on-glass session is the first place that
calibration actually happens. CFG-01 therefore ships a theme picker whose
registry (`server/device_config.py`'s `THEMES`) currently holds exactly
one entry, `"sky"`. Adding Phase 7's real, hardware-validated theme
variants is a single `THEMES` dict entry in `server/device_config.py` -
see that module's own docstring for the extension procedure - with no
change to this module at all.

The old 64px "inviolable" SAFE_BOX margin (Phase 2) is still enforced for
the top-row labels, which D-26 explicitly pins to that same MARGIN inset.
It is deliberately **not** enforced for the frame, the illustrations, or
the flight text blocks below them: D-26's live-approved layout puts the
decorative frame at a tighter ~2.5%-of-width inset (~30px), inside the old
64px band. This has only been confirmed against on-screen preview PNGs, not
against the real physical bezel - an open item for Wave 4's on-glass
checkpoint, alongside the PT Serif Regular legibility check above.

Usage (manual QA):
    server/.venv/bin/python3 server/plane/render.py --state empty --out /tmp/panel.bin
    server/.venv/bin/python3 server/plane/render.py --state arriving --callsign AF1380 \
        --out /tmp/panel.bin --preview /tmp/panel.preview.png
    server/.venv/bin/python3 server/plane/render.py --state departing --callsign AF1380 \
        --previous-callsign VY1234 --out /tmp/panel.bin --preview /tmp/panel.preview.png
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

from server import device_config
from server import panel_format as pf
from server.panel_format import IDX_BLACK, IDX_BLUE, IDX_GREEN, IDX_RED, IDX_WHITE, IDX_YELLOW, WIDTH, HEIGHT
from server.plane import dither, enrich, illustrations, runway_config

# --- UI-SPEC Spacing Scale (02-UI-SPEC.md, unchanged since Revision 1) ----
SPACE_XS = 8
SPACE_SM = 16
SPACE_MD = 32
SPACE_LG = 64

# MARGIN is the top-row labels' inset (D-26: "the existing MARGIN (64px)
# inset, not the frame's own 2.5% inset - they sit inside the frame, not
# on it"). See the module docstring for why this is no longer enforced as
# a blanket "inviolable" margin for every element the way it was in Phase 2.
MARGIN = SPACE_LG
SAFE_BOX = (MARGIN, MARGIN, WIDTH - MARGIN, HEIGHT - MARGIN)  # (64, 64, 1136, 1536)

# --- Typography (D-20/D-27, supersedes 02/03's Inter -> Zilla Slab chain) --
FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")
)
PT_SERIF_REGULAR = os.path.join(FONT_DIR, "PTSerif-Regular.ttf")
PT_SERIF_BOLD = os.path.join(FONT_DIR, "PTSerif-Bold.ttf")

# D-26's exact confirmed sizes, per role. (font_path, size, weight) - weight
# is documentation only (the path already selects the correct static weight
# file). D-27: every active-state role is Regular; the empty state's
# heading keeps a Bold weight for continuity with Phase 2's hero-caption
# boldness (not itself a D-26 subject - the empty state's copy is
# unchanged by this phase).
STATE_LABEL_FONT = (PT_SERIF_REGULAR, 20, 400)
TOP_TAG_FONT = (PT_SERIF_REGULAR, 18, 400)
MAIN_LINE1_FONT = (PT_SERIF_REGULAR, 44, 400)
MAIN_LINE2_FONT = (PT_SERIF_REGULAR, 22, 400)
PREVIOUS_LINE1_FONT = (PT_SERIF_REGULAR, 28, 400)
PREVIOUS_LINE2_FONT = (PT_SERIF_REGULAR, 16, 400)
EMPTY_HEADING_FONT = (PT_SERIF_BOLD, 72, 700)
EMPTY_BODY_FONT = (PT_SERIF_REGULAR, 40, 400)

# Overflow floors (fit_text_size()'s per-role minimums) - real city/airline
# names shrink in small steps rather than clipping, wrapping mid-word, or
# overflowing, but never below these named limits.
MAIN_LINE1_MIN_SIZE = 28
MAIN_LINE2_MIN_SIZE = 16
PREVIOUS_LINE1_MIN_SIZE = 18
PREVIOUS_LINE2_MIN_SIZE = 12
# CFG-12: the empty-state heading is now runway-dependent
# (empty_heading_text()) and therefore not a fixed, pre-measured string -
# it gets the same fit_text_size() shrink treatment as the long
# route/airline text above, floored well above illegibility. All three
# registry headings ("Watching Runway 3" / "06-24" / "02-20") are
# deliberately short, so this floor is not expected to bind in practice -
# it exists only as a guard rail should a longer heading ever be added.
EMPTY_HEADING_MIN_SIZE = 48
_FIT_STEP_PX = 2

# --- Colour section (state-scoped, unchanged since 02-UI-SPEC.md Revision
# 2) - keyed by runway_config's STATE_* constants (not bare string
# literals) so the two modules cannot drift apart. --------------------------
#
# CFG-01 (06-CONTEXT.md D-09/D-10/D-11): STATE_BACKGROUND/STATE_INK are
# retained below as module-level constants, redefined from the default
# theme's own server/device_config.py registry entry, ONLY because
# server/test_render.py's pre-existing checks read them directly. New code
# must never read these two dicts directly - call
# state_background_index()/state_ink_index() instead, which resolve
# through device_config.THEMES, the single registry the companion Config
# page's picker also reads. Do not delete these constants and do not
# change their values - the default ("sky") theme's colours are exactly
# the pre-Phase-6 values.
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
    """Return the background palette index for `state` ("departing" or
    "arriving") under `theme_id`, the CFG-01 theme registry key. `theme_id`
    is normalised through `device_config.normalise_theme_id()` first, so an
    unrecognised, hostile, or stale theme id silently degrades to the
    default theme (T-06-06-01) rather than ever reaching a dict lookup - an
    unrecognised *theme* is forgiving. `state` is intentionally NOT
    normalised the same way: an unknown state is a real caller-bug detector
    and must stay loud - every caller in this module only ever reaches this
    function after `_build_active_canvas()`'s own `state not in
    STATE_BACKGROUND` guard has already validated it.
    """
    theme_id = device_config.normalise_theme_id(theme_id)
    return device_config.theme_background_index(state, theme_id)


def state_ink_index(state, theme_id=device_config.DEFAULT_THEME_ID):
    """Same contract as state_background_index(), for the ink (foreground)
    index. `state` is accepted so both functions share one call shape at
    every call site, even though today's single theme's ink colour does
    not vary by state - a future theme entry could add a per-state ink
    split without changing this signature.
    """
    theme_id = device_config.normalise_theme_id(theme_id)
    return device_config.theme_ink_index(theme_id)


def runway_tag_text(runway_id=device_config.DEFAULT_RUNWAY_ID):
    """Return the CFG-12 top-right tag string for `runway_id`, normalised
    through `device_config.normalise_runway_id()` first so an unrecognised,
    hostile, or stale runway id silently degrades to the default runway's
    tag rather than raising (T-06-06-01) - matching
    state_background_index()'s "unrecognised registry id is forgiving"
    contract.
    """
    runway_id = device_config.normalise_runway_id(runway_id)
    return device_config.runway_tag_text(runway_id)


def empty_heading_text(runway_id=device_config.DEFAULT_RUNWAY_ID):
    """Same contract as runway_tag_text(), for the empty-state heading."""
    runway_id = device_config.normalise_runway_id(runway_id)
    return device_config.runway_empty_heading(runway_id)


# CFG-12 (06-CONTEXT.md): EMPTY_HEADING_TEXT/TOP_RIGHT_TAG_TEXT are
# retained below as module-level constants, redefined from the default
# runway's own device_config.py registry entry, ONLY because
# server/test_render.py's pre-existing checks read them directly. New code
# must never read these two constants directly - call
# empty_heading_text()/runway_tag_text() instead.
EMPTY_HEADING_TEXT = empty_heading_text(device_config.DEFAULT_RUNWAY_ID)

# The empty state's own already-established ink (its heading and body copy
# both already used the bare IDX_BLACK literal) - named so the battery icon
# can share "each state's own ink" structurally, not by comment (05-UI-SPEC.md
# resolved discretion item: battery icon renders in all three states,
# including empty, since a low-battery reading is a device-health fact
# independent of whether an aircraft is currently detected).
#
# The empty state is deliberately NOT theme-dependent (CFG-01): it is always
# White/Black, so this stays a bare constant rather than resolving through
# state_ink_index(). The CFG-05 source-fault badge shares it for the same
# reason.
EMPTY_INK = IDX_BLACK
EMPTY_BODY_TEXT = "No aircraft detected yet — the display updates the moment one is."
TOP_RIGHT_TAG_TEXT = runway_tag_text(device_config.DEFAULT_RUNWAY_ID)
ROUTE_FALLBACK_TEXT = "Route unavailable"

# CFG-05 (D-06 seed .planning/seeds/on-device-fault-icon.md): the source-
# fault alert badge's caption - short, English (D-23), and pointing at the
# companion page, which is where an all-sources-down outage is actually
# diagnosed (06-UI-SPEC.md). SOURCE_FAULT_GLYPH_PX is deliberately small -
# see draw_source_fault_badge()'s own docstring for why the badge's area
# must stay small enough that _assert_legal_palette()'s background-
# dominance assertion still holds.
SOURCE_FAULT_TEXT = "ADS-B source unavailable — check the companion page"
SOURCE_FAULT_GLYPH_PX = 28

# --- D-26 frame + layout geometry -------------------------------------------
FRAME_INSET_FRAC = 0.025  # ~2.5% of canvas WIDTH, inset from every edge
FRAME_STROKE_PX = 2

MAIN_ILLUSTRATION_WIDTH_FRAC = 0.87  # of the inner (post-frame-inset) canvas width
MAIN_ILLUSTRATION_TOP_FRAC = 0.30  # of canvas height
MAIN_TEXT_OVERLAP_PX = 20  # main text top = main illustration bottom - this
MAIN_LINE_GAP_PX = 8  # gap between main line 1's bottom and line 2's top

PREVIOUS_ILLUSTRATION_WIDTH_FRAC = 0.57  # of the MAIN illustration's own rendered width
PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC = 0.76  # of canvas height
PREVIOUS_TEXT_GAP_PX = 22  # gap below the previous illustration's bottom edge
PREVIOUS_LINE_GAP_PX = 34  # line 2's top below line 1's own TOP (not bottom)

# --- D-04/D-06/D-07 battery-low icon geometry (05-UI-SPEC.md, 05-02-PLAN.md)
# The two POSITION constants (LEFT/BOTTOM) still derive from MARGIN, unchanged
# since 05-02. The four SIZE constants are a uniform round(original * 0.7)
# reduction of their former spacing-scale values - a live on-glass correction
# (260828-0qo, quick task) applied after the developer saw the original
# (72x32-nominal) glyph on the real Spectra 6 panel and judged it too large.
# Total bounding box is now (64, 1514, 115, 1536) - see draw_battery_icon()'s
# docstring for the full geometry derivation.
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
BATTERY_ICON_FILL_FRAC = 0.22  # bespoke: a fixed "low" glyph, not a live gauge (05-UI-SPEC.md) - unchanged, a ratio not a pixel size

_font_cache = {}


def _font(spec):
    path, size, _weight = spec
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def fit_text_size(font_path, initial_size, text, max_width, min_size):
    """Return the largest ImageFont at `font_path`, stepping down from
    `initial_size` in `_FIT_STEP_PX`-point decrements, whose rendered width
    for `text` fits within `max_width` - floored at `min_size`. Never clips,
    wraps mid-word, or overflows; callers still assert the final bbox as a
    guard rail.
    """
    size = initial_size
    while size > min_size:
        font = _font((font_path, size, None))
        if font.getlength(text) <= max_width:
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


def _assert_within_canvas(bbox, label):
    """Looser guard rail than _assert_in_safe_box(): only asserts the
    element does not fall off the 1200x1600 canvas entirely. Used for the
    frame, the illustrations, and the flight text blocks below them - D-26's
    live-approved layout deliberately sits some of these inside the old
    64px SAFE_BOX band (see the module docstring's "not yet verified
    against the real physical bezel" note).
    """
    left, top, right, bottom = bbox
    assert left >= 0 and top >= 0 and right <= WIDTH and bottom <= HEIGHT, (
        "%s bounding box %r falls outside the %dx%d canvas" % (label, bbox, WIDTH, HEIGHT)
    )


def _wrap_text(font, text, max_width):
    """Manual word-wrap: split on spaces, greedily pack words onto a line
    while the line's rendered width (font.getlength) stays within
    max_width. Pillow's ImageDraw.multiline_text does not word-wrap, so the
    empty-state body copy is wrapped by hand to fit the safe-box width.
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
    """D-26: a thin `ink_idx`-coloured rectangle outline, `FRAME_STROKE_PX`
    wide, inset `FRAME_INSET_FRAC` of the canvas width from every edge.
    Returns the frame's own bounding box.
    """
    inset = round(WIDTH * FRAME_INSET_FRAC)
    box = (inset, inset, WIDTH - inset, HEIGHT - inset)
    ImageDraw.Draw(canvas).rectangle(box, outline=ink_idx, width=FRAME_STROKE_PX)
    return box


def draw_source_fault_badge(canvas, ink_idx):
    """CFG-05: draw a small triangular alert glyph (outline + exclamation
    stroke) with `SOURCE_FAULT_TEXT` beside it, bottom-centre inside the
    frame `draw_frame()` returns. Uses `ink_idx` only - `ImageDraw.polygon()`
    and `ImageDraw.line()` calls, never a new palette index - so the badge
    can never introduce an illegal index regardless of the active theme.
    The badge's combined bounding box (glyph + caption) is deliberately
    small, so `_assert_legal_palette()`'s "bg_idx is the single most common
    index" dominance assertion still holds for every state and theme; a
    later enlargement of this badge is a conscious decision, not an
    accident inherited from this implementation.

    Driven only by `poll_loop.py`'s all-providers-failed classification
    (derived from `detect.poll_current_aircraft()`'s diagnostics dict) -
    see `render_panel()`'s own docstring for the rule that makes this
    requirement correct rather than a false-alarm trap (T-06-06-02,
    `.planning/seeds/on-device-fault-icon.md`).
    """
    draw = ImageDraw.Draw(canvas)
    frame_inset = round(WIDTH * FRAME_INSET_FRAC)
    frame_bottom = HEIGHT - frame_inset

    caption_font = _font(TOP_TAG_FONT)
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
    draw.line(
        [(stroke_x, top + glyph_size * 0.8), (stroke_x, top + glyph_size * 0.8)],
        fill=ink_idx, width=2,
    )
    draw.text((text_left, mid_y), SOURCE_FAULT_TEXT, font=caption_font, fill=ink_idx, anchor="lm")

    return combined_bbox


def draw_battery_icon(canvas, draw, ink_idx):
    """D-04/D-06: a bottom-left battery glyph - a hollow outlined body with a
    small solid terminal nub and a left-aligned solid partial fill,
    signalling a fixed "low" reading rather than a live gauge. Own dedicated
    bottom-left zone (D-05) - the one area of the locked two-flight layout
    with no existing element, and the visual counterweight to the
    bottom-right previous-flight card; never reuses, displaces, or resizes
    the top-left state label or the top-right runway tag (CFG-12 made that
    tag runway-dependent; this icon's zone is unaffected either way). It is
    also horizontally clear of the CFG-05 source-fault badge, which is
    centred on the same bottom band - see draw_source_fault_badge().

    All geometry derives from the BATTERY_ICON_* module constants (the two
    position constants from MARGIN, the four size constants from a uniform
    0.7 reduction of their former spacing-scale values - 260828-0qo) - no ad
    hoc magic numbers. Draws three flat integer-palette-index rectangles: the
    body as a BATTERY_ICON_STROKE_PX-wide outline, the nub filled solid, and
    the fill box filled solid - square corners, no rounded-rectangle
    primitive, no antialiasing parameters. These box tuples are Pillow's
    inclusive corner coordinates, matching draw_frame()'s own convention: the
    rendered footprint is therefore 52x23px for a nominal 51x22 box,
    intentionally.

    Returns the icon's total bounding box (left, top, right, bottom) -
    (64, 1514, 115, 1536).
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
    # Looser canvas guard, not the strict safe-box guard (05-UI-SPEC.md): this
    # element sits inside the old 64px band's bottom-left corner
    # deliberately, exactly like the frame and both illustrations already do.
    _assert_within_canvas(total, "battery icon")

    draw.rectangle(body, outline=ink_idx, width=BATTERY_ICON_STROKE_PX)
    draw.rectangle(nub, fill=ink_idx)
    draw.rectangle(fill, fill=ink_idx)
    return total


def draw_top_labels(canvas, state, ink_idx, runway_id=device_config.DEFAULT_RUNWAY_ID):
    """D-26 top row: the state label (top-left) and the CFG-12 runway tag
    (top-right, `runway_tag_text(runway_id)`), both PT Serif Regular at the
    small sizes D-26 confirmed, both at the existing `MARGIN` inset (inside
    the frame, not on it) - no icon glyph, no letter-spacing/tracking (that
    was the old, larger zone-1 treatment; superseded).
    """
    draw = ImageDraw.Draw(canvas)
    label_font = _font(STATE_LABEL_FONT)
    tag_font = _font(TOP_TAG_FONT)
    tag_text = runway_tag_text(runway_id)

    # _assert_within_canvas(), not the strict _assert_in_safe_box(): real
    # font glyph metrics can carry a 1-2px negative left/right bearing at
    # these small sizes (e.g. PT Serif's "A" at 20px), which would fail a
    # pixel-exact 64px boundary despite the text visually sitting exactly
    # at MARGIN as D-26 specifies - see the module docstring's note on why
    # the old "inviolable" SAFE_BOX is not enforced pixel-exactly here.
    label_text = STATE_LABEL_TEXT[state]
    label_bbox = draw.textbbox((MARGIN, MARGIN), label_text, font=label_font, anchor="la")
    _assert_within_canvas(label_bbox, "state label")
    draw.text((MARGIN, MARGIN), label_text, font=label_font, fill=ink_idx, anchor="la")

    tag_bbox = draw.textbbox((WIDTH - MARGIN, MARGIN), tag_text, font=tag_font, anchor="ra")
    _assert_within_canvas(tag_bbox, "top-right tag")
    draw.text((WIDTH - MARGIN, MARGIN), tag_text, font=tag_font, fill=ink_idx, anchor="ra")


def _illustration_over_pixel_cap(path):
    """Render-path counterpart of `illustrations.validate_illustration_file()`'s
    header-first pixel cap (T-03-03-01 / T-03.1-05-01): return `True` when
    `path`'s PNG header declares more than `illustrations.ILLUSTRATION_MAX_PIXELS`
    pixels, or when the header cannot even be read (missing, garbage,
    unreadable) - a file this plan's caller should move past rather than
    attempt to decode. `Image.open()` is lazy - it parses the header
    without decoding pixel data - which is the whole point: this check
    never triggers a full decode.

    Deliberately checks only the pixel count, not
    `validate_illustration_file()`'s other vendor-time quality rules
    (minimum width, landscape orientation, alpha presence) - those are
    hand-off gates for a human reviewing new art, and must never cause a
    live poll cycle to drop an otherwise-legitimate illustration. Never
    raises, for any input.
    """
    try:
        with Image.open(path) as img:
            width, height = img.size
            return (width * height) > illustrations.ILLUSTRATION_MAX_PIXELS
    except Exception:
        return True


def _load_illustration_safely(path, target_w):
    """Return a resized RGBA image loaded from `path`, degrading through an
    ordered candidate ladder - `path` first, then
    `illustrations.generic_fallback_path()` - and returning `None` once the
    ladder is exhausted. Never raises, for any input, including `None`.

    This restores the degradation ladder 03-03-PLAN.md's must-have and
    threat T-03-03-02 specified, whose original home
    (`draw_silhouette()`'s enclosing try/except) was removed by the
    D-25/D-26 two-flight redesign and never replaced (03-VERIFICATION.md).
    The last resort is no longer a redrawn silhouette but D-08's
    `generic-fallback.png`, and then "no illustration at all" - matching
    the already-correct missing-directory degradation.

    `_load_illustration_safely(None, w)` behaves exactly as today's
    `select_illustration()` returning `None` did end to end: the generic
    fallback is attempted and, if it is absent, the illustration is
    skipped.
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


def _resize_illustration(path, target_w):
    """Load a vendored per-airline illustration PNG (real alpha channel,
    see HANDOFF.md) and resize it to `target_w` px wide, preserving its
    source aspect ratio. Returns a fresh "RGBA" image.
    """
    with Image.open(path) as source:
        rgba = source.convert("RGBA")
        src_w, src_h = rgba.size
        target_h = max(1, round(target_w * src_h / src_w))
        return rgba.resize((target_w, target_h), Image.LANCZOS)


def draw_illustration(canvas, resized_rgba, left, top):
    """Composite an already-resized real illustration (from
    `_resize_illustration()`) onto `canvas` at (`left`, `top`). Full-color,
    dithered to the panel's real 6-color palette via
    `dither.dither_to_full_panel_palette()` - unlike the retired flat-
    silhouette path this replaces, the illustration keeps its real livery
    colors (D-25). D-24: never mirrored - the caller always passes the
    vendored file exactly as resized, regardless of departing/arriving
    state.

    03-RESEARCH.md Pitfall 2 (verified this session): a soft/gradient alpha
    mask blends palette INDEX INTEGERS during paste(), not colors, and
    produces illegal in-between indices - the alpha channel is hard-
    thresholded to strictly binary before paste().

    Returns the composited illustration's absolute bounding box
    (left, top, right, bottom).
    """
    w, h = resized_rgba.size
    rgb = resized_rgba.convert("RGB")
    quantized = dither.dither_to_full_panel_palette(rgb)
    alpha = resized_rgba.getchannel("A").point(lambda p: 255 if p > 127 else 0)
    canvas.paste(quantized, (int(left), int(top)), mask=alpha)
    return (left, top, left + w, top + h)


def _flight_line1_text(flight, state, route):
    """`"{callsign} to|from {city}"`, or bare `callsign` when `route` has no
    city for this state. This is not only a full enrichment miss (D-06,
    quick task 260827-hyy): `route` may legitimately be an airline-only
    route (`enrich.resolve_route()`'s `"airline_only"` source /
    `enrich.airline_only_route()`) that carries a real airline name but
    `None` for every city field - in that case line 1 correctly stays the
    bare callsign, because the origin/destination really are unknown; it
    does not fabricate a city from the callsign's ICAO prefix. D-26:
    ordinary lowercase "to"/"from" as sentence text, not the old tracked-
    caps Label-role prefix.
    """
    callsign = flight.get("callsign") or (flight.get("hex") or "").upper() or "?"
    city = enrich.city_for_state(route, state) if route is not None else None
    if city:
        direction = "to" if state == runway_config.STATE_DEPARTING else "from"
        return "%s %s %s" % (callsign, direction, city)
    return callsign


# Friendly human-readable labels for the ICAO type designators detect.py's
# aircraft_type field can carry (03.1-02), closing D-26's original
# `{airline} · {aircraft_type}` brief with a legible label rather than a raw
# code (P-02: neo/MAX variants are named explicitly, not collapsed to the
# base family - more informative, cosmetic, and reversible per CONTEXT.md's
# Claude's Discretion). Covers every designator in
# illustrations._TYPE_SHAPE_BUCKETS; a designator present in that bucket
# table but absent here is allowed and simply renders the airline name
# alone via _flight_line2_text()'s fallback - not every ICAO code needs a
# friendly label for line 2 to degrade safely.
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

# P-01: a presentation-only display alias for the one carrier that
# rebranded in 2013.
#
# SUPERSEDED (quick task 260827-kih, 2026-08-27, QT-kih-D-08): this entry
# is retained unchanged as a defensive no-op, not as the live presentation
# path. `enrich.correct_airline_name()` now corrects this carrier's
# `airline_name` upstream, inside `lookup_route()`'s single seam - every
# route that reaches `_flight_line2_text()` through the normal
# `enrich.resolve_route()` path already carries the corrected string "Air
# Corsica", so the alias below can no longer be triggered by a live route.
# It stays only for a hand-built route dict (e.g. a test fixture, or a
# future caller that bypasses `enrich.py` entirely) that still carries the
# literal upstream string "CCM Airlines" - display_airline_name() still
# resolves that correctly. No rendering logic, table value, or existing
# check was altered by this session.
_AIRLINE_DISPLAY_ALIASES = {
    "CCM Airlines": "Air Corsica",
}


def display_airline_name(airline_name):
    """Return the presentation-only display name for `airline_name` (P-01):
    the aliased brand name when one exists, otherwise `airline_name`
    unchanged. Returns `airline_name` unchanged for any non-string or
    falsy value. Never raises.
    """
    if not isinstance(airline_name, str) or not airline_name:
        return airline_name
    return _AIRLINE_DISPLAY_ALIASES.get(airline_name, airline_name)


def _flight_line2_text(route, aircraft_type=None):
    """`"{airline} · {friendly type label}"`, closing D-26's original brief
    now that real per-flight type data exists (detect.py's `aircraft_type`
    field, 03.1-02) and a type-to-shape classifier exists to size the art
    (illustrations.classify_aircraft_type(), 03.1-03). The displayed
    airline name is resolved through `display_airline_name()` (P-01) - a
    presentation-only alias that never reaches illustration selection.

    Falls back to the display name alone when `aircraft_type` is missing
    or has no friendly label in `_TYPE_DISPLAY_LABELS` - an unlabelled or
    absent type never fabricates a label and never renders an empty
    separator. Falls back to `ROUTE_FALLBACK_TEXT` only when no route was
    supplied, or the supplied route has no airline name at all - regardless
    of what type was detected. Since quick task 260827-hyy (D-06), that
    condition is strictly narrower than "adsbdb missed": a route may be
    airline-only (`enrich.resolve_route()`'s `"airline_only"` source /
    `enrich.airline_only_route()` - adsbdb had nothing, but the callsign's
    ICAO prefix identified the carrier) and still carry a real
    `airline_name`, in which case this function composes `"{airline} ·
    {type label}"` exactly as it would for a full adsbdb hit.
    `ROUTE_FALLBACK_TEXT` now fires only when *neither* enrichment source
    produced an airline.

    Never raises for a non-dict route, a non-string airline name, or a
    hostile aircraft type.
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


def draw_main_text_block(canvas, flight, state, route, main_bbox, ink_idx):
    """D-26 main flight text: two centred lines starting at
    `main_bbox`'s bottom minus `MAIN_TEXT_OVERLAP_PX` (a deliberate slight
    overlap - the vendored illustration files have no transparent bottom
    padding of their own, confirmed via `Image.getbbox()` during the live
    sketch pass, so this is the only way to get the text as close as
    confirmed). Returns (line1_bbox, line2_bbox).
    """
    draw = ImageDraw.Draw(canvas)
    center_x = WIDTH // 2
    safe_width = SAFE_BOX[2] - SAFE_BOX[0]

    line1_text = _flight_line1_text(flight, state, route)
    line2_text = _flight_line2_text(route, flight.get("aircraft_type"))

    line1_font = fit_text_size(PT_SERIF_REGULAR, MAIN_LINE1_FONT[1], line1_text, safe_width, MAIN_LINE1_MIN_SIZE)
    line2_font = fit_text_size(PT_SERIF_REGULAR, MAIN_LINE2_FONT[1], line2_text, safe_width, MAIN_LINE2_MIN_SIZE)

    top_y = main_bbox[3] - MAIN_TEXT_OVERLAP_PX
    line1_bbox = draw.textbbox((center_x, top_y), line1_text, font=line1_font, anchor="ma")
    _assert_within_canvas(line1_bbox, "main flight text line 1")
    draw.text((center_x, top_y), line1_text, font=line1_font, fill=ink_idx, anchor="ma")

    line2_top = line1_bbox[3] + MAIN_LINE_GAP_PX
    line2_bbox = draw.textbbox((center_x, line2_top), line2_text, font=line2_font, anchor="ma")
    _assert_within_canvas(line2_bbox, "main flight text line 2")
    draw.text((center_x, line2_top), line2_text, font=line2_font, fill=ink_idx, anchor="ma")

    return line1_bbox, line2_bbox


def draw_previous_text_block(canvas, flight, state, route, prev_bbox, ink_idx):
    """D-26 previous flight text: two right-aligned lines, right-aligned to
    `prev_bbox`'s own right edge (the previous illustration's right edge,
    itself right-aligned to the main illustration's right edge). Line 1
    starts `PREVIOUS_TEXT_GAP_PX` below the illustration's bottom; line 2
    starts `PREVIOUS_LINE_GAP_PX` below line 1's own TOP, not its bottom
    (D-26's tighter confirmed stacking). No `PREVIOUS ·` prefix - explicitly
    removed after the live sketch pass. Returns (line1_bbox, line2_bbox).
    """
    draw = ImageDraw.Draw(canvas)
    right_x = prev_bbox[2]
    available_width = right_x - SAFE_BOX[0]

    line1_text = _flight_line1_text(flight, state, route)
    line2_text = _flight_line2_text(route, (flight or {}).get("aircraft_type"))

    line1_font = fit_text_size(PT_SERIF_REGULAR, PREVIOUS_LINE1_FONT[1], line1_text, available_width, PREVIOUS_LINE1_MIN_SIZE)
    line2_font = fit_text_size(PT_SERIF_REGULAR, PREVIOUS_LINE2_FONT[1], line2_text, available_width, PREVIOUS_LINE2_MIN_SIZE)

    top_y = prev_bbox[3] + PREVIOUS_TEXT_GAP_PX
    line1_bbox = draw.textbbox((right_x, top_y), line1_text, font=line1_font, anchor="ra")
    _assert_within_canvas(line1_bbox, "previous flight text line 1")
    draw.text((right_x, top_y), line1_text, font=line1_font, fill=ink_idx, anchor="ra")

    line2_top = line1_bbox[1] + PREVIOUS_LINE_GAP_PX
    line2_bbox = draw.textbbox((right_x, line2_top), line2_text, font=line2_font, anchor="ra")
    _assert_within_canvas(line2_bbox, "previous flight text line 2")
    draw.text((right_x, line2_top), line2_text, font=line2_font, fill=ink_idx, anchor="ra")

    return line1_bbox, line2_bbox


def _build_empty_canvas(runway_id=device_config.DEFAULT_RUNWAY_ID, source_fault=False, battery_low=False):
    """Build the empty-state canvas ("Watching Runway 3" by default; the
    heading follows `runway_id` since CFG-12).

    `battery_low` (D-04/D-06): when True, draws the bottom-left battery-low
    icon in EMPTY_INK - a low-battery reading is a device-health fact
    independent of whether an aircraft is currently detected, so the icon
    renders here too.

    `source_fault` (CFG-05): when True, draws the bottom-centre source-fault
    badge, also in EMPTY_INK. The two indicators are independent and may
    both be shown at once - they occupy horizontally disjoint parts of the
    same bottom band.
    """
    canvas = pf.new_canvas(IDX_WHITE)
    draw = ImageDraw.Draw(canvas)
    heading_text = empty_heading_text(runway_id)
    body_font = _font(EMPTY_BODY_FONT)
    center_x = WIDTH // 2
    safe_width = SAFE_BOX[2] - SAFE_BOX[0]

    # CFG-12: the heading is now runway-dependent and not a fixed,
    # pre-measured string - it gets fit_text_size()'s shrink treatment
    # (the same one long route/airline text already receives) rather than
    # a bare _font() lookup, so a longer runway label shrinks instead of
    # tripping the safe-box assertion below.
    heading_font = fit_text_size(PT_SERIF_BOLD, EMPTY_HEADING_FONT[1], heading_text, safe_width, EMPTY_HEADING_MIN_SIZE)

    heading_ascent, heading_descent = heading_font.getmetrics()
    heading_height = heading_ascent + heading_descent

    body_lines = _wrap_text(body_font, EMPTY_BODY_TEXT, safe_width)
    body_ascent, body_descent = body_font.getmetrics()
    body_line_height = body_ascent + body_descent

    total_height = heading_height + SPACE_SM + len(body_lines) * body_line_height
    start_y = (HEIGHT - total_height) // 2

    heading_bbox = draw.textbbox((center_x, start_y), heading_text, font=heading_font, anchor="ma")
    _assert_in_safe_box(heading_bbox, "empty-state heading")
    draw.text((center_x, start_y), heading_text, font=heading_font, fill=EMPTY_INK, anchor="ma")

    y = start_y + heading_height + SPACE_SM
    for line in body_lines:
        line_bbox = draw.textbbox((center_x, y), line, font=body_font, anchor="ma")
        _assert_in_safe_box(line_bbox, "empty-state body line")
        draw.text((center_x, y), line, font=body_font, fill=EMPTY_INK, anchor="ma")
        y += body_line_height

    # CFG-05: the source-fault badge is visible whichever state the panel
    # is in, including the empty state - the empty canvas uses EMPTY_INK,
    # matching every other element it already draws.
    if source_fault:
        draw_source_fault_badge(canvas, EMPTY_INK)

    if battery_low:
        draw_battery_icon(canvas, draw, EMPTY_INK)

    return canvas


_LEGAL_PANEL_INDICES = {IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN}


def _assert_legal_palette(canvas, bg_idx):
    """Guard rail: every index anywhere on the panel is one of the 6 legal
    Spectra 6 panel indices, and `bg_idx` (the state's flat background
    fill, D-21) is the single most common index on the panel.

    This replaces 03-02's spatially-scoped `_assert_palette_contract()`
    (retired along with the dithered mood background and quiet-zone text
    compositing it protected): a real illustration's own livery colors may
    now legitimately use every other legal index anywhere on the canvas, so
    there is no more "only {bg_idx, IDX_WHITE} outside one bbox" contract to
    check - just "no illegal index anywhere, and the flat field is
    provably dominant."
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

    `battery_low` (D-04/D-06): when True, draws the bottom-left battery-low
    icon in the state's own ink after the previous-flight card, before the
    closing palette guard rail.

    `source_fault` (CFG-05): when True, draws the bottom-centre source-fault
    badge in that same ink. Both indicators resolve their ink through the
    active theme's `state_ink_index()` (CFG-01), so neither can introduce an
    index outside the current theme's palette.
    """
    if state not in STATE_BACKGROUND:
        raise ValueError("unknown state %r (expected 'departing', 'arriving', or 'empty')" % (state,))
    bg_idx = state_background_index(state, theme_id=theme_id)
    fg_idx = state_ink_index(state, theme_id=theme_id)

    # D-21: flat single-color background field - no dithered mood gradient.
    canvas = pf.new_canvas(bg_idx)

    # D-26: thin frame, inset ~2.5% of canvas width from every edge.
    draw_frame(canvas, fg_idx)

    # D-26 top row: state label top-left, CFG-12 runway tag top-right, both
    # at the existing MARGIN inset (inside the frame, not on it).
    draw_top_labels(canvas, state, fg_idx, runway_id=runway_id)

    # D-25/D-26 main flight: the current detection's real per-airline
    # illustration, always nose-left (D-24 - no mirroring).
    inner_width = WIDTH * (1 - 2 * FRAME_INSET_FRAC)
    main_w = round(inner_width * MAIN_ILLUSTRATION_WIDTH_FRAC)
    main_top = round(HEIGHT * MAIN_ILLUSTRATION_TOP_FRAC)

    main_path = illustrations.select_illustration(route, flight.get("aircraft_type"))
    main_bbox = None
    main_resized = _load_illustration_safely(main_path, main_w)
    if main_resized is not None:
        main_left = (WIDTH - main_resized.size[0]) // 2
        main_bbox = draw_illustration(canvas, main_resized, main_left, main_top)
        _assert_within_canvas(main_bbox, "main aircraft illustration")
        draw_main_text_block(canvas, flight, state, route, main_bbox, fg_idx)

    # D-25/D-26 previous flight: a real second flight card - the detection
    # immediately preceding this one (poll_loop.py's two-deep history).
    # Same nose-left convention as the main illustration, no mirroring.
    if previous_flight is not None and main_bbox is not None:
        prev_path = illustrations.select_illustration(previous_route, (previous_flight or {}).get("aircraft_type"))
        prev_w = round((main_bbox[2] - main_bbox[0]) * PREVIOUS_ILLUSTRATION_WIDTH_FRAC)
        prev_resized = _load_illustration_safely(prev_path, prev_w)
        if prev_resized is not None:
            prev_h = prev_resized.size[1]
            prev_left = main_bbox[2] - prev_resized.size[0]
            prev_top = round(HEIGHT * PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC - prev_h / 2)
            prev_bbox = draw_illustration(canvas, prev_resized, prev_left, prev_top)
            _assert_within_canvas(prev_bbox, "previous aircraft illustration")
            draw_previous_text_block(canvas, previous_flight, previous_state, previous_route, prev_bbox, fg_idx)

    # CFG-05: the source-fault badge, drawn last so it sits on top of
    # everything else, using the state's own resolved ink index.
    if source_fault:
        draw_source_fault_badge(canvas, fg_idx)

    if battery_low:
        draw_battery_icon(canvas, ImageDraw.Draw(canvas), fg_idx)

    # Guard rail: every index on the panel is legal, and the flat
    # background field is provably dominant.
    _assert_legal_palette(canvas, bg_idx)

    return canvas


def build_canvas(
    flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False,
):
    """Return the pre-pack "P"-mode canvas for `flight` in `state`
    ("departing" / "arriving" / "empty"). Public (not `_build_canvas`) so
    callers - notably server/test_render.py's anti-aliasing assertions,
    which read Image.getcolors() directly - never have to reach into
    private render state.

    `route` is the normalised dict produced by either
    `server.plane.enrich.lookup_route()` (a full route: airline + origin +
    destination) or, since quick task 260827-hyy,
    `server.plane.enrich.airline_only_route()` (D-03/D-06: airline name
    only, the four city/IATA fields `None`) - `poll_loop.py` chooses between
    them via `server.plane.enrich.resolve_route()`. `route` is `None` on a
    full enrichment miss (neither source resolved anything) or for the
    empty state.

    `previous_flight`/`previous_route`/`previous_state` (D-25/D-26) are the
    detection immediately preceding `flight`, or all None if none exists
    yet (e.g. the very first detection since the state directory was last
    empty) - the previous flight card is simply omitted in that case.
    Ignored for the empty state, which has no flight to enrich.

    `theme_id` (CFG-01) selects the DEPARTING/ARRIVING background and ink
    colours from `server/device_config.py`'s `THEMES` registry; an
    unrecognised id degrades to the default theme rather than raising.
    Ignored for the empty state, which is always White/Black.

    `runway_id` (CFG-12) selects the top-right tag and (for the empty
    state) the heading text from `device_config`'s `RUNWAYS` registry; an
    unrecognised id degrades to the default runway rather than raising.

    `source_fault` (CFG-05) draws a small alert badge pointing at the
    companion page when true. It must be set only when every ADS-B source
    the server queries has failed (`poll_loop.py`'s classification of
    `detect.poll_current_aircraft()`'s diagnostics dict) - never merely
    because no aircraft was selected, which is Orly's ordinary quiet state
    and firing on it is exactly the false-alarm trap
    `.planning/seeds/on-device-fault-icon.md` rejects.

    `battery_low` (D-04/D-06): when True, draws the bottom-left
    battery-low icon - in every one of the three states, including empty.
    Independent of `source_fault`; both may be true at once.
    """
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
    source_fault=False, battery_low=False,
):
    """Return a packed 960,000-byte panel for `flight` (the normalised dict
    from detect.select_runway3_aircraft(), or None) in `state`
    ("departing" / "arriving" / "empty").

    `state` is the return value of a server.plane.runway_config call
    (poll_loop.py never hardcodes it) - server.plane.runway_config.py's
    STATE_DEPARTING/STATE_ARRIVING constants are the exact strings
    "departing"/"arriving" this function and build_canvas() key their
    per-state dicts on.

    `route`/`previous_flight`/`previous_route`/`previous_state`/`theme_id`/
    `runway_id`/`source_fault`/`battery_low` are passed straight through to
    build_canvas() (D-25/D-26, CFG-01, CFG-12, CFG-05, D-04/D-06) - see
    build_canvas()'s own docstring for the full contract of each, including
    what `route` may now be (a full route or, since quick task 260827-hyy,
    an airline-only route) and `battery_low`'s per-state behaviour.
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
    )
    return pf.pack_panel(canvas)


# Manual-QA-only sample routes (02-04, extended D-26) - server/plane/render.py's
# CLI has no live enrichment lookup of its own (that's poll_loop.py's job);
# these are plausible-looking hits so `--preview` without `--no-route` shows
# the resolved-route text layout rather than always previewing the fallback.
_PREVIEW_ROUTE = {
    "airline_name": "Air France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "JFK",
    "destination_city": "New York",
}
_PREVIEW_PREVIOUS_ROUTE = {
    "airline_name": "Vueling Airlines",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "BCN",
    "destination_city": "Barcelona",
}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=["departing", "arriving", "empty"], default="empty")
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
        "--preview-airline-only",
        action="store_true",
        help="Manual QA only (D-06, quick task 260827-hyy): preview the airline-only intermediate "
             "render state (airline known via the callsign's ICAO prefix, destination genuinely "
             "unknown - bare callsign on line 1, '{airline} · {type}' on line 2, the airline's own "
             "illustration). Takes precedence over --no-route when both are given.",
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
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    flight = None
    route = None
    previous_flight = None
    previous_route = None
    previous_state = None
    if args.state != "empty":
        flight = {"hex": args.hex, "callsign": args.callsign}
        # D-06 preview takes precedence over --no-route when both are given
        # (documented in --preview-airline-only's own help text above).
        if args.preview_airline_only:
            route = enrich.airline_only_route(_PREVIEW_ROUTE["airline_name"])
        elif args.no_route:
            route = None
        else:
            route = _PREVIEW_ROUTE
        if args.previous_callsign:
            previous_flight = {"hex": args.previous_hex, "callsign": args.previous_callsign}
            if args.preview_airline_only:
                previous_route = enrich.airline_only_route(_PREVIEW_PREVIOUS_ROUTE["airline_name"])
            elif args.no_route:
                previous_route = None
            else:
                previous_route = _PREVIEW_PREVIOUS_ROUTE
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
