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

from server.plane import render
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
BAND_TOP_LEFT_FRAC = 0.5818
BAND_TOP_RIGHT_FRAC = 0.8523
BAND_BOT_LEFT_FRAC = 0.0742
BAND_BOT_RIGHT_FRAC = 0.4772


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


# --- Text hierarchy, left-anchored, reference-inspired ---
FLIGHT_NUMBER_FONT = (render.PT_SERIF_BOLD, 56, 700)
ROUTE_LINE_FONT = (render.PT_SERIF_BOLD, 22, 700)
AIRLINE_LINE_FONT = (render.PT_SERIF_REGULAR, 20, 400)  # italic not vendored - Regular placeholder
DASH_W = 24
DASH_GAP = 10


def patched_draw_main_text_block(canvas, flight, state, route, main_placement, ink_idx, bg_idx, weight):
    draw = ImageDraw.Draw(canvas)
    left_x = render.MARGIN
    top_y = main_placement.content[3] + render.MAIN_TEXT_GAP_PX

    identifier = (route or {}).get("callsign_iata") or ""
    origin = (route or {}).get("origin_city") or ""
    dest = (route or {}).get("destination_city") or ""
    route_pair = "%s — %s" % (origin.upper(), dest.upper()) if origin and dest else ""
    airline = render.display_airline_name((route or {}).get("airline_name") or "")

    # Flight number, big and bold, left-anchored.
    num_font = render._role_fit_text_size(FLIGHT_NUMBER_FONT, identifier, render.WIDTH - 2 * left_x, 28, weight)
    num_bbox = draw.textbbox((left_x, top_y), identifier, font=num_font, anchor="la")
    draw.text((left_x, top_y), identifier, font=num_font, fill=ink_idx, anchor="la")

    # Thin dash rule directly under the flight number.
    dash_y = num_bbox[3] + DASH_GAP
    draw.line([(left_x, dash_y), (left_x + DASH_W, dash_y)], fill=ink_idx, width=2)

    # Route line, tracked small-caps (reusing the shipped top-label technique).
    route_y = dash_y + DASH_GAP + 4
    route_font = render._role_font(ROUTE_LINE_FONT, weight)
    render.draw_tracked_text(draw, (left_x, route_y), route_pair, route_font, ink_idx, render.LABEL_TRACKING_PX)
    route_bbox = render._tracked_text_bbox(route_font, (left_x, route_y), route_pair, render.LABEL_TRACKING_PX)

    # Airline name (Regular placeholder - italic not vendored).
    airline_y = route_bbox[3] + 12
    airline_font = render._role_font(AIRLINE_LINE_FONT, weight)
    draw.text((left_x, airline_y), airline, font=airline_font, fill=ink_idx, anchor="la")
    airline_bbox = draw.textbbox((left_x, airline_y), airline, font=airline_font, anchor="la")

    return num_bbox, airline_bbox


def main():
    orig_draw_main_text_block = render.draw_main_text_block
    candidates = [
        ("ref-band-blue-dithered", pf.IDX_BLUE, True),
        ("ref-band-blue-flat", pf.IDX_BLUE, False),
        ("ref-band-green-dithered", pf.IDX_GREEN, True),
        ("ref-band-red-flat", pf.IDX_RED, False),
        ("ref-band-black-flat", pf.IDX_BLACK, False),
    ]
    try:
        render.draw_main_text_block = patched_draw_main_text_block
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
        pf.new_canvas = _TRUE_ORIG_NEW_CANVAS


if __name__ == "__main__":
    main()
