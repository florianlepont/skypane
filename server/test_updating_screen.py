#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
"""Contract tests for the UPDATING hold screen's server-side composition
(`server/plane/render/hold_screens.py`'s `_build_updating_canvas()` and
`glyphs.py`'s `draw_updating_icon()`) - the source of truth
`firmware/tools/gen_fault_screen.py --screen updating` bakes into
`firmware/main/updating_screen_mask.h` (see server/test_updating_screen_mask.py
for the byte-for-byte drift proof).

Runs under server/.venv's interpreter - render transitively imports Pillow.
Mirrors server/test_render.py's NO CONNECTION tests (same
`_build_hold_canvas()` family, same flat/dithered contract), scoped to the
one new screen this file owns.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.panel_format as panel_format  # noqa: E402
import server.plane.render as render  # noqa: E402
from PIL import ImageDraw  # noqa: E402

pytestmark = pytest.mark.slow

IDX_BLACK, IDX_WHITE = 0, 1


def test_updating_copy_constants_match_locked_strings():
    """UPDATING_HEADING_TEXT == 'UPDATING' and UPDATING_BODY_LINES == the two locked authored sentences, asserted by exact equality"""
    if render.UPDATING_HEADING_TEXT != "UPDATING":
        pytest.fail("UPDATING_HEADING_TEXT is %r, expected 'UPDATING'" % (render.UPDATING_HEADING_TEXT,))
    expected_lines = ("Installing a firmware update.", "The frame will restart when it's ready.")
    if render.UPDATING_BODY_LINES != expected_lines:
        pytest.fail("UPDATING_BODY_LINES is %r, expected %r" % (render.UPDATING_BODY_LINES, expected_lines))
    if render.UPDATING_BODY_TEXT != " ".join(expected_lines):
        pytest.fail("UPDATING_BODY_TEXT is %r, expected the joined body lines" % (render.UPDATING_BODY_TEXT,))


def test_updating_dispatches_through_shared_hold_composition():
    """render._build_updating_canvas() calls render._build_hold_canvas exactly once, with draw_updating_icon, UPDATING_ICON_DIAMETER_PX, UPDATING_HEADING_TEXT, UPDATING_BODY_LINES, DIMMED_FIELD_IDX, DIMMED_INK and dithered=True by default - the same shared composition family NO CONNECTION uses"""
    orig = render.hold_screens._build_hold_canvas
    calls = []

    def _spy(*args, **kwargs):
        calls.append((args, kwargs))
        return orig(*args, **kwargs)

    render.hold_screens._build_hold_canvas = _spy
    try:
        render._build_updating_canvas()
    finally:
        render.hold_screens._build_hold_canvas = orig
    if len(calls) != 1:
        pytest.fail("_build_hold_canvas was called %d time(s), expected exactly 1" % (len(calls),))
    args, kwargs = calls[0]
    if len(args) < 7:
        pytest.fail("_build_hold_canvas call had %d positional args, expected at least 7 "
            "(glyph_draw, glyph_height, label_text, sentences, field_idx, ink, dithered)" % (len(args),))
    glyph_draw, glyph_height, label_text, sentences, field_idx, ink, dithered = args[0:7]
    if glyph_draw is not render.draw_updating_icon:
        pytest.fail("glyph_draw was %r, expected render.draw_updating_icon" % (glyph_draw,))
    if glyph_height != render.UPDATING_ICON_DIAMETER_PX:
        pytest.fail("glyph_height was %r, expected UPDATING_ICON_DIAMETER_PX (%r)"
            % (glyph_height, render.UPDATING_ICON_DIAMETER_PX))
    if label_text != render.UPDATING_HEADING_TEXT:
        pytest.fail("label_text was %r, expected UPDATING_HEADING_TEXT" % (label_text,))
    if sentences != render.UPDATING_BODY_LINES:
        pytest.fail("sentences was %r, expected UPDATING_BODY_LINES" % (sentences,))
    if field_idx != render.DIMMED_FIELD_IDX:
        pytest.fail("field_idx was %r, expected DIMMED_FIELD_IDX" % (field_idx,))
    if ink != render.DIMMED_INK:
        pytest.fail("ink was %r, expected DIMMED_INK" % (ink,))
    if dithered is not True:
        pytest.fail("dithered was %r, expected True for the default (flat=False) call" % (dithered,))


def test_updating_dithered_legal_palette_and_black_dominant():
    """_build_updating_canvas() (dithered) uses only IDX_BLACK/IDX_WHITE, dominated by DIMMED_FIELD_IDX (Black)"""
    canvas = render._build_updating_canvas()
    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    bad = idx_set - {IDX_WHITE, IDX_BLACK}
    if bad:
        pytest.fail("updating canvas contains index(es) other than White/Black: %r" % (sorted(bad),))
    if IDX_WHITE not in idx_set:
        pytest.fail("updating canvas has no White pixels")
    if IDX_BLACK not in idx_set:
        pytest.fail("updating canvas has no Black pixels")
    counts = {value: count for count, value in colors}
    if max(counts, key=counts.get) != render.DIMMED_FIELD_IDX:
        pytest.fail("updating canvas is not dominated by its own field index %r" % (render.DIMMED_FIELD_IDX,))


def test_updating_flat_canvas_is_1200x1600_and_contains_only_black_and_white():
    """_build_updating_canvas(flat=True) returns a 1200x1600 image containing only {IDX_BLACK, IDX_WHITE} - no dither noise, since it exists purely for gen_fault_screen.py's ink-mask extraction"""
    canvas = render._build_updating_canvas(flat=True)
    if canvas.size != (1200, 1600):
        pytest.fail("flat updating canvas size is %r, expected (1200, 1600)" % (canvas.size,))
    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    bad = idx_set - {IDX_WHITE, IDX_BLACK}
    if bad:
        pytest.fail("flat updating canvas contains index(es) other than White/Black: %r" % (sorted(bad),))


def test_updating_ink_bbox_is_centred_and_differs_from_no_connection():
    """The UPDATING flat canvas's ink bounding box is horizontally centred within 2px, and its bytes differ from the NO CONNECTION flat canvas (different glyph and text)"""
    updating = render._build_updating_canvas(flat=True)
    no_connection = render._build_no_connection_canvas(flat=True)

    lut = [0] * 256
    lut[IDX_WHITE] = 255
    bbox = updating.point(lut, mode="L").convert("1").getbbox()
    if bbox is None:
        pytest.fail("updating flat canvas has no White (ink) pixels")
    left, _top, right, _bottom = bbox
    center_x = (left + right) / 2
    canvas_center_x = updating.size[0] / 2
    if abs(center_x - canvas_center_x) > 2:
        pytest.fail("updating ink bounding box center_x=%r is not within 2px of the canvas center %r"
            % (center_x, canvas_center_x))

    if updating.tobytes() == no_connection.tobytes():
        pytest.fail("updating flat canvas is byte-identical to the no-connection flat canvas - "
            "expected a different glyph and text")


def test_draw_updating_icon_height_and_stroke_budget():
    """draw_updating_icon() returns a height of at most POWER_ICON_BAR_RISE_PX + POWER_ICON_DIAMETER_PX (86px, the largest existing hold-glyph sibling's total footprint), UPDATING_ICON_STROKE_PX == POWER_ICON_STROKE_PX, draws only ink_idx, and leaves visible ink on the canvas"""
    canvas = panel_format.new_canvas(IDX_BLACK)
    draw = ImageDraw.Draw(canvas)
    top_y = 200
    center_x = 600
    returned = render.draw_updating_icon(draw, center_x, top_y, IDX_WHITE)

    max_height = render.POWER_ICON_BAR_RISE_PX + render.POWER_ICON_DIAMETER_PX
    if returned > max_height:
        pytest.fail("draw_updating_icon returned height %r, expected at most %r" % (returned, max_height))
    if render.UPDATING_ICON_STROKE_PX != render.POWER_ICON_STROKE_PX:
        pytest.fail("UPDATING_ICON_STROKE_PX is %r, expected POWER_ICON_STROKE_PX (%r)"
            % (render.UPDATING_ICON_STROKE_PX, render.POWER_ICON_STROKE_PX))

    colors = canvas.getcolors()
    idx_set = {value for _count, value in colors} if colors else set()
    stray = idx_set - {IDX_BLACK, IDX_WHITE}
    if stray:
        pytest.fail("canvas contains index(es) other than the field/ink pair: %r" % (sorted(stray),))
    if canvas.getbbox() is None:
        pytest.fail("draw_updating_icon drew nothing (getbbox() is None)")


def test_build_canvas_never_produces_the_updating_canvas():
    """build_canvas() never returns the same bytes as _build_updating_canvas() for any state it accepts - that screen is drawn only by the firmware, never dispatched by the server"""
    updating_bytes = render._build_updating_canvas().tobytes()
    cases = [
        (None, "battery_empty", {}),
        (None, "display_off", {}),
        (None, "quiet_hours", {"quiet_hours_until": "07:00"}),
        (None, "empty", {}),
    ]
    for flight, state, kwargs in cases:
        canvas = render.build_canvas(flight, state, **kwargs)
        if canvas.tobytes() == updating_bytes:
            pytest.fail("build_canvas(%r, %r) matched the updating canvas - this screen must never be "
                "server-dispatched" % (flight, state))
