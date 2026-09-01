#!/usr/bin/env python3
"""Spike 003 (extended): full poster-composition reproduction - corrected
trapezoid band geometry (measured from the developer's reference image,
not eyeballed) + the reference's text hierarchy (big flight number, small
dash rule, tracked-caps route line, airline name), left-anchored under
the aircraft instead of the current centred main text block.

Band geometry measured directly from the reference PNG
(~/Downloads/d8b790c7-1316-4121-b23c-749d9ada7491.png, 1023x1537) via
per-row pixel scanning + linear regression on both edges independently -
it is a TRAPEZOID (widens going down), not a parallelogram like this
spike's first pass assumed:
  top edge:    left=58.18% width, right=85.23% width (top width ~27%)
  bottom edge: left=7.42% width,  right=47.72% width  (bottom width ~40%)

Text hierarchy measured the same way (bounding boxes of dark-ink regions):
  - Flight number ("AF1006"): big bold serif, left-anchored at the same
    x as the top-left state label, starting ~49% down the canvas.
  - A thin ~1-2px dash rule directly under both the state label and the
    flight number - a minor decorative detail, included for fidelity.
  - Route line ("PARIS -- NEW YORK"): small-caps tracked text, directly
    below the flight number - reuses the exact draw_tracked_text()/
    LABEL_TRACKING_PX technique already shipped for the top labels
    (quick task 260831-njw), just applied to a new text role.
  - Airline name ("Air France"): italic in the reference. PT Serif
    Italic is NOT currently vendored (only Regular/Bold exist in
    server/assets/fonts/) - this spike renders it in Regular as a
    placeholder and flags the gap; an italic variant would need vendoring
    before this could ship as-is.

Monkeypatches panel_format.new_canvas() (band) and
render.draw_main_text_block() (text hierarchy) for the duration of this
script only - server/plane/render.py is never edited.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "server", ".."))

from server.plane import render, illustrations
from server import panel_format as pf
from server.plane import dither
from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(__file__), "renders")
os.makedirs(OUT_DIR, exist_ok=True)

TEST_FLIGHT = {"hex": "39de41", "callsign": "AFR1234", "aircraft_type": "A320"}
TEST_ROUTE = {
    "airline_name": "Air France",
    "callsign_iata": "AF1234",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "JFK",
    "destination_city": "New York",
}
TEST_PREV_ROUTE = {
    "airline_name": "Vueling Airlines",
    "callsign_iata": "VY1234",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "BCN",
    "destination_city": "Barcelona",
}

# --- Band geometry, measured from the reference (trapezoid, not a parallelogram) ---
# Round 11: with "RWY 3" alone on the right (see patched_draw_top_labels
# below) instead of the full "ORY · RWY 3", no shift is needed at all -
# the reference's own as-measured position already clears both
# constraints. See that function's own comment for the numbers.
BAND_SHIFT_FRAC = 0.0
BAND_TOP_LEFT_FRAC = 0.5818 + BAND_SHIFT_FRAC
BAND_TOP_RIGHT_FRAC = 0.8523 + BAND_SHIFT_FRAC
BAND_BOT_LEFT_FRAC = max(0.0, 0.0742 + BAND_SHIFT_FRAC)
BAND_BOT_RIGHT_FRAC = 0.4772 + BAND_SHIFT_FRAC


def draw_reference_band(canvas, band_idx, dithered=False):
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


_TRUE_ORIG_NEW_CANVAS = pf.new_canvas


def make_patched_new_canvas(band_idx, dithered):
    def _patched(bg_index):
        canvas = _TRUE_ORIG_NEW_CANVAS(bg_index)
        if bg_index == pf.IDX_WHITE:
            draw_reference_band(canvas, band_idx, dithered)
        return canvas
    return _patched


# --- Round 11 (developer's correction to round 7/9): split the airport
# code to the LEFT (merged with the state label - "DEPARTING FROM ORY" /
# "ARRIVING TO ORY") and keep a SHORTER tag on the right ("RWY 3" alone,
# not "ORY · RWY 3"). The shorter right-side tag starts much further
# right (measured: 0.8817 vs the full tag's 0.8117 - a 7pt gain) than the
# full tag did, which is what actually resolves round 9/10's conflict:
# with this split, BAND_SHIFT_FRAC=0.0 (the reference's own unshifted,
# as-measured position - no shift at all) clears BOTH the shorter tag
# (2.9pt margin) AND the below-illustration nose-aligned main text (5pt
# margin, verified against the precisely measured text-block right edge
# of 0.265, not the earlier round's rough guess of 0.33) at once.
_MERGED_LABEL_DIRECTION = {
    render.runway_config.STATE_DEPARTING: "FROM",
    render.runway_config.STATE_ARRIVING: "TO",
}


def patched_draw_top_labels(canvas, state, ink_idx, bg_idx, weight, runway_id=None):
    if runway_id is None:
        runway_id = render.device_config.DEFAULT_RUNWAY_ID
    draw = ImageDraw.Draw(canvas)
    label_font = render._role_font(render.STATE_LABEL_FONT, weight)
    tag_font = render._role_font(render.TOP_TAG_FONT, weight)
    direction = _MERGED_LABEL_DIRECTION[state]
    full_tag = render.runway_tag_text(runway_id)
    airport_code, _sep, runway_part = full_tag.partition(" · ")

    merged_text = "%s %s %s" % (render.STATE_LABEL_TEXT[state], direction, airport_code)
    render.draw_tracked_text(draw, (render.MARGIN, render.MARGIN), merged_text, label_font, ink_idx, render.LABEL_TRACKING_PX)

    tag_w = render._tracked_text_width(tag_font, runway_part, render.LABEL_TRACKING_PX)
    tag_x = render.WIDTH - render.MARGIN - tag_w
    render.draw_tracked_text(draw, (tag_x, render.MARGIN), runway_part, tag_font, ink_idx, render.LABEL_TRACKING_PX)


# --- Text hierarchy, left-anchored, reference-inspired presentation over
# the REAL content ladder (_flight_line1_text()/_flight_line2_text(),
# unmodified) - round 4's fix: round 3 invented a "{origin} — {dest}"
# route-pair line and a bare airline name that don't exist anywhere in
# the shipped four-tier content ladder (D-08/D-09/D-10), silently
# dropping the aircraft type and the raw-callsign guarantee's tiered
# fallback behaviour. This version calls the real functions and only
# restyles their output - it never invents content the real project
# doesn't already produce. Developer's explicit call: PT Serif Regular
# stays the body-copy weight for e-ink (no italic vendored, and none
# wanted for this role - Bold already reads "agressif" per Phase 8's own
# on-glass finding, D-06).
FLIGHT_NUMBER_FONT = (render.PT_SERIF_BOLD, 56, 700)
ROUTE_LINE_FONT = (render.PT_SERIF_REGULAR, 22, 400)
AIRLINE_LINE_FONT = (render.PT_SERIF_REGULAR, 20, 400)
DASH_W = 24
DASH_GAP = 10
ABOVE_ILLUSTRATION_GAP_PX = 32  # gap between the text block's bottom and the fuselage's VISUAL top (see below)
FUSELAGE_WIDTH_THRESHOLD = 0.4  # row counts as "fuselage" once its opaque width crosses this fraction of the max


def _fuselage_visual_top_y(route, aircraft_type, main_placement):
    """Return the canvas y where the illustration's silhouette first
    looks like "the plane" to the eye - not `main_placement.content[1]`,
    the topmost technically-opaque pixel.

    Round 5 fix (developer: text reads "très écarté" from the aircraft).
    Measured directly on the Air France file: the topmost opaque pixel
    (the swept tail fin's tip) sits only 8px into the resized image, but
    the fuselage doesn't reach 40% of the illustration's own max row
    width until 169px down - the thin tail spike accounts for 161 of the
    387px-tall image before anything "solid-looking" appears. Anchoring
    to `.content[1]` (correct for bounding-box purposes, e.g.
    `_assert_within_canvas()`) is exactly why the text block ends up
    visually stranded near the top labels: it's 40px from a real pixel,
    just one that reads as empty air to a human looking at the panel.

    Re-selects and re-resizes the same illustration file
    `_build_active_canvas()` already chose (same functions, same
    parameters) purely to read its alpha-channel row-width profile -
    doesn't change which file is drawn or how, only where the text block
    reads this one number from.
    """
    main_path = illustrations.select_illustration(route, aircraft_type)
    inner_width = render.WIDTH * (1 - 2 * render.FRAME_INSET_FRAC)
    main_w = round(inner_width * render.MAIN_ILLUSTRATION_WIDTH_FRAC)
    resized = render._load_illustration_safely(main_path, main_w)
    if resized is None or resized.mode != "RGBA":
        return main_placement.content[1]  # fallback: no illustration loaded, behave as before
    alpha = resized.split()[-1]
    w, h = resized.size
    row_widths = [sum(1 for p in alpha.crop((0, y, w, y + 1)).getdata() if p > 20) for y in range(h)]
    max_w = max(row_widths) if row_widths else 0
    if max_w == 0:
        return main_placement.content[1]
    threshold = FUSELAGE_WIDTH_THRESHOLD * max_w
    offset_y = next((y for y, rw in enumerate(row_widths) if rw >= threshold), 0)
    return main_placement.rect[1] + offset_y


def patched_draw_main_text_block(canvas, flight, state, route, main_placement, ink_idx, bg_idx, weight):
    draw = ImageDraw.Draw(canvas)
    # Round 9 (developer): align the text block's left edge to the
    # aircraft's own nose, not the canvas margin - main_placement.content[0]
    # is the illustration's leftmost OPAQUE pixel column, i.e. the nose
    # tip itself, the same ".content" (not ".rect") bbox every other
    # measurement in this pipeline already trusts for "where the aircraft
    # actually is" (unlike the vertical top edge, a side-view nose is a
    # filled, rounded shape, not a thin spike, so this is a safe reuse -
    # no separate width-profile analysis needed here).
    left_x = main_placement.content[0]

    # The real content ladder, called verbatim - same functions, same
    # data, same never-shows-the-raw-callsign guarantee production uses.
    line1_full = render._flight_line1_text(flight, state, route)
    line2_full = render._flight_line2_text(route, flight.get("aircraft_type"))

    identifier_raw = (route or {}).get("callsign_iata") if isinstance(route, dict) else None
    identifier = identifier_raw.strip() if isinstance(identifier_raw, str) and identifier_raw.strip() else None

    # Decide the visual split from the real output alone - never a
    # separate re-derivation of which tier applies.
    if line1_full == "":
        # Tier 3 (D-10): line 1 omitted, line 2 promoted - no number, no
        # tracked route line, just the (promoted) airline+type line.
        number_text = None
        tracked_text = None
        plain_text = line2_full
    elif identifier and line1_full.startswith(identifier + " "):
        # Tier 1: "{identifier} to|from {city}" - split at the identifier
        # so it can be styled as the big number; the remainder becomes
        # the tracked route line, exactly as the real string already
        # reads, just upper-cased for the tracked-caps treatment.
        number_text = identifier
        tracked_text = line1_full[len(identifier) + 1:].upper()
        plain_text = line2_full
    else:
        # Tier 2 ("{To|From} {city}") or tier 4 ("Unknown flight") - no
        # identifier to split out, the whole real string becomes the
        # tracked line with no separate number.
        number_text = None
        tracked_text = line1_full.upper()
        plain_text = line2_full

    num_font = render._role_font(FLIGHT_NUMBER_FONT, weight)
    route_font = render._role_font(ROUTE_LINE_FONT, weight)
    airline_font = render._role_font(AIRLINE_LINE_FONT, weight)

    # Round 11 (developer's correction): back below the illustration once
    # more. Splitting the top-right tag down to "RWY 3" alone (see
    # patched_draw_top_labels) frees enough room that BAND_SHIFT_FRAC=0.0
    # clears both the shorter tag AND this below-position, nose-aligned
    # block at once (verified numerically before switching back - see
    # that constant's own comment for the exact margins) - round 9/10's
    # conflict doesn't reopen this time. Real production anchor again:
    # MAIN_TEXT_GAP_PX below the illustration's opaque bottom edge.
    y = main_placement.content[3] + render.MAIN_TEXT_GAP_PX
    first_bbox = None

    if number_text:
        num_bbox = draw.textbbox((left_x, y), number_text, font=num_font, anchor="la")
        draw.text((left_x, y), number_text, font=num_font, fill=ink_idx, anchor="la")
        first_bbox = num_bbox
        dash_y = num_bbox[3] + DASH_GAP
        draw.line([(left_x, dash_y), (left_x + DASH_W, dash_y)], fill=ink_idx, width=2)
        y = dash_y + DASH_GAP + 4

    if tracked_text:
        render.draw_tracked_text(draw, (left_x, y), tracked_text, route_font, ink_idx, render.LABEL_TRACKING_PX)
        tracked_bbox = render._tracked_text_bbox(route_font, (left_x, y), tracked_text, render.LABEL_TRACKING_PX)
        if first_bbox is None:
            first_bbox = tracked_bbox
        y = tracked_bbox[3] + 12

    plain_bbox = draw.textbbox((left_x, y), plain_text, font=airline_font, anchor="la")
    draw.text((left_x, y), plain_text, font=airline_font, fill=ink_idx, anchor="la")
    if first_bbox is None:
        first_bbox = plain_bbox

    return first_bbox, plain_bbox


# --- Previous (secondary) card: same three-level hierarchy (number / dash
# + tracked route / airline+type), right-aligned to match its existing
# convention, scaled down to roughly the card's own long-established 57%
# scale vs. the main card (992 x 0.57 = 565px, D-25/D-26's own ratio).
# Position stays BELOW the previous illustration, unchanged from
# production (PREVIOUS_TEXT_GAP_PX/PREVIOUS_TEXT_LEFT_OFFSET_PX) - unlike
# the main card, the band never reaches this far right at this card's
# height (checked: band's rightmost extent here is ~45% width, this
# card's text sits at ~89% width), so there's no collision to dodge and
# no reason to also flip it above its aircraft.
PREV_NUMBER_FONT = (render.PT_SERIF_BOLD, 32, 700)
PREV_ROUTE_FONT = (render.PT_SERIF_REGULAR, 16, 400)
PREV_AIRLINE_FONT = (render.PT_SERIF_REGULAR, 14, 400)
PREV_DASH_W = 16
PREV_DASH_GAP = 6


def patched_draw_previous_text_block(canvas, flight, state, route, prev_placement, ink_idx, bg_idx, weight):
    draw = ImageDraw.Draw(canvas)
    right_x = prev_placement.content[2] - render.PREVIOUS_TEXT_LEFT_OFFSET_PX

    line1_full = render._flight_line1_text(flight, state, route)
    line2_full = render._flight_line2_text(route, (flight or {}).get("aircraft_type"))

    identifier_raw = (route or {}).get("callsign_iata") if isinstance(route, dict) else None
    identifier = identifier_raw.strip() if isinstance(identifier_raw, str) and identifier_raw.strip() else None

    if line1_full == "":
        number_text, tracked_text, plain_text = None, None, line2_full
    elif identifier and line1_full.startswith(identifier + " "):
        number_text = identifier
        tracked_text = line1_full[len(identifier) + 1:].upper()
        plain_text = line2_full
    else:
        number_text, tracked_text, plain_text = None, line1_full.upper(), line2_full

    num_font = render._role_font(PREV_NUMBER_FONT, weight)
    route_font = render._role_font(PREV_ROUTE_FONT, weight)
    airline_font = render._role_font(PREV_AIRLINE_FONT, weight)

    y = prev_placement.content[3] + render.PREVIOUS_TEXT_GAP_PX
    first_bbox = None

    if number_text:
        num_bbox = draw.textbbox((right_x, y), number_text, font=num_font, anchor="ra")
        draw.text((right_x, y), number_text, font=num_font, fill=ink_idx, anchor="ra")
        first_bbox = num_bbox
        dash_y = num_bbox[3] + PREV_DASH_GAP
        draw.line([(right_x - PREV_DASH_W, dash_y), (right_x, dash_y)], fill=ink_idx, width=2)
        y = dash_y + PREV_DASH_GAP + 3

    if tracked_text:
        tracked_w = render._tracked_text_width(route_font, tracked_text, render.LABEL_TRACKING_PX)
        tracked_x = right_x - tracked_w
        render.draw_tracked_text(draw, (tracked_x, y), tracked_text, route_font, ink_idx, render.LABEL_TRACKING_PX)
        tracked_bbox = render._tracked_text_bbox(route_font, (tracked_x, y), tracked_text, render.LABEL_TRACKING_PX)
        if first_bbox is None:
            first_bbox = tracked_bbox
        y = tracked_bbox[3] + 8

    plain_bbox = draw.textbbox((right_x, y), plain_text, font=airline_font, anchor="ra")
    draw.text((right_x, y), plain_text, font=airline_font, fill=ink_idx, anchor="ra")
    if first_bbox is None:
        first_bbox = plain_bbox

    return first_bbox, plain_bbox


def main():
    orig_draw_main_text_block = render.draw_main_text_block
    orig_draw_previous_text_block = render.draw_previous_text_block
    orig_draw_top_labels = render.draw_top_labels
    candidates = [
        ("ref-band-blue-dithered", pf.IDX_BLUE, True),
        ("ref-band-blue-flat", pf.IDX_BLUE, False),
        ("ref-band-green-dithered", pf.IDX_GREEN, True),
        ("ref-band-red-flat", pf.IDX_RED, False),
        ("ref-band-black-flat", pf.IDX_BLACK, False),
    ]
    try:
        render.draw_main_text_block = patched_draw_main_text_block
        render.draw_previous_text_block = patched_draw_previous_text_block
        render.draw_top_labels = patched_draw_top_labels
        for label, band_idx, dithered in candidates:
            pf.new_canvas = make_patched_new_canvas(band_idx, dithered)
            canvas = render.build_canvas(
                TEST_FLIGHT, "departing", route=TEST_ROUTE,
                previous_flight=TEST_FLIGHT, previous_route=TEST_PREV_ROUTE, previous_state="arriving",
                theme_id="white",
            )
            out_path = os.path.join(OUT_DIR, "%s-full-composition.png" % label)
            canvas.convert("RGB").save(out_path)
            legal_ok = True
            try:
                render._assert_legal_palette(canvas, pf.IDX_WHITE)
            except AssertionError as e:
                legal_ok = False
                print("PALETTE VIOLATION on %s: %s" % (label, e))
            print("wrote %s | legal=%s" % (out_path, legal_ok))
    finally:
        render.draw_main_text_block = orig_draw_main_text_block
        render.draw_previous_text_block = orig_draw_previous_text_block
        render.draw_top_labels = orig_draw_top_labels
        pf.new_canvas = _TRUE_ORIG_NEW_CANVAS


if __name__ == "__main__":
    main()
