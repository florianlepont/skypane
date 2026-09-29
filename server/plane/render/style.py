"""Spacing scale, typography roles, state colours, headline copy, and the
frame/band/battery geometry constants for the plane panel renderer.

Also holds the two canvas-bounds assertion helpers (`_assert_in_safe_box`/
`_assert_within_canvas`) and the diagonal band's pure edge-geometry
helpers (`_band_edges`/`_band_center_x`), since both `text.py` and
`layout.py` need them and putting them here avoids a two-way import
between those siblings.
"""
import os

from server import device_config
from server.panel_format import HEIGHT, IDX_BLACK, IDX_WHITE, WIDTH
from server.plane import runway_config

# --- Spacing scale ---------------------------------------------------------
SPACE_XS = 8
SPACE_SM = 16
SPACE_MD = 32
SPACE_LG = 64

# MARGIN is the top-row labels' inset, not a blanket margin (see the
# package docstring in __init__.py).
MARGIN = SPACE_LG
SAFE_BOX = (MARGIN, MARGIN, WIDTH - MARGIN, HEIGHT - MARGIN)  # (64, 64, 1136, 1536)

# --- Typography --------------------------------------------------------
FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "fonts")
)
PT_SERIF_REGULAR = os.path.join(FONT_DIR, "PTSerif-Regular.ttf")
PT_SERIF_BOLD = os.path.join(FONT_DIR, "PTSerif-Bold.ttf")

# Per-role (font_path, size, weight); weight is documentation only. Bold
# is the base weight (carries legibility against a dithered background);
# `text._role_font()`/`text._role_fit_text_size()` substitute Regular when
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
# (STATE_LABEL_FONT, TOP_TAG_FONT) via text.draw_tracked_text() in
# layout.draw_top_labels(). Screen-preview-validated only - never checked
# against real Spectra 6 ink.
LABEL_TRACKING_PX = 6

# Band-theme top-label direction word. Only consulted by
# layout.draw_top_labels() when `band_theme=True`.
_BAND_TOP_LABEL_DIRECTION = {
    runway_config.STATE_DEPARTING: "FROM",
    runway_config.STATE_ARRIVING: "TO",
}

# Overflow floors (text.fit_text_size()'s per-role minimums) - real city/
# airline names shrink in small steps rather than clipping, wrapping
# mid-word, or overflowing, but never below these named limits.
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
# hold_screens.py's builder wraps each sentence separately to honour the
# break.
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
# equality check; hold_screens.py's `_build_display_off_canvas()` wraps
# each sentence separately.
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

# Locked English copy, same fixed-string convention as NO_CONNECTION_* -
# the server never renders this screen either. The firmware draws it on
# its own (firmware/tools/gen_fault_screen.py --screen updating bakes it
# into updating_screen_mask.h at build time), so changing either sentence
# requires regenerating that header or server/test_updating_screen_mask.py's
# drift test fails. Body line 2 deliberately does not promise success -
# "when it's ready" covers both a clean install and a silent
# rollback-and-resume, both of which end the same way from the reader's
# perspective.
UPDATING_HEADING_TEXT = "UPDATING"
UPDATING_BODY_LINES = (
    "Installing a firmware update.",
    "The frame will restart when it's ready.",
)
UPDATING_BODY_TEXT = " ".join(UPDATING_BODY_LINES)

# --- The dimmed hold composition ------------------------------------------
# Shared by DISPLAY OFF and QUIET HOURS via hold_screens._build_dimmed_hold_canvas():
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
# diagnosed. Glyph is small so layout._assert_legal_palette()'s
# background-dominance assertion still holds - see
# layout.draw_source_fault_badge().
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
# Measured from the OPAQUE-PIXEL bottom edge (`layout.IllustrationPlacement.
# content`), not the source rectangle: the soft drop-shadow band below
# each aircraft varies per file, and `layout.draw_illustration()` never
# paints it (hard-thresholded away).
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
