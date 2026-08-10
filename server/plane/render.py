#!/usr/bin/env python3
"""Minimal-but-real panel renderer for the plane view (PLANE-01/02/03).

Implements the state field, state label, flight-number caption, and bottom
static tag - 02-03 adds the silhouette centrepiece, 02-04 adds the route
and airline lines. Every draw call goes directly onto a "P"-mode canvas
from panel_format.new_canvas() with an integer palette-index fill, never an
RGB tuple and never an RGB compose-then-quantize step (02-RESEARCH.md
Architecture Pattern 1) - this is the mechanism that satisfies
02-UI-SPEC.md's binding "disable anti-aliasing" rule for free.

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
from server.panel_format import IDX_BLACK, IDX_BLUE, IDX_GREEN, IDX_WHITE, WIDTH, HEIGHT
from server.plane import runway_config

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

# --- UI-SPEC Typography (02-UI-SPEC.md) ------------------------------------
FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")
)
_INTER_REGULAR = os.path.join(FONT_DIR, "Inter-Regular.ttf")
_INTER_BOLD = os.path.join(FONT_DIR, "Inter-Bold.ttf")

# (font_path, size, weight) per role - weight is documentation only (the
# path already selects the correct static weight file).
LABEL_FONT = (_INTER_BOLD, 36, 700)
BODY_FONT = (_INTER_REGULAR, 56, 400)
HEADING_FONT = (_INTER_BOLD, 88, 700)

# Label role is uppercase with widened letter-spacing (Pillow has no native
# tracking API - UI-SPEC's Typography note calls for manual per-glyph
# advance widening, see draw_tracked_text()). This tracking value is a
# render-detail left to implementation discretion by UI-SPEC (not itself
# spec'd to an exact pixel count).
LABEL_TRACKING_PX = 4

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

EMPTY_HEADING_TEXT = "Watching Runway 3"
EMPTY_BODY_TEXT = "No aircraft detected yet — the display updates the moment one is."
BOTTOM_TAG_TEXT = "ORY · RWY 3"

# Reserved vertical footprint for zone 3 (silhouette, filled by 02-03) so
# the flight-number caption (zone 5) lands where 02-UI-SPEC.md's Layout &
# Composition puts it and 02-03/02-04 can slot their content in above it
# without ever moving what this plan already renders. Zone 1 (state label)
# is now drawn by this plan (draw_state_label()) within this same reserved
# footprint.
_ZONE1_STATE_LABEL_HEIGHT = 96  # "roughly the same vertical footprint... ~96px" (UI-SPEC zone 1)
_ZONE3_SILHOUETTE_MAX_HEIGHT = 260  # UI-SPEC zone 3: "~220-260px tall"
_ZONE3_HEIGHT = SPACE_3XL + _ZONE3_SILHOUETTE_MAX_HEIGHT + SPACE_3XL  # 3xl padding both sides

FLIGHT_NUMBER_TOP_Y = (
    MARGIN
    + _ZONE1_STATE_LABEL_HEIGHT
    + SPACE_2XL
    + _ZONE3_HEIGHT
    + SPACE_XL
)  # = 1028

_font_cache = {}


def _font(spec):
    path, size, _weight = spec
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def _assert_in_safe_box(bbox, label):
    left, top, right, bottom = bbox
    sb_left, sb_top, sb_right, sb_bottom = SAFE_BOX
    assert left >= sb_left and top >= sb_top and right <= sb_right and bottom <= sb_bottom, (
        "%s bounding box %r exceeds the inviolable %dpx safe box %r"
        % (label, bbox, MARGIN, SAFE_BOX)
    )


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


def draw_state_label(canvas, state, ink_idx):
    """Draw UI-SPEC zone 1 - the state label row: the plane-takeoff/
    plane-landing glyph (filled `ink_idx`) + SPACE_XS gap + tracked
    uppercase Label-role text (`STATE_LABEL_TEXT[state]`), horizontally
    centred, top-anchored within the 96px zone-1 band already reserved by
    FLIGHT_NUMBER_TOP_Y's zone stacking. No filled rectangle behind it -
    02-UI-SPEC.md Revision 2 explicitly removed the mode badge (a same-
    colour badge would be invisible against its own full-bleed background).

    Called only for the active (departing/arriving) states - the Empty
    state renders no state label and no glyph at all (nothing detected yet,
    nothing to depict).
    """
    draw = ImageDraw.Draw(canvas)
    label_font = _font(LABEL_FONT)
    text = STATE_LABEL_TEXT[state]

    # Size the glyph to the Label role's cap height, per 02-02-PLAN.md Task 3.
    cap_bbox = label_font.getbbox("H")
    cap_height = cap_bbox[3] - cap_bbox[1]
    icon_size = (cap_height, cap_height)

    label_ascent, label_descent = label_font.getmetrics()
    text_height = label_ascent + label_descent
    text_width = _tracked_text_width(label_font, text, LABEL_TRACKING_PX)

    row_height = max(cap_height, text_height)
    block_width = cap_height + SPACE_XS + text_width

    center_x = WIDTH // 2
    zone1_top = MARGIN
    row_top = zone1_top + (_ZONE1_STATE_LABEL_HEIGHT - row_height) // 2
    block_left = center_x - block_width / 2

    icon_x = block_left
    icon_y = row_top + (row_height - cap_height) // 2
    mask = load_binary_mask(STATE_GLYPH_PATH[state], icon_size)
    icon_bbox = (icon_x, icon_y, icon_x + cap_height, icon_y + cap_height)
    _assert_in_safe_box(icon_bbox, "state label glyph")
    canvas.paste(ink_idx, (int(icon_x), int(icon_y)), mask=mask)

    text_x = icon_x + cap_height + SPACE_XS
    text_y = row_top + (row_height - text_height) // 2
    text_bbox = _tracked_text_bbox(label_font, (text_x, text_y), text, LABEL_TRACKING_PX)
    _assert_in_safe_box(text_bbox, "state label text")
    draw_tracked_text(draw, (text_x, text_y), text, label_font, ink_idx, tracking=LABEL_TRACKING_PX)


def _build_empty_canvas():
    canvas = pf.new_canvas(IDX_WHITE)
    draw = ImageDraw.Draw(canvas)
    heading_font = _font(HEADING_FONT)
    body_font = _font(BODY_FONT)
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


def _build_active_canvas(flight, state):
    if state not in STATE_BACKGROUND:
        raise ValueError("unknown state %r (expected 'departing', 'arriving', or 'empty')" % (state,))
    bg_idx = STATE_BACKGROUND[state]
    fg_idx = STATE_INK[state]

    canvas = pf.new_canvas(bg_idx)
    draw = ImageDraw.Draw(canvas)
    center_x = WIDTH // 2

    # UI-SPEC zone 1: state label - plane-takeoff/plane-landing glyph +
    # tracked DEPARTING/ARRIVING text, no filled rectangle behind it (the
    # Revision 2 "mode badge removed" decision).
    draw_state_label(canvas, state, fg_idx)

    # UI-SPEC zone 5: flight-number caption, Heading size, horizontally
    # centred. Falls back to the aircraft's hex uppercased when no callsign
    # was recovered, so the panel never renders an empty hero line.
    callsign = flight.get("callsign") or (flight.get("hex") or "").upper() or "?"
    heading_font = _font(HEADING_FONT)
    heading_bbox = draw.textbbox((center_x, FLIGHT_NUMBER_TOP_Y), callsign, font=heading_font, anchor="ma")
    _assert_in_safe_box(heading_bbox, "flight number caption")
    draw.text((center_x, FLIGHT_NUMBER_TOP_Y), callsign, font=heading_font, fill=fg_idx, anchor="ma")

    # UI-SPEC zone 11: bottom-anchored static tag, Label size, tracked
    # letter-spacing, White.
    label_font = _font(LABEL_FONT)
    tag_width = _tracked_text_width(label_font, BOTTOM_TAG_TEXT, LABEL_TRACKING_PX)
    label_ascent, label_descent = label_font.getmetrics()
    tag_line_height = label_ascent + label_descent
    tag_x = center_x - tag_width / 2
    tag_y = HEIGHT - MARGIN - tag_line_height
    tag_bbox = (tag_x, tag_y, tag_x + tag_width, tag_y + tag_line_height)
    _assert_in_safe_box(tag_bbox, "bottom static tag")
    draw_tracked_text(draw, (tag_x, tag_y), BOTTOM_TAG_TEXT, label_font, fg_idx, tracking=LABEL_TRACKING_PX)

    return canvas


def build_canvas(flight, state):
    """Return the pre-pack "P"-mode canvas for `flight` in `state`
    ("departing" / "arriving" / "empty"). Public (not `_build_canvas`) so
    callers - notably server/test_render.py's anti-aliasing assertions,
    which read Image.getcolors() directly - never have to reach into
    private render state.
    """
    if flight is None or state == "empty":
        return _build_empty_canvas()
    return _build_active_canvas(flight, state)


def render_panel(flight, state):
    """Return a packed 960,000-byte panel for `flight` (the normalised dict
    from detect.select_runway3_aircraft(), or None) in `state`
    ("departing" / "arriving" / "empty").

    `state` is the return value of a server.plane.runway_config call
    (poll_loop.py never hardcodes it) - server.plane.runway_config.py's
    STATE_DEPARTING/STATE_ARRIVING constants are the exact strings
    "departing"/"arriving" this function and build_canvas() key their
    per-state dicts on.
    """
    canvas = build_canvas(flight, state)
    return pf.pack_panel(canvas)


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
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    flight = None
    if args.state != "empty":
        flight = {"hex": args.hex, "callsign": args.callsign}

    canvas = build_canvas(flight, args.state)
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
