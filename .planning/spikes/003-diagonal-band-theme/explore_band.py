#!/usr/bin/env python3
"""Spike 003: a diagonal decorative band, drawn behind the aircraft
illustration, as a new theme candidate.

Developer's scoped-down request (starting from a travel-poster reference
image): drop the reference's textured cream background entirely (no new
background treatment beyond what Phase 8 already shipped), keep the
diagonal band as the one genuinely new graphic element, apply NO colour
treatment to the aircraft illustrations (unchanged vendored PNGs). Ships
as ONE new dedicated theme (existing 11 themes untouched), band drawn
BEHIND the illustration so the aircraft stays fully visible on top.

Real hardware constraint: only 6 fixed Spectra 6 inks. The band's colour
must be one of IDX_BLACK/WHITE/YELLOW/RED/BLUE/GREEN, flat or dithered
toward white - never an arbitrary RGB like the reference's muted grey-blue.

Approach: monkeypatch panel_format.new_canvas() so that whenever it's
called with bg_idx == IDX_WHITE (the base field this spike tests against),
it draws a diagonal band on top of the flat fill before returning -
render.build_canvas()'s real pipeline then draws labels/text/illustration
on top of that, unmodified. server/plane/render.py is never edited.

Also runs the REAL render._assert_legal_palette() against every candidate
(not a reimplementation) to catch a background-dominance violation before
it reaches the developer's eyes, and checks whether the band's rendered
extent overlaps the top-label zone (MARGIN..3*MARGIN band, same check
spike 002 used).
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


def _band_polygon(w, h, top_cx_frac, bot_cx_frac, width_frac):
    band_w = width_frac * w
    top_cx = top_cx_frac * w
    bot_cx = bot_cx_frac * w
    return [
        (top_cx - band_w / 2, 0), (top_cx + band_w / 2, 0),
        (bot_cx + band_w / 2, h), (bot_cx - band_w / 2, h),
    ]


def draw_diagonal_band(canvas, band_idx, top_cx_frac, bot_cx_frac, width_frac, dithered=False):
    w, h = canvas.size
    poly = _band_polygon(w, h, top_cx_frac, bot_cx_frac, width_frac)
    if dithered:
        band_fill = dither.dithered_state_background(band_idx)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        canvas.paste(band_fill, (0, 0), mask)
    else:
        ImageDraw.Draw(canvas).polygon(poly, fill=band_idx)
    return poly


# Captured once, at import time, before any candidate patches pf.new_canvas -
# every candidate's patched function wraps THIS, never whatever pf.new_canvas
# currently is. Deriving "orig" from the live pf.new_canvas inside the loop
# (the bug this comment replaces) chains each candidate's patch on top of the
# previous one's, so a later, differently-shaped band never fully occludes an
# earlier, wider one - a real bug in this script, not a rendering finding.
_TRUE_ORIG_NEW_CANVAS = pf.new_canvas


def make_patched_new_canvas(band_idx, top_cx_frac, bot_cx_frac, width_frac, dithered):
    def _patched(bg_index):
        canvas = _TRUE_ORIG_NEW_CANVAS(bg_index)
        if bg_index == pf.IDX_WHITE:
            draw_diagonal_band(canvas, band_idx, top_cx_frac, bot_cx_frac, width_frac, dithered)
        return canvas

    return _patched


# Candidates: (label, band_idx, dithered, top_cx_frac, bot_cx_frac, width_frac)
CANDIDATES = [
    ("blue-flat-shallow", pf.IDX_BLUE, False, 0.62, 0.28, 0.22),
    ("blue-dithered-shallow", pf.IDX_BLUE, True, 0.62, 0.28, 0.22),
    ("black-flat-shallow", pf.IDX_BLACK, False, 0.62, 0.28, 0.22),
    ("green-dithered-shallow", pf.IDX_GREEN, True, 0.62, 0.28, 0.22),
    ("blue-flat-narrow", pf.IDX_BLUE, False, 0.62, 0.28, 0.13),
    ("blue-flat-wide", pf.IDX_BLUE, False, 0.68, 0.18, 0.32),
    ("blue-flat-steep", pf.IDX_BLUE, False, 0.58, 0.42, 0.22),
]

MARGIN = render.MARGIN
TOP_ZONE = (0, MARGIN, render.WIDTH, MARGIN * 3)


def band_overlaps_top_zone(top_cx_frac, bot_cx_frac, width_frac):
    w, h = render.WIDTH, render.HEIGHT
    # y range within TOP_ZONE is [MARGIN, MARGIN*3]; approximate band x-range
    # there by linear interpolation between the top (y=0) and bottom (y=h) edges.
    frac_at_margin1 = MARGIN / h
    frac_at_margin3 = (MARGIN * 3) / h
    top_cx = top_cx_frac * w
    bot_cx = bot_cx_frac * w
    band_w = width_frac * w
    for frac in (frac_at_margin1, frac_at_margin3):
        cx_at = top_cx + (bot_cx - top_cx) * frac
        left = cx_at - band_w / 2
        right = cx_at + band_w / 2
        if right >= 0 and left <= w:
            # any horizontal overlap with canvas at this y within the top zone
            # is a genuine overlap with the label row's y-range
            return True
    return False


def main():
    results = []
    try:
        for label, band_idx, dithered, top_cx, bot_cx, width in CANDIDATES:
            pf.new_canvas = make_patched_new_canvas(band_idx, top_cx, bot_cx, width, dithered)
            for state, prev_state in (("departing", "arriving"),):
                canvas = render.build_canvas(
                    TEST_FLIGHT, state, route=TEST_ROUTE,
                    previous_flight=TEST_FLIGHT, previous_route=TEST_ROUTE, previous_state=prev_state,
                    theme_id="white",
                )
                out_path = os.path.join(OUT_DIR, "%s-%s.png" % (label, state))
                canvas.convert("RGB").save(out_path)

                # Real guard-rail check, not a reimplementation.
                legal_ok = True
                legal_err = None
                try:
                    render._assert_legal_palette(canvas, pf.IDX_WHITE)
                except AssertionError as e:
                    legal_ok = False
                    legal_err = str(e)

                overlaps_top = band_overlaps_top_zone(top_cx, bot_cx, width)

                results.append((label, out_path, legal_ok, legal_err, overlaps_top))
                print("wrote %s | legal_palette_ok=%s%s | overlaps_top_label_zone=%s" % (
                    out_path, legal_ok, ("" if legal_ok else " (%s)" % legal_err), overlaps_top))
    finally:
        pf.new_canvas = _TRUE_ORIG_NEW_CANVAS

    print("\n=== Summary ===")
    for label, path, legal_ok, legal_err, overlaps_top in results:
        status = "OK" if legal_ok else "PALETTE-DOMINANCE-VIOLATION"
        print("%-28s legal=%s overlaps_top_labels=%s" % (label, status, overlaps_top))


if __name__ == "__main__":
    main()
