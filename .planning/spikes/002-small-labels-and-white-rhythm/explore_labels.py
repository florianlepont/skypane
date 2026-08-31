#!/usr/bin/env python3
"""Spike 002a: letter-spacing (tracking) treatment for the panel's two
smallest fixed-size text roles - STATE_LABEL_FONT (top-left, 20px) and
TOP_TAG_FONT (top-right, 18px).

Both label strings are ALREADY fully uppercase ("DEPARTING"/"ARRIVING",
"ORY · RWY 3") - there is no lowercase to shrink, so a literal OpenType
small-caps simulation doesn't apply here. What the developer described
("petites capitales avec un peu d'espacement, comme un cartel de musée")
is achievable as tracked (letter-spaced) all-caps text instead, which is
exactly what this spike tests.

Prior art found in git history (commit 73a6eb2^, superseded when the
panel moved to the two-flight poster layout, D-21/D-24/D-25/D-26 -
removed because that redesign changed the zone, not because it failed):
draw_tracked_text()/_tracked_text_width(), Phase 2/3's LABEL_TRACKING_PX
(4px -> 6px, D-15). Never verified on real Spectra 6 glass in that phase
- hardware/BRINGUP-LOG.md has no mention of it. Resurrected and adapted
here, monkeypatching render.draw_top_labels() for the duration of each
render so every other element (illustration, main text, previous card)
comes from the real, current production pipeline unchanged.

Never edits server/plane/render.py - throwaway exploration only.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "server", ".."))

from server.plane import render
from server import device_config
from PIL import ImageDraw

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


def _tracked_text_width(font, text, tracking):
    if not text:
        return 0.0
    return sum(font.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def _draw_tracked_text(draw, xy, text, font, fill, tracking=0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill, anchor="la")
        x += font.getlength(ch) + tracking
    return x


def make_tracked_draw_top_labels(tracking_px, size_delta=0):
    """Returns a draw_top_labels() replacement that draws both top labels
    tracked by `tracking_px` extra pixels between glyphs, at the role's
    normal size + `size_delta` (negative = smaller, for the "smaller but
    tracked" variant).
    """
    def _tracked_draw_top_labels(canvas, state, ink_idx, bg_idx, weight, runway_id=device_config.DEFAULT_RUNWAY_ID):
        draw = ImageDraw.Draw(canvas)
        label_path, label_size, label_w = render.STATE_LABEL_FONT
        tag_path, tag_size, tag_w = render.TOP_TAG_FONT
        label_font = render._role_font((label_path, label_size + size_delta, label_w), weight)
        tag_font = render._role_font((tag_path, tag_size + size_delta, tag_w), weight)
        tag_text = render.runway_tag_text(runway_id)
        label_text = render.STATE_LABEL_TEXT[state]

        # Left-anchored label: draw directly at MARGIN.
        _draw_tracked_text(draw, (render.MARGIN, render.MARGIN), label_text, label_font, ink_idx, tracking_px)

        # Right-anchored tag: pre-compute tracked width, offset left by it.
        tag_w_px = _tracked_text_width(tag_font, tag_text, tracking_px)
        tag_x = render.WIDTH - render.MARGIN - tag_w_px
        _draw_tracked_text(draw, (tag_x, render.MARGIN), tag_text, tag_font, ink_idx, tracking_px)

        # Sanity check (not a hard assert - exploratory script): both must
        # stay inside the canvas.
        if tag_x < 0:
            print("  WARNING: tag_x=%.1f is negative - tag text overflows the left edge at tracking=%dpx, size_delta=%d" % (tag_x, tracking_px, size_delta))

    return _tracked_draw_top_labels


VARIANTS = [
    ("baseline-0px", 0, 0),
    ("tracked-2px", 2, 0),
    ("tracked-4px", 4, 0),
    ("tracked-6px", 6, 0),
    ("smaller-tracked-6px", 6, -2),
]

THEMES_TO_TEST = ["white", "grey"]  # white (flat) + grey (dithered) per spike methodology


def main():
    orig_draw_top_labels = render.draw_top_labels
    try:
        for variant_name, tracking_px, size_delta in VARIANTS:
            for theme_id in THEMES_TO_TEST:
                render.draw_top_labels = make_tracked_draw_top_labels(tracking_px, size_delta)
                for state, previous_state in (("departing", "arriving"), ("arriving", "departing")):
                    canvas = render.build_canvas(
                        TEST_FLIGHT, state, route=TEST_ROUTE,
                        previous_flight=TEST_FLIGHT, previous_route=TEST_ROUTE, previous_state=previous_state,
                        theme_id=theme_id,
                    )
                    out_path = os.path.join(OUT_DIR, "%s-%s-%s-full.png" % (variant_name, theme_id, state))
                    canvas.convert("RGB").save(out_path)
                    print("wrote", out_path)

                    # Zoomed 3x crop of just the top band (state label + tag),
                    # matching spike 001's compare2_top_tag.png methodology.
                    crop_box = (0, 0, render.WIDTH, render.MARGIN * 3)
                    crop = canvas.crop(crop_box).convert("RGB")
                    crop = crop.resize((crop.width * 3, crop.height * 3))
                    crop_path = os.path.join(OUT_DIR, "%s-%s-%s-crop3x.png" % (variant_name, theme_id, state))
                    crop.save(crop_path)
                    print("wrote", crop_path)
    finally:
        render.draw_top_labels = orig_draw_top_labels


if __name__ == "__main__":
    main()
