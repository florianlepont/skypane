#!/usr/bin/env python3
"""Render all four content-ladder tiers on the blue-light (dithered) band
candidate, so the developer can check each fallback level individually
at full resolution."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "server", ".."))
sys.path.insert(0, os.path.dirname(__file__))

import explore_full_composition as comp
from server.plane import render, enrich
from server import panel_format as pf

OUT_DIR = os.path.join(os.path.dirname(__file__), "renders")

TIER1_ROUTE = comp.TEST_ROUTE  # identifier + city
TIER2_ROUTE = dict(comp.TEST_ROUTE, callsign_iata=None)  # city, no identifier
TIER3_ROUTE = enrich.airline_only_route(comp.TEST_ROUTE["airline_name"])  # airline only
TIER4_ROUTE = None  # nothing resolved

TIERS = [
    ("tier1-identifier-and-city", TIER1_ROUTE),
    ("tier2-city-only", TIER2_ROUTE),
    ("tier3-airline-only", TIER3_ROUTE),
    ("tier4-nothing-resolved", TIER4_ROUTE),
]


def main():
    orig_draw_main_text_block = render.draw_main_text_block
    try:
        render.draw_main_text_block = comp.patched_draw_main_text_block
        pf.new_canvas = comp.make_patched_new_canvas(pf.IDX_BLUE, True)
        for label, route in TIERS:
            canvas = render.build_canvas(
                comp.TEST_FLIGHT, "departing", route=route,
                previous_flight=comp.TEST_FLIGHT, previous_route=comp.TEST_PREV_ROUTE, previous_state="arriving",
                theme_id="white",
            )
            out_path = os.path.join(OUT_DIR, "blue-dithered-%s.png" % label)
            canvas.convert("RGB").save(out_path)
            try:
                render._assert_legal_palette(canvas, pf.IDX_WHITE)
                legal = True
            except AssertionError as e:
                legal = False
                print("PALETTE VIOLATION on %s: %s" % (label, e))
            print("wrote %s | legal=%s" % (out_path, legal))
    finally:
        render.draw_main_text_block = orig_draw_main_text_block
        pf.new_canvas = comp._TRUE_ORIG_NEW_CANVAS


if __name__ == "__main__":
    main()
