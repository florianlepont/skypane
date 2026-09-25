#!/usr/bin/env python3
"""Panel renderer for the plane view: departure and arrival cards for the
watched runway, plus an empty state.

Every draw call goes directly onto a "P"-mode canvas with an integer
palette-index fill, never an RGB tuple and never an RGB compose-then-
quantize step for flat fills - this keeps anti-aliasing off everywhere
except the real per-airline illustrations, which are deliberately
full-color and dithered.

Layout:

- The active-state background is a flat single-color fill
  (`panel_format.new_canvas(bg_idx)`) - no dithered gradient.
- Aircraft illustrations are never mirrored. Every vendored illustration
  file is nose-left by convention (`illustrations.ILLUSTRATION_SOURCE_NOSE`)
  and is drawn exactly as vendored, in both departing and arriving states -
  real, detailed, full-color art does not mirror convincingly. The
  background color and the state label text are the only remaining
  departing/arriving cues.
- Two real flight cards share one canvas: the current detection (large,
  upper-center) and the immediately-preceding detection (smaller,
  bottom-right, right-aligned to the main illustration's own right edge).
  Both use their own real per-airline illustration file
  (`illustrations.select_illustration()`), full-color, Floyd-Steinberg-
  dithered to the panel's 6-color palette via
  `dither.dither_to_full_panel_palette()` - never simplified to a flat
  silhouette. No quiet-zone rectangles anywhere: the flat background needs
  no protection against text sitting on a dithered pixel.
- Every text role uses PT Serif Bold, except on the White theme (never
  dithered), where Regular is substituted because Bold's only job -
  resisting dithered speckle - does not apply there.

**Colour**: the panel's DEPARTING/ARRIVING background and ink colours are
on-screen-confirmed values (`server/panel_format.py`'s "confirmed against
on-screen previews only" note), not yet calibrated against real glass. A
theme picker selects between the registry entries in
`server/device_config.py`'s `THEMES` (`white` is the default).

The 64px SAFE_BOX margin is enforced for the top-row labels, pinned to the
MARGIN inset. It is deliberately **not** enforced for the frame, the
illustrations, or the flight text blocks below them, which sit at a
tighter ~2.5%-of-width inset (~30px), inside the 64px band. This has only
been confirmed against on-screen preview PNGs, not against the real
physical bezel.

Usage (manual QA):
    server/.venv/bin/python3 server/plane/render.py --state empty --out /tmp/panel.bin
    server/.venv/bin/python3 server/plane/render.py --state arriving --callsign AF1380 \
        --out /tmp/panel.bin --preview /tmp/panel.preview.png
    server/.venv/bin/python3 server/plane/render.py --state departing --callsign AF1380 \
        --previous-callsign VY1234 --out /tmp/panel.bin --preview /tmp/panel.preview.png

Reproducible on-glass forcing commands, so a verification session never
needs a hand-built dict or an inline Python snippet typed on a production
host:
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

# --- Spacing scale ---------------------------------------------------------
SPACE_XS = 8
SPACE_SM = 16
SPACE_MD = 32
SPACE_LG = 64

# MARGIN is the top-row labels' inset. See the module docstring for why
# this is not a blanket margin for every element.
MARGIN = SPACE_LG
SAFE_BOX = (MARGIN, MARGIN, WIDTH - MARGIN, HEIGHT - MARGIN)  # (64, 64, 1136, 1536)

# --- Typography --------------------------------------------------------
FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")
)
PT_SERIF_REGULAR = os.path.join(FONT_DIR, "PTSerif-Regular.ttf")
PT_SERIF_BOLD = os.path.join(FONT_DIR, "PTSerif-Bold.ttf")

# Confirmed sizes per role. (font_path, size, weight) - weight is
# documentation only (the path already selects the correct static weight
# file). Every active-state role's *base* weight is Bold: the heavier
# stroke is what carries legibility against a dithered state background.
#
# `_role_font()` / `_role_fit_text_size()` below substitute Regular for
# these role tuples' path specifically when `bg_idx == IDX_WHITE`, because
# Bold's only job - resisting dithered speckle - never applies there (White
# is never dithered); every dithered theme keeps Bold. These tuples
# themselves stay the Bold specification and are never read directly by
# the draw_*() functions below; always go through `_role_font()` /
# `_role_fit_text_size()`, which resolve the weight from `bg_idx`.
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
# The empty-state heading is runway-dependent (empty_heading_text()) and
# therefore not a fixed, pre-measured string - it gets the same
# fit_text_size() shrink treatment as the long route/airline text above,
# floored well above illegibility. All three registry headings are
# deliberately short, so this floor is not expected to bind in practice -
# it exists only as a guard rail should a longer heading ever be added.
EMPTY_HEADING_MIN_SIZE = 48
_FIT_STEP_PX = 2

# --- Colour (state-scoped) - keyed by runway_config's STATE_* constants
# (not bare string literals) so the two modules cannot drift apart. --------
#
# STATE_BACKGROUND/STATE_INK are retained below as module-level constants,
# redefined from the default theme's own server/device_config.py registry
# entry, ONLY because server/test_render.py's pre-existing checks read them
# directly. New code must never read these two dicts directly - call
# state_background_index()/state_ink_index() instead, which resolve
# through device_config.THEMES, the single registry the companion Config
# page's picker also reads. Do not delete these constants - their values
# are computed directly from `device_config.DEFAULT_THEME_ID` at import
# time, so they always agree with whatever the registry currently calls
# the default.
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
    "arriving") under `theme_id`. `theme_id` is normalised through
    `device_config.normalise_theme_id()` first, so an unrecognised,
    hostile, or stale theme id silently degrades to the default theme
    rather than ever reaching a dict lookup - an unrecognised *theme* is
    forgiving. `state` is intentionally NOT normalised the same way: an
    unknown state is a real caller-bug detector and must stay loud - every
    caller in this module only ever reaches this function after
    `_build_active_canvas()`'s own `state not in STATE_BACKGROUND` guard
    has already validated it.
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
    """Return the top-right tag string for `runway_id`, normalised
    through `device_config.normalise_runway_id()` first so an unrecognised,
    hostile, or stale runway id silently degrades to the default runway's
    tag rather than raising - matching state_background_index()'s
    "unrecognised registry id is forgiving" contract.
    """
    runway_id = device_config.normalise_runway_id(runway_id)
    return device_config.runway_tag_text(runway_id)


def empty_heading_text(runway_id=device_config.DEFAULT_RUNWAY_ID):
    """Same contract as runway_tag_text(), for the empty-state heading."""
    runway_id = device_config.normalise_runway_id(runway_id)
    return device_config.runway_empty_heading(runway_id)


# EMPTY_HEADING_TEXT/TOP_RIGHT_TAG_TEXT are retained below as module-level
# constants, redefined from the default runway's own device_config.py
# registry entry, ONLY because server/test_render.py's pre-existing checks
# read them directly. New code must never read these two constants
# directly - call empty_heading_text()/runway_tag_text() instead.
EMPTY_HEADING_TEXT = empty_heading_text(device_config.DEFAULT_RUNWAY_ID)

# The empty state's own already-established ink (its heading and body copy
# both already used the bare IDX_BLACK literal) - named so the battery icon
# can share "each state's own ink" structurally, not by comment. The
# battery icon renders in all three states, including empty, since a
# low-battery reading is a device-health fact independent of whether an
# aircraft is currently detected.
#
# The empty state is deliberately NOT theme-dependent: it is always
# White/Black, so this stays a bare constant rather than resolving through
# state_ink_index(). The source-fault badge shares it for the same reason.
EMPTY_INK = IDX_BLACK
# Two authored sentences, each a full stop, the break falling before "the
# display" rather than wherever the measured width happens to land.
# EMPTY_BODY_TEXT is their joined form, the single string the copy is
# asserted against. The builder wraps each sentence on its own, so the
# break is honoured while the width safety net still catches a line that
# cannot fit.
EMPTY_BODY_LINES = (
    "No aircraft detected yet.",
    "The display updates the moment one is.",
)
EMPTY_BODY_TEXT = " ".join(EMPTY_BODY_LINES)
TOP_RIGHT_TAG_TEXT = runway_tag_text(device_config.DEFAULT_RUNWAY_ID)
ROUTE_FALLBACK_TEXT = "Route unavailable"

# The scheduled-quiet-hours screen's locked English copy - all-caps
# heading, "Back at HH:MM" body, matching every other panel string
# (DEPARTING/ARRIVING, ORY · RWY 3). Do not localise; every other panel
# string is English.
QUIET_HOURS_HEADING_TEXT = "QUIET HOURS"
QUIET_HOURS_BODY_TEMPLATE = "Back at %s"

# The remote display-off screen's locked English copy. Unlike
# QUIET_HOURS_BODY_TEMPLATE above, this body is a plain string constant,
# not a `%`-template - a manual toggle has no end time, so there is no
# value to interpolate (no "Back at HH:MM", no countdown, no duration).
# The copy also deliberately withholds any of the fault vocabulary
# SOURCE_FAULT_TEXT below already owns ("unavailable", "error", "offline",
# "disconnected") - this is an intentional operator action, not a genuine
# fault, and blurring the two would be ambiguous. Do not localise.
DISPLAY_OFF_HEADING_TEXT = "DISPLAY OFF"
# Two authored sentences, the break falling after "page." rather than
# wherever the measured width happens to land. DISPLAY_OFF_BODY_TEXT stays
# the joined form so the locked copy is still one string to assert
# against. _build_display_off_canvas() wraps each sentence individually,
# so the semantic break is honoured while the width safety net still
# catches a line that cannot fit.
DISPLAY_OFF_BODY_LINES = (
    "Switched off from the companion page.",
    "Turn it back on there anytime.",
)
DISPLAY_OFF_BODY_TEXT = " ".join(DISPLAY_OFF_BODY_LINES)

# The BATTERY EMPTY hold screen's locked English copy, following
# DISPLAY_OFF_HEADING_TEXT/DISPLAY_OFF_BODY_LINES' own convention exactly -
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

# The NO CONNECTION hold screen's locked English copy - same fixed-string
# convention as DISPLAY_OFF_*/BATTERY_EMPTY_*. This screen is unique among
# the four: the server never renders it - the firmware draws it entirely
# on its own (firmware/tools/gen_fault_screen.py bakes this exact copy
# into firmware/main/fault_screen_mask.h at build time), so changing
# either sentence here requires regenerating that header or
# server/test_fault_screen_mask.py's drift test fails. The second sentence
# stays true because the device retries on its own backoff schedule
# (app_main.c's fail_and_sleep()) and the server's real picture returns
# automatically on the first healthy wake after recovery - no user action
# required.
NO_CONNECTION_HEADING_TEXT = "NO CONNECTION"
NO_CONNECTION_BODY_LINES = (
    "The frame can't reach its server.",
    "It will try again on its own.",
)
NO_CONNECTION_BODY_TEXT = " ".join(NO_CONNECTION_BODY_LINES)

# --- The dimmed hold composition ------------------------------------------
# Shared by the two "resting on purpose" screens, DISPLAY OFF and QUIET
# HOURS, and drawn by one routine (_build_dimmed_hold_canvas()) so the two
# share their art direction by construction rather than by copy.
#
# The composition: a glyph, then a tracked label in the frame's own label
# voice over a short hairline rule, then the body, on a dimmed field
# (Black dithered toward White, the Grey theme's own recipe, white ink).
# Validated on real Spectra 6 glass: the field reads as a soft even grey,
# the Regular white body holds at 40px, and the Bold-class label, rule and
# glyph are crisp.
#
# The field is the load-bearing choice, and it makes the hold screens a
# system: DARK means the frame is resting on purpose (off, quiet hours);
# WHITE means it is working (the empty state, the flight boards). The two
# dark screens then tell apart by glyph - power ring versus crescent -
# which carries further across a room than two bold headings ever did.
#
# Bold for the label, not Regular: thin white strokes drown in dither
# noise, which is why the Grey theme itself ships `weight: bold`. The body
# is Regular at 40px (EMPTY_BODY_FONT) - confirmed legible on glass.
DIMMED_FIELD_IDX = IDX_BLACK
DIMMED_INK = IDX_WHITE
DIMMED_LABEL_FONT = (PT_SERIF_BOLD, 40, 700)
DIMMED_LABEL_TRACKING_PX = 10
DIMMED_RULE_WIDTH_PX = 120
DIMMED_RULE_HEIGHT_PX = 4
DIMMED_BODY_FONT = EMPTY_BODY_FONT
DIMMED_BODY_LINE_GAP_PX = 6

# The source-fault alert badge's caption - short, English, and pointing at
# the companion page, which is where an all-sources-down outage is
# actually diagnosed. SOURCE_FAULT_GLYPH_PX is deliberately small - see
# draw_source_fault_badge()'s own docstring for why the badge's area must
# stay small enough that _assert_legal_palette()'s background-dominance
# assertion still holds.
SOURCE_FAULT_TEXT = "ADS-B source unavailable — check the companion page"
SOURCE_FAULT_GLYPH_PX = 28

# --- Frame + layout geometry ------------------------------------------
FRAME_INSET_FRAC = 0.025  # ~2.5% of canvas WIDTH, inset from every edge
FRAME_STROKE_PX = 2

MAIN_ILLUSTRATION_WIDTH_FRAC = 0.87  # of the inner (post-frame-inset) canvas width
# Of canvas height. This is a fraction of the illustration's PAINTED
# CONTENT centre, not its source rectangle: top transparent padding varies
# per vendored file (6-124px across the illustration set), so anchoring on
# the rectangle top would drift the aircraft's visible vertical centre by
# over 100px depending purely on which airline is flying. Anchoring on
# painted-pixel centre keeps every illustration file landing on the same
# row (sub-pixel spread, measured across the full illustration set).
# SIZING still derives from `.rect` (see the sizing note on the previous
# card's own placement, `_build_active_canvas()` below); only POSITION
# follows painted pixels.
MAIN_ILLUSTRATION_CENTER_Y_FRAC = 0.4006
MAIN_LINE_GAP_PX = 8  # gap between main line 1's bottom and line 2's top

PREVIOUS_ILLUSTRATION_WIDTH_FRAC = 0.57  # of the MAIN illustration's own rendered width
# Of canvas height. Anchored on the previous card's painted-pixel centre
# rather than its source rectangle: the drop-shadow band makes bottom
# padding always exceed top padding, so centring the rectangle would push
# the visible aircraft consistently high by a per-file amount.
PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC = 0.7528
PREVIOUS_LINE_GAP_PX = 34  # line 2's top below line 1's own TOP (not bottom)

# The previous card's two text lines are right-aligned this many pixels
# LEFT of the aircraft's measured opaque right edge
# (prev_placement.content[2]) - an intentional optical correction, not a
# fix to the measurement itself. The aircraft's rightmost painted pixel
# typically sits on a thin raked tail-fin tip, not on the visual mass of
# the fuselage the eye actually anchors on, so text right-aligned to the
# true edge reads as floating slightly right of where the aircraft "is".
PREVIOUS_TEXT_LEFT_OFFSET_PX = 20

# --- Aircraft-to-text gaps ---------------------------------------------
# Both constants are measured from the illustration's OPAQUE-PIXEL bottom
# edge (`IllustrationPlacement.content`), never from the source PNG's full
# rectangle: every vendored file carries a soft drop-shadow band
# (alpha 1..127) below the aircraft, which `draw_illustration()`
# hard-thresholds away (`p > 127`) and never paints. Measuring from the
# full rectangle instead would let the real aircraft-to-text gap vary by
# over 100px purely by which airline is flying, since the drop-shadow
# band's size differs per vendored file.
MAIN_TEXT_GAP_PX = 54  # main text top = main illustration's OPAQUE bottom + this
PREVIOUS_TEXT_GAP_PX = 47  # previous text top = its OPAQUE bottom + this

# --- Diagonal band geometry ---------------------------------------------
# Measured from the reference image via per-row pixel scanning + linear
# regression. A trapezoid, not a parallelogram: the top and bottom edges
# span different fractions of the canvas width. `BAND_SHIFT_FRAC` is the
# reference's own unshifted, as-measured position (0.0) - splitting the
# top-right tag (see `_BAND_TOP_LABEL_DIRECTION`/`draw_top_labels()`
# below) already clears both the shorter tag and the below-illustration
# text with margin, so no extra shift is needed. `BAND_BOT_LEFT_FRAC` is
# floored at 0.0 as a defensive guard against a future negative shift
# walking the polygon off-canvas.
BAND_SHIFT_FRAC = 0.0
BAND_TOP_LEFT_FRAC = 0.5818 + BAND_SHIFT_FRAC
BAND_TOP_RIGHT_FRAC = 0.8523 + BAND_SHIFT_FRAC
BAND_BOT_LEFT_FRAC = max(0.0, 0.0742 + BAND_SHIFT_FRAC)
BAND_BOT_RIGHT_FRAC = 0.4772 + BAND_SHIFT_FRAC


def draw_diagonal_band(canvas, band_idx, dithered=False):
    """Paint the diagonal trapezoid band directly onto `canvas`, in
    `band_idx`'s colour - flat or dithered ~40% toward White depending on
    `dithered`. `band_idx` must be one of the 6 legal `panel_format.IDX_*`
    values (never a bare integer), so `_assert_legal_palette()` downstream
    stays satisfied.

    MUST be called before any text/illustration drawing, so the band sits
    behind everything else on the canvas and illustrations occlude it
    naturally.

    Geometry is measured from the reference image - see the `BAND_*_FRAC`
    constants above.
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
    """The diagonal band's own left/right pixel edges at a given canvas
    `y` - the same linear interpolation `draw_diagonal_band()`'s polygon
    corners and `_band_center_x()` already use, factored out so a caller
    can also ask "how wide is the band here", not just "where is its
    centre". Returns (left_x, right_x) in pixels.
    """
    f = canvas_y / HEIGHT
    left_frac = BAND_TOP_LEFT_FRAC - (BAND_TOP_LEFT_FRAC - BAND_BOT_LEFT_FRAC) * f
    right_frac = BAND_TOP_RIGHT_FRAC - (BAND_TOP_RIGHT_FRAC - BAND_BOT_RIGHT_FRAC) * f
    return left_frac * w, right_frac * w


def _band_center_x(canvas_y, w):
    """The diagonal band's own horizontal centre at a given canvas `y` -
    used to centre the main text block INSIDE the trapezoid instead of
    beside it. The trapezoid's centreline shifts left as `y` increases (the
    same linear interpolation `draw_diagonal_band()`'s own polygon corners
    already use), so this is a function of `y`, not a constant.

    Callers must compute this ONCE per text block, at the block's top y,
    and reuse that single value for every line - recomputing it per line
    produces a visibly staggered column instead of one aligned centre (see
    `draw_main_text_block()`'s band branch).
    """
    left_x, right_x = _band_edges(canvas_y, w)
    return (left_x + right_x) / 2


# --- Battery-low icon geometry ------------------------------------------
# The two POSITION constants (LEFT/BOTTOM) derive from MARGIN. The four
# SIZE constants are a uniform round(original * 0.7) reduction of their
# former spacing-scale values, after the original (72x32-nominal) glyph
# read too large on the real Spectra 6 panel. Total bounding box is
# (64, 1514, 115, 1536) - see draw_battery_icon()'s docstring for the full
# geometry derivation.
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


def _tracked_text_width(font, text, tracking):
    """Return the total rendered advance of `text` at `font`, with `tracking`
    extra pixels inserted between every pair of adjacent glyphs (never after
    the last one - a single glyph carries no trailing tracking). 0.0 for an
    empty string.
    """
    if not text:
        return 0.0
    return sum(font.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def draw_tracked_text(draw, xy, text, font, fill, tracking=0):
    """Draw `text` glyph-by-glyph with `tracking` extra pixels of advance
    between each glyph - Pillow has no native letter-spacing/tracking API.
    `xy` is the top-left origin of the first glyph; callers wanting right-
    or centre-aligned tracked text should pre-compute the block width with
    `_tracked_text_width()` and offset `xy` accordingly. Returns the
    x-coordinate immediately after the last glyph drawn
    (`start_x + _tracked_text_width(...) + tracking`).

    `anchor="la"` is passed explicitly on each glyph draw because the test
    harness spies on the anchor kwarg, and leaving it implicit (Pillow's
    default for horizontal text is already "la") would make that assertion
    read `None`.
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
    """Resolve `weight` (`device_config.theme_weight()`'s return value,
    `"regular"` or `"bold"`) to the matching PT Serif static-weight file.

    Not derivable from `bg_idx` alone (08-06 on-glass finding, widened
    same session): the same palette index can back two different themes
    with two different weights - `IDX_BLACK` is both "black" (flat,
    Regular) and "grey" (dithered, Bold) - so the active theme's own
    `weight` field is threaded through explicitly by
    `_build_active_canvas()` rather than re-derived from the background
    index here. The empty state is untouched by this - it never calls
    this helper.
    """
    if weight == "regular":
        return PT_SERIF_REGULAR
    if weight == "bold":
        return PT_SERIF_BOLD
    raise ValueError("unknown weight %r (expected 'regular' or 'bold')" % (weight,))


def _role_font(role_spec, weight):
    """`_font()` for one of the six active-state role tuples
    (`STATE_LABEL_FONT`, `TOP_TAG_FONT`, ...), resolving the role's weight
    via `_role_weight_path()` rather than reading the tuple's own
    (always-Bold) path directly.
    """
    _path, size, role_weight = role_spec
    return _font((_role_weight_path(weight), size, role_weight))


def _role_fit_text_size(role_spec, text, max_width, min_size, weight):
    """`fit_text_size()` for one of the six active-state role tuples,
    resolving the role's weight the same way `_role_font()` does, instead
    of the caller hardcoding a bare `PT_SERIF_BOLD` path.
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
    """Looser guard rail than _assert_in_safe_box(): only asserts the
    element does not fall off the 1200x1600 canvas entirely. Used for the
    frame, the illustrations, and the flight text blocks below them, which
    deliberately sit inside the old 64px SAFE_BOX band (see the module
    docstring's "not yet verified against the real physical bezel" note).
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
    """A thin `ink_idx`-coloured rectangle outline, `FRAME_STROKE_PX` wide,
    inset `FRAME_INSET_FRAC` of the canvas width from every edge. Returns
    the frame's own bounding box.
    """
    inset = round(WIDTH * FRAME_INSET_FRAC)
    box = (inset, inset, WIDTH - inset, HEIGHT - inset)
    ImageDraw.Draw(canvas).rectangle(box, outline=ink_idx, width=FRAME_STROKE_PX)
    return box


def draw_source_fault_badge(canvas, ink_idx, weight="bold"):
    """Draw a small triangular alert glyph (outline + exclamation stroke)
    with `SOURCE_FAULT_TEXT` beside it, bottom-centre inside the frame
    `draw_frame()` returns. Uses `ink_idx` only - `ImageDraw.polygon()` and
    `ImageDraw.line()` calls, never a new palette index - so the badge can
    never introduce an illegal index regardless of the active theme. The
    badge's combined bounding box (glyph + caption) is deliberately small,
    so `_assert_legal_palette()`'s "bg_idx is the single most common index"
    dominance assertion still holds for every state and theme; a later
    enlargement of this badge is a conscious decision, not an accident
    inherited from this implementation.

    Driven only by `poll_loop.py`'s all-providers-failed classification
    (derived from `detect.poll_current_aircraft()`'s diagnostics dict) -
    see `render_panel()`'s own docstring for the rule that makes this
    requirement correct rather than a false-alarm trap.

    `weight`: the caption is an active-state text role like any other, so
    it must resolve its PT Serif weight from the active theme via
    `_role_font()` rather than hardcoding Bold - Bold reads as needlessly
    heavy on the White theme, the same reason every other role is
    theme-conditional. Defaults to `"bold"` only because
    `_build_empty_canvas()`'s call site is deliberately not
    theme-dependent (it already mixes weights on its own heading/body
    text) and passes that literal explicitly rather than relying on the
    default; `_build_active_canvas()` passes its own resolved `weight`.
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
    """A bottom-left battery glyph - a hollow outlined body with a small
    solid terminal nub and a left-aligned solid partial fill, signalling a
    fixed "low" reading rather than a live gauge. Own dedicated
    bottom-left zone - the one area of the locked two-flight layout with
    no existing element, and the visual counterweight to the bottom-right
    previous-flight card; never reuses, displaces, or resizes the top-left
    state label or the top-right runway tag. It is also horizontally clear
    of the source-fault badge, which is centred on the same bottom band -
    see draw_source_fault_badge().

    All geometry derives from the BATTERY_ICON_* module constants (the two
    position constants from MARGIN, the four size constants from a uniform
    0.7 reduction of their former spacing-scale values) - no ad hoc magic
    numbers. Draws three flat integer-palette-index rectangles: the body
    as a BATTERY_ICON_STROKE_PX-wide outline, the nub filled solid, and
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
    # Looser canvas guard, not the strict safe-box guard: this element sits
    # inside the old 64px band's bottom-left corner deliberately, exactly
    # like the frame and both illustrations already do.
    _assert_within_canvas(total, "battery icon")

    draw.rectangle(body, outline=ink_idx, width=BATTERY_ICON_STROKE_PX)
    draw.rectangle(nub, fill=ink_idx)
    draw.rectangle(fill, fill=ink_idx)
    return total


def draw_top_labels(
    canvas, state, ink_idx, bg_idx, weight, runway_id=device_config.DEFAULT_RUNWAY_ID, band_theme=False
):
    """Top row: the state label (top-left) and the runway tag (top-right,
    `runway_tag_text(runway_id)`), at the confirmed small sizes (20px/18px),
    both at the existing `MARGIN` inset (inside the frame, not on it). Both
    roles are drawn with `LABEL_TRACKING_PX` (6px) of letter-spacing via
    `draw_tracked_text()`. This is **screen-preview-validated only** -
    tracking has never been checked against real Spectra 6 ink.

    The runway tag is right-anchored, but tracked text has no Pillow
    `anchor="ra"` equivalent (tracking is applied glyph-by-glyph by hand) -
    its start x is pre-computed from `_tracked_text_width()` instead, so its
    run still ends flush at `WIDTH - MARGIN`.

    `weight` (`device_config.theme_weight()`'s return value) selects each
    role's PT Serif weight via `_role_font()` - not derivable from `bg_idx`
    alone, since the same index can back both a Regular and a Bold theme
    (see `_role_weight_path()`). `bg_idx` itself is retained - still no
    direct use in this function beyond being available to callers/future
    roles.

    `band_theme` (PHASE9-3, default `False` - every pre-Phase-9 call site's
    behaviour is byte-identical to before this phase): when `True`, the
    state label and runway tag are split differently for the diagonal-band
    themes, ported verbatim from spike 003's `patched_draw_top_labels()`
    (round 11's correction to rounds 7/9) - the state label absorbs a
    direction word and the tag's airport-code half ("DEPARTING FROM ORY"),
    and the top-right tag shrinks to just the runway-part half ("RWY 3"
    alone), which starts far enough right to clear the diagonal band with
    margin at `BAND_SHIFT_FRAC=0.0` (no shift needed). Both halves are
    derived from `runway_tag_text(runway_id)`'s real return value via
    `.partition(" · ")` - never a hardcoded "ORY"/"RWY 3" literal, so a
    future runway selection ("06-24"/"02-20") splits correctly too.
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

    # _assert_within_canvas(), not the strict _assert_in_safe_box(): real
    # font glyph metrics can carry a 1-2px negative left/right bearing at
    # these small sizes (e.g. PT Serif's "A" at 20px), which would fail a
    # pixel-exact 64px boundary despite the text visually sitting exactly
    # at MARGIN - see the module docstring's note on why the old
    # "inviolable" SAFE_BOX is not enforced pixel-exactly here.
    #
    # Both bbox measurements below use _tracked_text_bbox(), not
    # draw.textbbox(): the latter measures an untracked run and would
    # under-report a tracked one's width, silently stopping the guard from
    # protecting anything.
    label_bbox = _tracked_text_bbox(label_font, (MARGIN, MARGIN), label_text, LABEL_TRACKING_PX)
    _assert_within_canvas(label_bbox, "state label")
    draw_tracked_text(draw, (MARGIN, MARGIN), label_text, label_font, ink_idx, tracking=LABEL_TRACKING_PX)

    tag_width = _tracked_text_width(tag_font, tag_text, LABEL_TRACKING_PX)
    tag_x = WIDTH - MARGIN - tag_width
    tag_bbox = _tracked_text_bbox(tag_font, (tag_x, MARGIN), tag_text, LABEL_TRACKING_PX)
    _assert_within_canvas(tag_bbox, "top-right tag")
    draw_tracked_text(draw, (tag_x, MARGIN), tag_text, tag_font, ink_idx, tracking=LABEL_TRACKING_PX)


def _illustration_over_pixel_cap(path):
    """Render-path counterpart of `illustrations.validate_illustration_file()`'s
    header-first pixel cap: return `True` when `path`'s PNG header declares
    more than `illustrations.ILLUSTRATION_MAX_PIXELS` pixels, or when the
    header cannot even be read (missing, garbage, unreadable) - a file the
    caller should move past rather than attempt to decode. `Image.open()`
    is lazy - it parses the header without decoding pixel data - which is
    the whole point: this check never triggers a full decode.

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

    The last resort is `generic-fallback.png`, and then "no illustration
    at all" - matching the already-correct missing-directory degradation.

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


_illustration_cache = {}
# Bounded so the long-lived companion process cannot grow it without limit
# across every (illustration, target width) pair it ever previews: past the
# cap the cache is simply flushed and refilled - a miss only costs one PNG
# decode + resize, exactly what every call cost before the cache existed.
_ILLUSTRATION_CACHE_MAX_ENTRIES = 128


def _resize_illustration(path, target_w):
    """Load a vendored per-airline illustration PNG (real alpha channel,
    see HANDOFF.md) and resize it to `target_w` px wide, preserving its
    source aspect ratio. Returns a fresh "RGBA" image.

    Memoized on (path, mtime_ns, size, target_w) via os.stat() - a cache hit
    skips both the PNG decode and the LANCZOS resize. Production poll_loop.py
    is a oneshot process per systemd timer, so this cache is a no-op there;
    it exists to remove ~650 redundant PNG decodes in test_render's own run
    and to speed up the long-lived companion process's panel previews. If
    os.stat() raises OSError, fall through to the uncached load unchanged -
    `_load_illustration_safely()`'s existing try/except ladder must keep
    seeing the same exceptions it always has.
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
"""Alpha strictly greater than this is painted; anything at or below it is
discarded entirely. Named (not inlined twice) so `_threshold_alpha()` and
every opaque-bbox measurement provably use one number - a drift between
"what we paint" and "what we measure" would make the aircraft-to-text gap
vary per illustration file."""


def _threshold_alpha(resized_rgba):
    """Return `resized_rgba`'s alpha channel hard-thresholded to strictly
    binary (0 or 255) at `ILLUSTRATION_ALPHA_THRESHOLD`.

    A soft/gradient alpha mask blends palette INDEX INTEGERS during
    paste(), not colors, and produces illegal in-between indices - so the
    mask handed to paste() must be strictly binary. Every vendored
    illustration also carries a soft drop-shadow band (alpha 1..127) below
    the aircraft, which this threshold discards; `_opaque_bbox()`
    therefore measures against this same mask so layout and painting can
    never disagree about where the aircraft ends.
    """
    return resized_rgba.getchannel("A").point(
        lambda p: 255 if p > ILLUSTRATION_ALPHA_THRESHOLD else 0
    )


def _opaque_bbox(resized_rgba):
    """Return the tight bounding box of the pixels `draw_illustration()` will
    actually paint - i.e. `Image.getbbox()` over `_threshold_alpha()`'s binary
    mask, in image-local coordinates.

    NOT `Image.getbbox()` on the RGBA image or on the raw alpha channel: both
    of those count the soft drop-shadow band (alpha 1..127) that the paste
    threshold erases, which is exactly the mismatch that made the
    aircraft-to-text gap vary per airline. For six vendored files -
    air-france.png among them - the raw-alpha bbox reports a bottom padding
    of exactly 0 while the real painted padding is 82..174px.

    Returns `None` when nothing at all would be painted (a fully transparent or
    entirely sub-threshold image); callers must fall back to the full
    rectangle. Never raises.
    """
    return _threshold_alpha(resized_rgba).getbbox()


class IllustrationPlacement(tuple):
    """What `draw_illustration()` returns: two absolute canvas bounding boxes
    that are deliberately NOT the same box.

    - `rect`: the full placement rectangle of the resized source PNG,
      `(left, top, left + w, top + h)`. This is a geometric footprint - it
      includes whatever transparent padding the artwork was drawn inside. Use
      it for canvas-containment guards and for anything sized relative to the
      illustration's nominal rendered dimensions.
    - `content`: the tight bbox of the pixels actually painted (see
      `_opaque_bbox()`), in the same absolute canvas coordinates. Use it for
      anything that must line up with the aircraft *as seen*, above all the
      flight-text vertical anchors. Falls back to `rect` when nothing is
      painted.

    Anchoring visual layout to `rect` is the bug this class exists to make
    hard to reintroduce: `rect`'s bottom edge sits 37-174px below the
    aircraft's last painted pixel, by a per-file amount.

    Subclasses `tuple` as `(rect, content)` so it unpacks naturally; the named
    attributes are what call sites should actually read, so each reads as a
    statement about which edge it means.
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
    """Return the paste `left` that puts the illustration's PAINTED horizontal
    midpoint on `center_x`.

    Not `(WIDTH - w) // 2`: that centres the source rectangle, and horizontal
    transparent padding is asymmetric (measured post-resize across all 43
    vendored files: left 3-32px, right 5-29px), which displaced the visible
    aircraft from the canvas centre by up to 7.5px, varying per file - the same
    defect as the vertical gap, on the other axis. Falls back to centring the
    full rectangle when nothing would be painted. Never raises.
    """
    local = _opaque_bbox(resized_rgba)
    if local is None:
        return round(center_x - resized_rgba.size[0] / 2)
    return round(center_x - (local[0] + local[2]) / 2)


def _left_for_right_aligned_content(resized_rgba, right_x):
    """Return the paste `left` that puts the illustration's PAINTED right edge
    on `right_x`, so two illustrations aligned this way share one visible
    vertical line regardless of their differing right padding (3-17px at the
    previous card's scale, 5-29px at the main card's). Falls back to aligning
    the full rectangle when nothing would be painted. Never raises.
    """
    local = _opaque_bbox(resized_rgba)
    if local is None:
        return round(right_x - resized_rgba.size[0])
    return round(right_x - local[2])


def _top_for_centered_content(resized_rgba, center_y):
    """Return the paste `top` that puts the illustration's PAINTED vertical
    midpoint on `center_y`.

    Vertical padding is strongly asymmetric - the drop-shadow band means bottom
    padding always exceeds top padding - so centring the source rectangle put
    the visible aircraft 5.5-28.5px ABOVE the intended centre, always high,
    varying per file. Falls back to centring the full rectangle when nothing
    would be painted. Never raises.
    """
    local = _opaque_bbox(resized_rgba)
    if local is None:
        return round(center_y - resized_rgba.size[1] / 2)
    return round(center_y - (local[1] + local[3]) / 2)


def draw_illustration(canvas, resized_rgba, left, top):
    """Composite an already-resized real illustration (from
    `_resize_illustration()`) onto `canvas` at (`left`, `top`). Full-color,
    dithered to the panel's real 6-color palette via
    `dither.dither_to_full_panel_palette()`, keeping its real livery
    colors. Never mirrored - the caller always passes the vendored file
    exactly as resized, regardless of departing/arriving state.

    The alpha channel is hard-thresholded to strictly binary before
    paste() (`_threshold_alpha()`).

    Returns an `IllustrationPlacement` carrying BOTH the full placement
    rectangle and the tight bbox of the pixels actually painted - see that
    class's docstring for which call site should read which, and why they are
    not interchangeable.
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
    """Four-tier content ladder for the main line, evaluated strictly in
    this order, returning on the first match. The raw ADS-B ICAO callsign
    is never reachable at any tier, even in the fallback cases.

    - **Tier 1** - `route`'s `callsign_iata` and
      `enrich.city_for_state(route, state)` are both usable: returns
      `"{identifier} to|from {city}"`, lowercase direction word (ordinary
      sentence text, not the tracked-caps Label-role prefix).
    - **Tier 2** - a city is known but no identifier: returns
      `"To|From {city}"`, TITLE-case direction word. The casing differs
      from tier 1 deliberately: tier 1's word sits mid-sentence after an
      identifier, tier 2's word starts the line.
    - **Tier 3** - `route` carries a truthy `airline_name` but no usable
      city or identifier (the `enrich.airline_only_route()` shape, or any
      hand-edited/corrupt route with the same profile): returns `""`, the
      sentinel meaning *line 1 is omitted entirely*. Draw callers
      (`draw_main_text_block()`/`draw_previous_text_block()`) must promote
      line 2 into line 1's slot on this signal - implemented independently
      in both functions, since they position line 2 from opposite edges of
      line 1 (bottom vs. top).
    - **Tier 4** - `route` is `None`, is not a dict, or carries no airline
      name either: returns the fixed string `"Unknown flight"`. Identical
      text for both states - the top-left label is what distinguishes
      departing from arriving here. Line 2 independently falls to
      `ROUTE_FALLBACK_TEXT` in this case, unchanged existing behaviour.

    Residual ordering note: a route carrying an identifier but no city
    falls through tier 1 and lands on tier 3 if it has an airline, or tier
    4 if it does not. `_parse_route()` (which requires all five core
    fields together) can never produce this shape, but a hand-edited or
    corrupt persisted cache entry could - this is a stated decision, not an
    accident.

    `flight` is retained in the signature even though this body no longer
    reads a callsign or hex from it - both call sites pass it positionally,
    and removing it would be a signature change this rewrite never asked
    for.

    Never raises: every read is guarded, and a non-string/blank-after-
    stripping `callsign_iata`, a non-dict `route`, or a hostile
    `route.get()` all degrade a tier rather than propagate.
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


# Friendly human-readable labels for the ICAO type designators detect.py's
# aircraft_type field can carry, so `{airline} · {aircraft_type}` shows a
# legible label rather than a raw code (neo/MAX variants are named
# explicitly, not collapsed to the base family - more informative). Covers
# every designator in
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

# A presentation-only display alias for the one carrier that rebranded in
# 2013.
#
# Retained unchanged as a defensive no-op, not as the live presentation
# path: `enrich.correct_airline_name()` now corrects this carrier's
# `airline_name` upstream, inside `lookup_route()`'s single seam - every
# route that reaches `_flight_line2_text()` through the normal
# `enrich.resolve_route()` path already carries the corrected string "Air
# Corsica", so the alias below can no longer be triggered by a live route.
# It stays only for a hand-built route dict (e.g. a test fixture, or a
# future caller that bypasses `enrich.py` entirely) that still carries the
# literal upstream string "CCM Airlines" - display_airline_name() still
# resolves that correctly.
_AIRLINE_DISPLAY_ALIASES = {
    "CCM Airlines": "Air Corsica",
}


def display_airline_name(airline_name):
    """Return the presentation-only display name for `airline_name`: the
    aliased brand name when one exists, otherwise `airline_name`
    unchanged. Returns `airline_name` unchanged for any non-string or
    falsy value. Never raises.
    """
    if not isinstance(airline_name, str) or not airline_name:
        return airline_name
    return _AIRLINE_DISPLAY_ALIASES.get(airline_name, airline_name)


def _flight_line2_text(route, aircraft_type=None):
    """`"{airline} · {friendly type label}"`, using real per-flight type
    data (detect.py's `aircraft_type` field) and a type-to-shape
    classifier to size the art (illustrations.classify_aircraft_type()).
    The displayed airline name is resolved through
    `display_airline_name()` - a presentation-only alias that never
    reaches illustration selection.

    Falls back to the display name alone when `aircraft_type` is missing
    or has no friendly label in `_TYPE_DISPLAY_LABELS` - an unlabelled or
    absent type never fabricates a label and never renders an empty
    separator. Falls back to `ROUTE_FALLBACK_TEXT` only when no route was
    supplied, or the supplied route has no airline name at all - regardless
    of what type was detected. That condition is strictly narrower than
    "adsbdb missed": a route may be airline-only
    (`enrich.resolve_route()`'s `"airline_only"` source /
    `enrich.airline_only_route()` - adsbdb had nothing, but the callsign's
    ICAO prefix identified the carrier) and still carry a real
    `airline_name`, in which case this function composes `"{airline} ·
    {type label}"` exactly as it would for a full adsbdb hit.
    `ROUTE_FALLBACK_TEXT` fires only when *neither* enrichment source
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


# --- Band-only main-card text roles ---------------------------------
# Declared weight ("700"/"400" in the tuple) is never read directly -
# `_role_font()` resolves the real weight from the active theme's `weight`
# field, same mechanism every other active-state role already uses.
BAND_MAIN_NUMBER_FONT = (PT_SERIF_BOLD, 56, 700)
BAND_MAIN_ROUTE_FONT = (PT_SERIF_REGULAR, 22, 400)
BAND_MAIN_AIRLINE_FONT = (PT_SERIF_REGULAR, 20, 400)
BAND_MAIN_DASH_W = 48
BAND_MAIN_DASH_GAP = 10

# Unlike every other active-state text role, the three band roles above
# were fixed-size - no fit_text_size()-style shrink-to-fit - and a long
# airline/city name overflowed on real glass. They use the same
# shrink-to-fit mechanism the rest of the panel already has. Min sizes
# chosen at roughly the same ~70% floor MAIN_LINE1_FONT/MAIN_LINE2_FONT
# already use (40/28, 22/16).
BAND_MAIN_NUMBER_MIN_SIZE = 40
BAND_MAIN_ROUTE_MIN_SIZE = 16
BAND_MAIN_AIRLINE_MIN_SIZE = 14


def _role_fit_tracked_text_size(role_spec, text, tracking, max_width, min_size, weight):
    """`_role_fit_text_size()`'s step-down loop, but measuring width via
    `_tracked_text_width()` (which adds `tracking` px between every glyph
    pair) instead of `font.getlength()` - `fit_text_size()` itself would
    under-measure a tracked line's real rendered width and could still let
    it overflow after "fitting".
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
    below the main illustration's OPAQUE bottom edge
    (`main_placement.content[3]`) - the aircraft's last actually-painted
    pixel row, not the bottom of its source rectangle.

    Anchoring to `main_placement.rect` instead would vary the gap by
    37-174px depending on which file is drawn, since the rectangle
    includes each file's own transparent padding. Reading `.content` makes
    the gap a constant by construction. See `MAIN_TEXT_GAP_PX` for how its
    value is derived.

    When `_flight_line1_text()` returns `""` (the sentinel meaning line 1
    is omitted), no font is computed for it, no bbox is computed or
    asserted, and nothing is drawn - line 2 is promoted into line 1's slot
    instead, starting at the same `main_placement.content[3] +
    MAIN_TEXT_GAP_PX` expression line 1's own `top_y` would have used. The
    returned pair's first slot is `None` in that case; both call sites
    already discard the return value, and `None` is more honest than an
    invented empty bbox.

    `main_placement` is a `draw_illustration()` return value. Returns
    (line1_bbox, line2_bbox).

    `weight` (`device_config.theme_weight()`'s return value) selects each
    line's PT Serif weight via `_role_fit_text_size()` - not derivable
    from `bg_idx` alone, since the same index can back both a Regular and
    a Bold theme (see `_role_weight_path()`). `bg_idx` itself is retained
    for callers/future roles.

    `band_idx`: `None` for every non-band theme (`_build_active_canvas()`
    only ever passes a real value for a registered band theme) - in that
    case this function's body draws the plain (non-band) layout. For a
    band theme, this instead draws a three-tier hierarchy (big identifier
    / dash rule / tracked route line / airline·type line) centred INSIDE
    the band, in the band's own contrast ink on the black band and the
    theme's plain `ink_idx` everywhere else.
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
        # White-ink override for every band theme: screen previews suggest
        # black text stays legible on some band colours, but real Spectra
        # 6 ink disagrees for all of them, so this is unconditional for
        # any band theme rather than an enumerated list of ink_idx
        # exceptions.
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

        # First-pass fonts, fit against SAFE_BOX's width purely to get an
        # approximate block height for the midpoint calc below - not the
        # final constraint (see the real fit below, which uses the band's
        # own width at each line's actual y).
        band_safe_width = SAFE_BOX[2] - SAFE_BOX[0]
        num_font = _role_fit_text_size(BAND_MAIN_NUMBER_FONT, number_text or "", band_safe_width, BAND_MAIN_NUMBER_MIN_SIZE, weight)
        route_font = _role_fit_tracked_text_size(BAND_MAIN_ROUTE_FONT, tracked_text or "", LABEL_TRACKING_PX, band_safe_width, BAND_MAIN_ROUTE_MIN_SIZE, weight)
        airline_font = _role_fit_text_size(BAND_MAIN_AIRLINE_FONT, plain_text, band_safe_width, BAND_MAIN_AIRLINE_MIN_SIZE, weight)

        # center_x is computed ONCE and reused for every line below -
        # never recomputed per line (see _band_center_x()'s own
        # docstring). Anchoring that one computation at the block's TOP
        # left the lower line(s) increasingly offset from the band's true
        # centreline, since the trapezoid drifts left as y increases -
        # the number line (top) looked centred but the route/airline
        # lines beneath it visibly didn't. Measuring the block's full
        # vertical extent first (a
        # dry-run pass, x-position irrelevant to the resulting heights)
        # and anchoring center_x at the block's MIDPOINT instead spreads
        # the trapezoid's leftward drift-with-y evenly across all three
        # lines rather than concentrating it at the bottom.
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

        # White ink is only visible ON the band - a line fit merely to
        # SAFE_BOX's width can still be wider than the band itself at its
        # own y, so its overhang lands on the plain White field and
        # silently vanishes (white-on-white), not a hard clip.
        # Each line is re-fit here against the band's own width at ITS
        # actual y (band_left/band_right, not the shared center_x's own
        # local band width) before drawing - center_x itself still stays
        # the one shared value from the midpoint calc above.
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
    """Previous flight text: two right-aligned lines. Line 1 starts
    `PREVIOUS_TEXT_GAP_PX` below the previous illustration's OPAQUE bottom edge
    (`prev_placement.content[3]`), for the same reason
    `draw_main_text_block()` uses `.content` - the source rectangle's bottom
    sits 21-99px below the aircraft at this card's scale, which would make
    the gap vary by up to 78px across the vendored set otherwise.

    Horizontal alignment uses `prev_placement.content[2]` MINUS
    `PREVIOUS_TEXT_LEFT_OFFSET_PX` - the previous aircraft's visible right
    edge, which `_build_active_canvas()` has already placed on the MAIN
    aircraft's visible right edge, nudged left by a fixed optical
    correction (see that constant's own comment for why the raw measured
    edge is not itself the bug). So the main aircraft, the previous
    aircraft and this text block all still share one visible reference
    line, offset by that one constant. Reading `.rect[2]` instead of
    `.content[2]` would put the text 3-17px right of the aircraft it
    belongs to, varying per file - a separate, unrelated defect from the
    left-offset correction applied on top of it.

    Line 2 starts `PREVIOUS_LINE_GAP_PX` below line 1's own TOP, not its
    bottom (a tighter confirmed stacking). No `PREVIOUS ·` prefix.

    When `_flight_line1_text()` returns `""` (line 1 omitted), no font is
    computed for it, no bbox is computed or asserted, and nothing is
    drawn - line 2 is promoted into line 1's slot, starting at this
    function's OWN `prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX`
    expression (not `draw_main_text_block()`'s equivalent - the two
    functions position line 2 from opposite edges of line 1 and must not
    share a helper for this, see that function's own docstring). The
    returned pair's first slot is `None` in that case.

    `prev_placement` is a `draw_illustration()` return value. Returns
    (line1_bbox, line2_bbox).

    `weight` (`device_config.theme_weight()`'s return value) selects each
    line's PT Serif weight via `_role_fit_text_size()` - not derivable
    from `bg_idx` alone, since the same index can back both a Regular and
    a Bold theme (see `_role_weight_path()`). `bg_idx` itself is retained
    for callers/future roles.

    `band_idx`: `None` for every non-band theme - in that case this
    function's body draws the plain (non-band) layout. For a band theme,
    this instead draws a three-tier hierarchy, right-aligned at this
    card's existing scale, in its unchanged position - the band never
    reaches this card's text at any candidate geometry, so unlike the
    main card there is no ink override here: this card always draws in
    the caller's plain `ink_idx`, even for band_black.
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
    heading follows `runway_id`).

    Uses the shared hold composition (`_build_hold_canvas()`, white
    variant): the runway mark, a tracked Bold label, a short rule, then
    the body - the same shape as the dimmed DISPLAY OFF and QUIET HOURS
    screens, on a white field because the frame is working here, not
    resting.

    `battery_low`: when True, draws the bottom-left battery-low icon in
    EMPTY_INK - a low-battery reading is a device-health fact independent
    of whether an aircraft is currently detected, so the icon renders
    here too.

    `source_fault`: when True, draws the bottom-centre source-fault
    badge, also in EMPTY_INK. The two indicators are independent and may
    both be shown at once - they occupy horizontally disjoint parts of the
    same bottom band.
    """
    # The shared hold composition, white variant - the runway mark, then
    # the heading as a tracked label in the frame's label voice. The
    # label is upper-cased at draw time only: EMPTY_HEADING_TEXT and
    # empty_heading_text() are untouched, so the locked copy and the
    # runway-dependent heading both stand. Every registered runway id fits
    # the 40px tracked label inside the safe box (the helper asserts it),
    # so the fit_text_size() shrink the 72px heading used to need is no
    # longer exercised here - a longer future runway label would trip
    # that assert at test time rather than shrink silently, which is the
    # right failure.
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
    """Build the scheduled-quiet-hours canvas: a dedicated, deliberate
    exception to the project's "no on-screen status text" rule, drawn
    once by poll_loop.py at the poll that first detects window entry.

    Uses the shared dimmed hold composition (`_build_dimmed_hold_canvas()`,
    see the DIMMED_* constants): a dithered dark field, white ink, the
    crescent as its mark, a tracked Bold label over a short rule, then the
    body. This makes the two "resting on purpose" screens - this one and
    DISPLAY OFF - a matched pair that differ by glyph, and leaves the
    empty state as the one white hold screen, since the frame is working
    there. `theme_id` and `runway_id` are both ignored - this screen is
    always the same White/Black composition regardless of the configured
    theme, exactly like the empty state.

    `quiet_hours_until` is expected to be the "HH:MM" local (Europe/Paris)
    wall-clock end time string produced by
    `device_config.seconds_until_quiet_hours_end()`. When it is missing,
    empty, or not a string, the body line is omitted entirely rather than
    ever drawing the literal text "Back at None" - the heading then
    centres alone, the same "an element exists visually only when it has
    real information to show" discipline the battery icon also follows.

    `battery_low`/`source_fault` match `_build_empty_canvas()`'s own
    precedent: both indicators are device/server-health facts independent
    of this screen's content, drawn in DIMMED_INK (white).
    """
    # The shared dimmed composition, the crescent as its mark. The
    # missing-return-time branch is preserved exactly: no
    # `quiet_hours_until` means no body and no body spacing, never a
    # placeholder, never an exception.
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
    """Build the remote display-off canvas: a dedicated, deliberate
    exception to the project's "no on-screen status text" rule, drawn
    once by poll_loop.py at the poll that first enters the off hold
    state.

    Uses the shared dimmed hold composition (`_build_dimmed_hold_canvas()`
    - a dithered dark field over DIMMED_FIELD_IDX, the Grey theme's
    recipe, white ink, the power ring, a tracked Bold label over a short
    rule, then the two authored body lines), the whole block vertically
    centred with the same formula the sibling screens use.
    `theme_id` and `runway_id` are both ignored - this screen is always the
    same White/Black composition regardless of the configured theme, exactly
    like the empty state and the quiet-hours screen.

    Unlike the quiet-hours screen, there is no `quiet_hours_until`
    parameter and no missing-value branch: DISPLAY_OFF_BODY_TEXT is a fixed
    constant with no interpolated value, so the body is always drawn -
    there is no "value is missing" case to handle because there is no
    value at all. The body string is meaningfully longer than the
    quiet-hours screen's one-liner and is expected to wrap; the wrap is
    decided by `_wrap_text()` against `safe_width`, never assumed to be a
    single line.

    `battery_low`/`source_fault` match
    `_build_empty_canvas()`'s/`_build_quiet_hours_canvas()`'s own
    precedent: both indicators are device/server-health facts independent
    of this screen's content - drawn in DIMMED_INK (white), the only ink
    that reads on the dimmed field.
    """
    # The shared dimmed composition, the power ring as its mark. Each
    # authored sentence is passed separately so the break falls after
    # "page." rather than wherever the measured width lands (the helper
    # still wraps each one, so a line that cannot fit is broken, never spilled).
    return _build_dimmed_hold_canvas(
        draw_power_icon,
        POWER_ICON_BAR_RISE_PX + POWER_ICON_DIAMETER_PX,
        DISPLAY_OFF_HEADING_TEXT,
        DISPLAY_OFF_BODY_LINES,
        source_fault=source_fault,
        battery_low=battery_low,
    )


def _build_battery_empty_canvas():
    """Build the BATTERY EMPTY hold canvas: a screen that ends a battery
    depletion run on a state that says something, rather than the panel
    freezing mid-transition. poll_loop.py latches this state once the
    reported pack voltage crosses BATTERY_CRITICAL_MV and parks the frame
    here - see poll_loop.py's `apply_battery_critical_hysteresis` for the
    3300/3700 hysteresis and byos_server.py's `battery_critical_sleep_s`
    for the hourly check-in pin.

    Goes through the shared `_build_dimmed_hold_canvas()` composition:
    never a bespoke layout, always the same family as DISPLAY OFF and
    QUIET HOURS (dithered dark field, white ink, glyph, tracked label,
    rule, body).

    Unlike its siblings, `theme_id`, `battery_low` and `source_fault` are
    not accepted here at all - `build_canvas()` dispatches this state before
    any of the three ever reach this function. That is deliberate rather
    than an oversight: the pack is already flat, so the low-battery badge
    would be redundant, and the image's bytes (and therefore its sha256
    hash) must stay perfectly constant for the whole parked episode so every
    hourly check-in byos serves is a hash-skip, never a redraw. A badge or a
    theme toggling mid-episode would break that invariant.
    """
    return _build_dimmed_hold_canvas(
        draw_empty_battery_icon,
        EMPTY_BATTERY_ICON_HEIGHT_PX,
        BATTERY_EMPTY_HEADING_TEXT,
        BATTERY_EMPTY_BODY_LINES,
    )


def _build_no_connection_canvas(flat=False):
    """Build the NO CONNECTION hold canvas: the fourth sibling of
    DISPLAY OFF / QUIET HOURS / BATTERY EMPTY, drawn through the same
    shared `_build_hold_canvas()` composition those three go through
    (dimmed field, glyph, tracked label, rule, body) rather than a
    bespoke layout.

    Unlike its three siblings, this function is never reached by
    `build_canvas()` - it is deliberately not dispatched from there at
    all. The whole reason this screen exists is that the device could not
    reach the server, so the server can never be the one to render it; the
    device draws it entirely on its own, in firmware, from a generated
    ink mask (`firmware/tools/gen_fault_screen.py` ->
    `firmware/main/fault_screen_mask.h`) this function's flat output feeds.
    This function is that mask's one source of truth on the Python side.

    `flat` (default `False`) selects between the two callers this function
    actually has: the server-side render tests exercise the normal
    `dithered=True` path (matching what a human would see on glass if this
    screen were ever rendered server-side, which it never is in
    production), while `gen_fault_screen.py` calls `flat=True` to get a
    flat two-colour (`DIMMED_FIELD_IDX`/`DIMMED_INK`) canvas with no dither
    noise, so its ink-mask extraction (`pixel == IDX_WHITE`) is exact - the
    firmware reproduces the dithered field itself, on-device, from the
    same integer Floyd-Steinberg spec `gen_fault_screen.py`'s own Python
    port implements (see that module's docstring for the shared spec).
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
# Drawn from primitives like every other panel mark (draw_battery_icon,
# draw_source_fault_badge) - no vendored asset, so nothing to attribute.
#
# The universal power mark rather than a moon or "Zzz", which is what "sleep"
# suggests first: QUIET HOURS is literally the night/curfew screen, so a
# night-register glyph would pull DISPLAY OFF toward the one screen it
# exists to keep distinct from. The power mark says "off" without
# borrowing that vocabulary - in white ink, where its 8px stroke is
# Bold-class and safe against the dither.
POWER_ICON_DIAMETER_PX = 76
POWER_ICON_STROKE_PX = 8
POWER_ICON_GAP_DEGREES = 64  # the ring's opening, centred on 12 o'clock
POWER_ICON_BAR_RISE_PX = 10  # how far the bar stands above the ring
POWER_ICON_BAR_DROP_PX = 34  # how far it reaches down into the ring


def draw_power_icon(draw, center_x, top_y, ink_idx):
    """Draw the power mark centred on `center_x`, its topmost pixel at `top_y`,
    and return the glyph's total height so the caller's vertical-centring
    arithmetic can account for it exactly like a text block's own height.

    `ImageDraw.arc()`'s angles run from 3 o'clock and increase clockwise, so
    12 o'clock is 270. Drawing from `270 + half_gap` clockwise to
    `270 - half_gap` wraps the long way round the ring and leaves the opening
    at the top, which is what makes the mark read as a power symbol rather
    than as a plain circle.
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
# The moon belongs here, not on DISPLAY OFF: QUIET HOURS is the curfew screen,
# so the night register is its own. Same 76px footprint and the same
# Bold-class white as the power ring, so the two dark screens sit as a pair
# and differ only by the mark - which is exactly what should tell them apart
# from across the room. Drawn as a filled crescent: the region inside one disc
# and outside a second disc shifted to the right, traced numerically so no
# intersection geometry is hand-derived. Filled rather than outlined because
# the bite would otherwise have to be painted over the dithered field with a
# flat index, leaving a solid patch in an even grey.
MOON_ICON_DIAMETER_PX = 76
MOON_ICON_BITE_DIAMETER_PX = 68
MOON_ICON_BITE_OFFSET_PX = 20  # the bite's centre, right of the disc's centre
MOON_ICON_SAMPLES = 180


def draw_moon_icon(draw, center_x, top_y, ink_idx):
    """Draw a filled crescent centred on `center_x`, its disc's topmost pixel
    at `top_y`, and return the glyph's height. The crescent is the set of
    points inside the main disc and outside the bite disc; both arcs are
    sampled and the two point runs joined into one polygon.
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

    # The lit limb runs over the left half, so its sampled angles straddle pi:
    # sort by angle after unwrapping so the run is contiguous, then walk the
    # inner arc back the other way to close the shape.
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
# An upright hollow battery, chosen over the horizontal draw_battery_icon()
# form (the bottom-left low-battery badge) because a 76px-tall family glyph
# drawn horizontally would run about 150px wide - heavier than the power ring
# and the crescent, and out of step with the family's shared scale. Upright
# instead, at the same 76px height as the ring and the crescent
# (EMPTY_BATTERY_ICON_HEIGHT_PX == MOON_ICON_DIAMETER_PX == POWER_ICON_DIAMETER_PX)
# and the same 48px width as the runway strip (EMPTY_BATTERY_ICON_WIDTH_PX ==
# RUNWAY_ICON_WIDTH_PX) - the family's other upright glyph, so this one reads
# as a sibling rather than a fourth, unrelated scale.
#
# The body is drawn as a stroke-only outline, exactly like draw_battery_icon()
# draws its own body outline - the interior is left unpainted (hollow) so the
# dithered field shows through, the same reasoning _build_hold_canvas()'s own
# docstring gives for why every mark here is drawn in the caller's `ink_idx`
# rather than a hardcoded index: a flat interior fill would paint a solid
# patch over the dithered field, which is exactly what draw_moon_icon()'s
# module comment says the crescent is filled (rather than outlined) to avoid.
# A dead pack reading zero-charge is also the honest picture: an empty
# battery has nothing inside to show.
EMPTY_BATTERY_ICON_HEIGHT_PX = 76
EMPTY_BATTERY_ICON_WIDTH_PX = 48
EMPTY_BATTERY_NUB_W_PX = 20
EMPTY_BATTERY_NUB_H_PX = 8
EMPTY_BATTERY_ICON_STROKE_PX = POWER_ICON_STROKE_PX  # same Bold-class 8px stroke as the ring


def draw_empty_battery_icon(draw, center_x, top_y, ink_idx):
    """Draw the battery-empty mark centred on `center_x`, its topmost pixel
    (the nub's top edge) at `top_y`, and return the glyph's total height so
    the caller's vertical-centring arithmetic can account for it exactly
    like every other `draw_*_icon()` here.

    Two flat-filled/outlined rectangles, both in `ink_idx` (never a
    hardcoded index - the caller supplies DIMMED_INK): a solid
    EMPTY_BATTERY_NUB_W_PX x EMPTY_BATTERY_NUB_H_PX terminal nub centred on
    top, then an EMPTY_BATTERY_ICON_WIDTH_PX-wide body below it, drawn as an
    EMPTY_BATTERY_ICON_STROKE_PX-wide outline only - no fill, so the
    interior stays the dithered field. Uses the same inclusive-corner
    `right - 1` / `bottom - 1` convention as draw_runway_icon() so the
    rendered footprint is exactly the nominal width/height, not one pixel
    wider (contrast draw_battery_icon()'s own docstring, which documents the
    opposite, deliberate, one-pixel-wider convention for that glyph).
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
# Same shape family as `draw_source_fault_badge()`'s small triangular alert
# mark (outline triangle + exclamation stroke + dot), scaled up to the
# 76px-tall hold-glyph family instead of the small inline badge size.
# `draw_source_fault_badge()` itself is left untouched (its pixels are
# covered by existing tests); this is a sibling glyph, not a shared call.
#
# ALERT_ICON_STROKE_PX matches POWER_ICON_STROKE_PX (Bold-class, 8px) - the
# same "thin white strokes drown in dither noise" finding that set every
# other dimmed-hold glyph's stroke width applies here too.
ALERT_ICON_HEIGHT_PX = 76
ALERT_ICON_WIDTH_PX = 88
ALERT_ICON_STROKE_PX = POWER_ICON_STROKE_PX


def draw_alert_icon(draw, center_x, top_y, ink_idx):
    """Draw the no-connection alert mark centred on `center_x`, its apex at
    `top_y`, and return the glyph's total height so the caller's
    vertical-centring arithmetic can account for it exactly like every
    other `draw_*_icon()` here.

    An outline triangle (apex at top-centre, base at the glyph's bottom
    edge, drawn with `ImageDraw.polygon(..., width=ALERT_ICON_STROKE_PX)`
    - Pillow 12.3's polygon outline width support), an exclamation stroke
    (a vertical `ALERT_ICON_STROKE_PX`-wide line from 0.35 to 0.65 of the
    glyph's height, kept inside the triangle's interior clear of the
    outline), and a round dot at 0.8 of the height, drawn as a filled
    ellipse rather than a zero-length `ImageDraw.line()` - a degenerate
    segment paints only a single pixel regardless of `width`, the same
    reason `draw_source_fault_badge()`'s own docstring records. Only
    `ink_idx` is ever used, matching every other `draw_*_icon()` here.
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
    """The shared hold-screen composition (see the DIMMED_* constants above,
    which also carry the type and spacing values the white variant reuses):
    a field - `field_idx` dithered toward White when `dithered`, flat
    otherwise - then one vertically-centred block in `ink`: `glyph_draw` (a
    `draw_*_icon()` routine, `glyph_height` tall), a tracked Bold label, a
    short rule, and the body. `sentences` are wrapped one by one so an
    authored line break is honoured while `_wrap_text()` still catches a
    line that cannot fit; an empty tuple omits the body and its spacing
    entirely, which is how the quiet-hours screen handles a missing return
    time.

    Three screens draw through here, and the field is what sorts them:
    DISPLAY OFF and QUIET HOURS are dimmed (the frame is resting on
    purpose), the empty state is white (the frame is working). All three
    share one composition so they read as one family, and the field says
    which kind of screen it is.

    The width of the tracked label is summed glyph-by-glyph the way
    draw_tracked_text() advances, so the block is centred on what will be
    drawn. Every part joins the same total the centring divides, so adding a
    part moves the whole block, never the text alone.

    `battery_low`/`source_fault` follow the sibling screens' precedent -
    device/server-health facts independent of the screen's content -
    drawn in the screen's own `ink`.
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
    """The dimmed variant of `_build_hold_canvas()` - DISPLAY OFF and QUIET
    HOURS: DIMMED_FIELD_IDX dithered toward White, DIMMED_INK for everything
    drawn on it."""
    return _build_hold_canvas(
        glyph_draw, glyph_height, label_text, sentences,
        DIMMED_FIELD_IDX, DIMMED_INK, True,
        source_fault=source_fault, battery_low=battery_low,
    )


# --- Empty-state runway glyph ---------------------------------------------
# The empty screen's subject is the runway being watched, so the mark is a
# runway seen from above: a strip with a dashed centreline and a
# threshold bar at each end, drawn from rectangles like every other panel
# mark. Same 76px height as the power ring and the crescent, so the three
# glyphs sit at one scale.
RUNWAY_ICON_HEIGHT_PX = 76
RUNWAY_ICON_WIDTH_PX = 48
RUNWAY_ICON_STROKE_PX = 4
RUNWAY_ICON_DASH_PX = 6
RUNWAY_ICON_DASH_GAP_PX = 5
RUNWAY_ICON_KEY_PX = 10  # the threshold "piano key" bars' height
RUNWAY_ICON_KEY_W_PX = 4  # ... and width; two per end, either side of the centreline


def draw_runway_icon(draw, center_x, top_y, ink_idx):
    """Draw the runway mark centred on `center_x`, its top edge at `top_y`,
    and return its height. A first pass used a solid bar at each end, which
    read as a battery at glyph size; the threshold "piano keys" real runways
    carry are what make the mark read as a runway, so it draws two short
    bars at each end instead, either side of the dashed centreline.
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

    `battery_low`: when True, draws the bottom-left battery-low icon in
    the state's own ink after the previous-flight card, before the
    closing palette guard rail.

    `source_fault`: when True, draws the bottom-centre source-fault
    badge in that same ink. Both indicators resolve their ink through the
    active theme's `state_ink_index()`, so neither can introduce an
    index outside the current theme's palette.
    """
    if state not in STATE_BACKGROUND:
        raise ValueError("unknown state %r (expected 'departing', 'arriving', or 'empty')" % (state,))
    bg_idx = state_background_index(state, theme_id=theme_id)
    fg_idx = state_ink_index(state, theme_id=theme_id)

    # Whether the background is dithered and which weight the text roles
    # use are both properties of the active theme
    # (`device_config.theme_dithered()`/`theme_weight()`), resolved once
    # here and threaded through - see THEMES' own module comment in
    # device_config.py for why neither is a fixed function of bg_idx alone.
    normalised_theme_id = device_config.normalise_theme_id(theme_id)
    theme_dithered = device_config.theme_dithered(normalised_theme_id)
    weight = device_config.theme_weight(normalised_theme_id)

    # Whether this theme carries a diagonal band, and that band's own
    # colour/dither flag, resolved once here (same pattern as
    # theme_dithered/weight just above) and threaded through to the
    # band-dispatch and draw_top_labels() calls below. `band_idx`/
    # `band_dithered_flag` are only meaningful when `is_band_theme` is True -
    # theme_band_index()/theme_band_dithered() are absent-key-safe and would
    # otherwise return None/False for a non-band theme, but the ternaries
    # below make that explicit rather than relying on the accessors' defaults.
    is_band_theme = device_config.theme_is_band(normalised_theme_id)
    band_idx = device_config.theme_band_index(normalised_theme_id) if is_band_theme else None
    band_dithered_flag = device_config.theme_band_dithered(normalised_theme_id) if is_band_theme else False

    # A dithered blend toward White (dither.dithered_state_background())
    # is the only way to visually lighten a fixed physical ink for themes
    # whose raw ink reads too dark/saturated at full-panel coverage;
    # bg_idx stays the dominant index. This treatment is not universal -
    # a theme with `dithered: False` (every "pure" colour, confirmed on
    # real glass to need no lightening) gets a flat fill instead
    # (`panel_format.new_canvas()`), matching what the empty state and
    # the White theme have always used.
    canvas = dither.dithered_state_background(bg_idx) if theme_dithered else pf.new_canvas(bg_idx)

    # For a band theme, paint the diagonal band immediately after the
    # background fill and before anything else, so it sits behind every
    # subsequent draw (top labels, illustrations, text) and illustrations
    # occlude it naturally. No-op for every non-band theme.
    if is_band_theme:
        draw_diagonal_band(canvas, band_idx, dithered=band_dithered_flag)

    # The thin frame outline is no longer drawn. FRAME_INSET_FRAC
    # deliberately survives below as pure layout geometry feeding
    # inner_width, and draw_source_fault_badge() independently derives
    # its own bottom anchor from the same constant. The helper itself,
    # draw_frame, is retained but no longer called from this render path.

    # Top row: state label top-left, runway tag top-right, both at the
    # existing MARGIN inset (inside the frame, not on it).
    # `band_theme=is_band_theme`: band themes get the merged
    # state-label/airport-code + short runway-tag split; every other theme
    # keeps today's unsplit pair (draw_top_labels()'s default is False).
    draw_top_labels(canvas, state, fg_idx, bg_idx, weight, runway_id=runway_id, band_theme=is_band_theme)

    # Main flight: the current detection's real per-airline illustration,
    # always nose-left (no mirroring).
    inner_width = WIDTH * (1 - 2 * FRAME_INSET_FRAC)
    main_w = round(inner_width * MAIN_ILLUSTRATION_WIDTH_FRAC)

    main_path = illustrations.select_illustration(route, flight.get("aircraft_type"))
    main_placement = None
    main_resized = _load_illustration_safely(main_path, main_w)
    if main_resized is not None:
        # Centres the main illustration on both axes: the pixels that are
        # actually painted, not the source rectangle - horizontally via
        # `_left_for_centered_content()`, and vertically via
        # `_top_for_centered_content()` - the exact helper the previous
        # card below already uses. main_top can only be computed here,
        # after main_resized exists: `_top_for_centered_content()` reads
        # the resized image's own opaque bbox.
        main_left = _left_for_centered_content(main_resized, WIDTH / 2)
        main_top = _top_for_centered_content(main_resized, HEIGHT * MAIN_ILLUSTRATION_CENTER_Y_FRAC)
        main_placement = draw_illustration(canvas, main_resized, main_left, main_top)
        # The full placement rectangle, not `.content`: this is a "does
        # the element fall off the canvas" guard, so the conservative
        # geometric footprint is the right thing to bound.
        _assert_within_canvas(main_placement.rect, "main aircraft illustration")
        draw_main_text_block(canvas, flight, state, route, main_placement, fg_idx, bg_idx, weight, band_idx=band_idx)

    # Previous flight: a real second flight card - the detection
    # immediately preceding this one (poll_loop.py's two-deep history).
    # Same nose-left convention as the main illustration, no mirroring.
    if previous_flight is not None and main_placement is not None:
        prev_path = illustrations.select_illustration(previous_route, (previous_flight or {}).get("aircraft_type"))
        # SIZE derives from the main illustration's full RENDERED width
        # (`.rect`), not `.content`: `.rect`'s width is a constant 992 for
        # every file, so this card's size is stable. Deriving it from the
        # main illustration's opaque width (933-984px) would make the
        # PREVIOUS card's size depend on which airline is in the MAIN
        # slot - the same previous aircraft would render up to 5% larger
        # or smaller depending on what flew before it. That is a new
        # per-file coupling, and strictly worse than the ~28px
        # visible-width variation it would remove. Sizing stays stable;
        # only POSITION follows the painted pixels.
        main_rect = main_placement.rect
        prev_w = round((main_rect[2] - main_rect[0]) * PREVIOUS_ILLUSTRATION_WIDTH_FRAC)
        prev_resized = _load_illustration_safely(prev_path, prev_w)
        if prev_resized is not None:
            # POSITION, by contrast, is anchored to painted pixels on both
            # axes: the previous aircraft's visible right edge lands
            # exactly on the main aircraft's visible right edge
            # (right-aligned to the main illustration's own right edge,
            # which the eye reads as the aircraft's edge, not its
            # padding's), and its visible vertical midpoint lands on
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
    """Return the pre-pack "P"-mode canvas for `flight` in `state`
    ("departing" / "arriving" / "empty"). Public (not `_build_canvas`) so
    callers - notably server/test_render.py's anti-aliasing assertions,
    which read Image.getcolors() directly - never have to reach into
    private render state.

    `route` is the normalised dict produced by either
    `server.plane.enrich.lookup_route()` (a full route: airline + origin +
    destination) or `server.plane.enrich.airline_only_route()` (airline
    name only, the four city/IATA fields `None`) - `poll_loop.py` chooses
    between them via `server.plane.enrich.resolve_route()`. `route` is
    `None` on a full enrichment miss (neither source resolved anything) or
    for the empty state.

    `previous_flight`/`previous_route`/`previous_state` are the detection
    immediately preceding `flight`, or all None if none exists yet (e.g.
    the very first detection since the state directory was last empty) -
    the previous flight card is simply omitted in that case. Ignored for
    the empty state, which has no flight to enrich.

    `theme_id` selects the DEPARTING/ARRIVING background and ink colours
    from `server/device_config.py`'s `THEMES` registry; an unrecognised id
    degrades to the default theme rather than raising. Ignored for the
    empty state, which is always White/Black.

    `runway_id` selects the top-right tag and (for the empty state) the
    heading text from `device_config`'s `RUNWAYS` registry; an
    unrecognised id degrades to the default runway rather than raising.

    `source_fault` draws a small alert badge pointing at the companion
    page when true. It must be set only when every ADS-B source the
    server queries has failed (`poll_loop.py`'s classification of
    `detect.poll_current_aircraft()`'s diagnostics dict) - never merely
    because no aircraft was selected, which is Orly's ordinary quiet state
    and firing on it would be a false alarm.

    `battery_low`: when True, draws the bottom-left battery-low icon - in
    every one of the three states, including empty. Independent of
    `source_fault`; both may be true at once.

    `quiet_hours_until`: when `state == "quiet_hours"`, the "HH:MM" local
    (Europe/Paris) wall-clock end-of-window string shown as "Back at
    HH:MM"; a missing/empty/non-string value omits the body line instead
    of raising. `theme_id`, `runway_id`, `route`, and the three
    `previous_*` arguments are all ignored for this state - it is always
    a flat White/Black screen with no flight to enrich, exactly like the
    empty state ignores `theme_id`. It is also ignored entirely when
    `state == "display_off"`: the display-off branch below never forwards
    it, even when a caller has one in hand from a shared hold-branch call
    site that also serves quiet-hours - dropping the argument here is
    what guarantees no return-time string can ever reach the off screen,
    no matter what the caller passes.

    `state == "display_off"`: a dedicated, always-White/Black screen with
    the locked "DISPLAY OFF" heading and a fixed body constant - no
    `theme_id`, `runway_id`, `route`, `previous_*`, or
    `quiet_hours_until` value reaches it, exactly like the quiet-hours and
    empty states ignore `theme_id`.

    `state == "battery_empty"`: the top-priority hold, dispatched before
    every other state check below. A dedicated, always-White/Black screen
    with the locked "BATTERY EMPTY" heading - `theme_id`, `runway_id`,
    `route`, `previous_*`, `source_fault`, `battery_low` and
    `quiet_hours_until` are all ignored, not merely unused: the image's
    bytes must stay byte-stable for the whole parked episode
    (poll_loop.py's hourly check-in relies on the hash never changing),
    and a badge or theme toggling mid-episode would break that.
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
    """Return a packed 960,000-byte panel for `flight` (the normalised dict
    from detect.select_runway3_aircraft(), or None) in `state`
    ("departing" / "arriving" / "empty" / "quiet_hours" / "display_off").

    `state` is the return value of a server.plane.runway_config call
    (poll_loop.py never hardcodes it) - server.plane.runway_config.py's
    STATE_DEPARTING/STATE_ARRIVING constants are the exact strings
    "departing"/"arriving" this function and build_canvas() key their
    per-state dicts on.

    `route`/`previous_flight`/`previous_route`/`previous_state`/`theme_id`/
    `runway_id`/`source_fault`/`battery_low`/`quiet_hours_until` are passed
    straight through to build_canvas() - see build_canvas()'s own
    docstring for the full contract of each, including what `route` may
    be (a full route or an airline-only route), `battery_low`'s per-state
    behaviour, and `quiet_hours_until`'s "quiet_hours"-only contract.
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
