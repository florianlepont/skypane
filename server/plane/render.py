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
_FIT_STEP_PX = 2

# --- Colour section (state-scoped, unchanged since 02-UI-SPEC.md Revision
# 2) - keyed by runway_config's STATE_* constants (not bare string
# literals) so the two modules cannot drift apart. --------------------------
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

EMPTY_HEADING_TEXT = "Watching Runway 3"
EMPTY_BODY_TEXT = "No aircraft detected yet — the display updates the moment one is."
TOP_RIGHT_TAG_TEXT = "ORY · RWY 3"
ROUTE_FALLBACK_TEXT = "Route unavailable"

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


def draw_top_labels(canvas, state, ink_idx):
    """D-26 top row: the state label (top-left) and the static
    `TOP_RIGHT_TAG_TEXT` (top-right), both PT Serif Regular at the small
    sizes D-26 confirmed, both at the existing `MARGIN` inset (inside the
    frame, not on it) - no icon glyph, no letter-spacing/tracking (that was
    the old, larger zone-1 treatment; superseded).
    """
    draw = ImageDraw.Draw(canvas)
    label_font = _font(STATE_LABEL_FONT)
    tag_font = _font(TOP_TAG_FONT)

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

    tag_bbox = draw.textbbox((WIDTH - MARGIN, MARGIN), TOP_RIGHT_TAG_TEXT, font=tag_font, anchor="ra")
    _assert_within_canvas(tag_bbox, "top-right tag")
    draw.text((WIDTH - MARGIN, MARGIN), TOP_RIGHT_TAG_TEXT, font=tag_font, fill=ink_idx, anchor="ra")


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
    """`"{callsign} to|from {city}"`, or bare `callsign` on an enrichment
    miss (no half-resolved route is ever shown - matches the discipline
    `enrich.lookup_route()`'s own docstring already establishes). D-26:
    ordinary lowercase "to"/"from" as sentence text, not the old tracked-
    caps Label-role prefix.
    """
    callsign = flight.get("callsign") or (flight.get("hex") or "").upper() or "?"
    city = enrich.city_for_state(route, state) if route is not None else None
    if city:
        direction = "to" if state == runway_config.STATE_DEPARTING else "from"
        return "%s %s %s" % (callsign, direction, city)
    return callsign


def _flight_line2_text(route):
    """The airline name, or `ROUTE_FALLBACK_TEXT` on an enrichment miss.

    D-26's brief also asked for `{airline} · {aircraft_type}` - real
    per-flight aircraft-type data does not exist yet (that is Phase 3.1,
    deliberately deferred pending ADS-B aircraft-type verification), so
    this line is the airline name alone rather than a fabricated type.
    """
    if route is not None:
        airline_name = route.get("airline_name")
        if airline_name:
            return airline_name
    return ROUTE_FALLBACK_TEXT


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
    line2_text = _flight_line2_text(route)

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
    line2_text = _flight_line2_text(route)

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


def _build_empty_canvas():
    canvas = pf.new_canvas(IDX_WHITE)
    draw = ImageDraw.Draw(canvas)
    heading_font = _font(EMPTY_HEADING_FONT)
    body_font = _font(EMPTY_BODY_FONT)
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


def _build_active_canvas(flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None):
    if state not in STATE_BACKGROUND:
        raise ValueError("unknown state %r (expected 'departing', 'arriving', or 'empty')" % (state,))
    bg_idx = STATE_BACKGROUND[state]
    fg_idx = STATE_INK[state]

    # D-21: flat single-color background field - no dithered mood gradient.
    canvas = pf.new_canvas(bg_idx)

    # D-26: thin frame, inset ~2.5% of canvas width from every edge.
    draw_frame(canvas, fg_idx)

    # D-26 top row: state label top-left, static tag top-right, both at the
    # existing MARGIN inset (inside the frame, not on it).
    draw_top_labels(canvas, state, fg_idx)

    # D-25/D-26 main flight: the current detection's real per-airline
    # illustration, always nose-left (D-24 - no mirroring).
    inner_width = WIDTH * (1 - 2 * FRAME_INSET_FRAC)
    main_w = round(inner_width * MAIN_ILLUSTRATION_WIDTH_FRAC)
    main_top = round(HEIGHT * MAIN_ILLUSTRATION_TOP_FRAC)

    main_path = illustrations.select_illustration(route)
    main_bbox = None
    if main_path is not None:
        main_resized = _resize_illustration(main_path, main_w)
        main_left = (WIDTH - main_resized.size[0]) // 2
        main_bbox = draw_illustration(canvas, main_resized, main_left, main_top)
        _assert_within_canvas(main_bbox, "main aircraft illustration")
        draw_main_text_block(canvas, flight, state, route, main_bbox, fg_idx)

    # D-25/D-26 previous flight: a real second flight card - the detection
    # immediately preceding this one (poll_loop.py's two-deep history).
    # Same nose-left convention as the main illustration, no mirroring.
    if previous_flight is not None and main_bbox is not None:
        prev_path = illustrations.select_illustration(previous_route)
        if prev_path is not None:
            prev_w = round((main_bbox[2] - main_bbox[0]) * PREVIOUS_ILLUSTRATION_WIDTH_FRAC)
            prev_resized = _resize_illustration(prev_path, prev_w)
            prev_h = prev_resized.size[1]
            prev_left = main_bbox[2] - prev_resized.size[0]
            prev_top = round(HEIGHT * PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC - prev_h / 2)
            prev_bbox = draw_illustration(canvas, prev_resized, prev_left, prev_top)
            _assert_within_canvas(prev_bbox, "previous aircraft illustration")
            draw_previous_text_block(canvas, previous_flight, previous_state, previous_route, prev_bbox, fg_idx)

    # Guard rail: every index on the panel is legal, and the flat
    # background field is provably dominant.
    _assert_legal_palette(canvas, bg_idx)

    return canvas


def build_canvas(flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None):
    """Return the pre-pack "P"-mode canvas for `flight` in `state`
    ("departing" / "arriving" / "empty"). Public (not `_build_canvas`) so
    callers - notably server/test_render.py's anti-aliasing assertions,
    which read Image.getcolors() directly - never have to reach into
    private render state.

    `route` is the normalised dict from server.plane.enrich.lookup_route()
    (or None on an enrichment miss / for the empty state).

    `previous_flight`/`previous_route`/`previous_state` (D-25/D-26) are the
    detection immediately preceding `flight`, or all None if none exists
    yet (e.g. the very first detection since the state directory was last
    empty) - the previous flight card is simply omitted in that case.
    Ignored for the empty state, which has no flight to enrich.
    """
    if flight is None or state == "empty":
        return _build_empty_canvas()
    return _build_active_canvas(
        flight,
        state,
        route=route,
        previous_flight=previous_flight,
        previous_route=previous_route,
        previous_state=previous_state,
    )


def render_panel(flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None):
    """Return a packed 960,000-byte panel for `flight` (the normalised dict
    from detect.select_runway3_aircraft(), or None) in `state`
    ("departing" / "arriving" / "empty").

    `state` is the return value of a server.plane.runway_config call
    (poll_loop.py never hardcodes it) - server.plane.runway_config.py's
    STATE_DEPARTING/STATE_ARRIVING constants are the exact strings
    "departing"/"arriving" this function and build_canvas() key their
    per-state dicts on.

    `route`/`previous_flight`/`previous_route`/`previous_state` are passed
    straight through to build_canvas() (D-25/D-26).
    """
    canvas = build_canvas(
        flight,
        state,
        route=route,
        previous_flight=previous_flight,
        previous_route=previous_route,
        previous_state=previous_state,
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
        route = None if args.no_route else _PREVIEW_ROUTE
        if args.previous_callsign:
            previous_flight = {"hex": args.previous_hex, "callsign": args.previous_callsign}
            previous_route = None if args.no_route else _PREVIEW_PREVIOUS_ROUTE
            previous_state = runway_config.STATE_ARRIVING if args.state == runway_config.STATE_DEPARTING else runway_config.STATE_DEPARTING

    canvas = build_canvas(
        flight,
        args.state,
        route=route,
        previous_flight=previous_flight,
        previous_route=previous_route,
        previous_state=previous_state,
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
