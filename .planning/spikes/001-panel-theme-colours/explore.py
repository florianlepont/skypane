#!/usr/bin/env python3
"""Throwaway visual-comparison script for spike 001 (panel background
colours + text-legibility technique). Does NOT modify any real project
file: it imports the real render pipeline (fonts, palette, layout, dither)
and monkeypatches only in-process, so every render below is pixel-faithful
to what server/plane/render.py would actually produce, minus the two axes
under test:

  1. background colour (theme_id) - registers a throwaway "white" theme
     in device_config.THEMES for the duration of this process only.
  2. text-legibility technique - swaps render._paint_text_backing() and
     ImageDraw.ImageDraw.text() for the run of one render, then restores
     the originals, so different renders can use different techniques
     without leaking into each other.

Run from repo root: `source server/.venv/bin/activate && python
.planning/spikes/001-panel-theme-colours/explore.py`
"""
import contextlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PIL import ImageDraw  # noqa: E402

from server import device_config, panel_format  # noqa: E402
from server.plane import render  # noqa: E402

OUT_DIR = os.path.join(_HERE, "renders")
os.makedirs(OUT_DIR, exist_ok=True)

# --- 1. Register throwaway background-colour candidates -------------------
# Real THEMES entries only ever reference panel_format.IDX_* - matching that
# discipline here even though this dict is never persisted.
device_config.THEMES["white"] = {
    "departing_index": panel_format.IDX_WHITE,
    "arriving_index": panel_format.IDX_WHITE,
    "ink_index": panel_format.IDX_BLACK,
    "label": "White (candidate default)",
}
device_config.THEME_IDS = tuple(device_config.THEMES)

# --- 2. Legibility-technique monkeypatches --------------------------------
_ORIG_PAINT_BACKING = render._paint_text_backing
_ORIG_TEXT = ImageDraw.ImageDraw.text


def _no_backing(draw, bbox, bg_idx, pad=4):
    pass  # paint nothing - relies on ink contrast (or the wrapped .text below) alone


def _outline_text_factory(stroke_idx, width=3):
    def _patched(self, xy, text, fill=None, font=None, anchor=None, *a, **kw):
        kw.pop("stroke_width", None)
        kw.pop("stroke_fill", None)
        return _ORIG_TEXT(
            self, xy, text, fill=fill, font=font, anchor=anchor,
            stroke_width=width, stroke_fill=stroke_idx, *a, **kw)
    return _patched


def _shadow_text_factory(shadow_idx, dx=3, dy=3):
    def _patched(self, xy, text, fill=None, font=None, anchor=None, *a, **kw):
        x, y = xy
        _ORIG_TEXT(self, (x + dx, y + dy), text, fill=shadow_idx, font=font, anchor=anchor, *a, **kw)
        return _ORIG_TEXT(self, xy, text, fill=fill, font=font, anchor=anchor, *a, **kw)
    return _patched


# --- 2b. Font-weight/family monkeypatch -----------------------------------
# Project history (server/assets/fonts/VENDOR.md) is directly relevant here:
# Zilla Slab Bold/SemiBold was the ORIGINAL Phase 3 choice, picked
# specifically because thick slab-serif strokes resist e-ink
# hairline-legibility loss - then replaced by PT Serif Regular (thin
# strokes) purely because the developer preferred its look, "after being
# shown the risk" (D-27). VENDOR.md's own documented fallback, if PT Serif
# Regular ever proves illegible, is PTSerif-Bold.ttf - already vendored,
# never wired into any active role. Zilla Slab's TTFs are also still
# vendored (inactive). All render._font() lookups route through PT_SERIF_
# REGULAR (state label, top tag, main/previous line 1+2); patching just
# that one path substitution covers every role used by build_canvas() for
# the departing/arriving states tested below.
_ORIG_FONT = render._font
ZILLA_SEMIBOLD = os.path.join(render.FONT_DIR, "ZillaSlab-SemiBold.ttf")
ZILLA_BOLD = os.path.join(render.FONT_DIR, "ZillaSlab-Bold.ttf")


def _font_substitute_factory(new_path):
    def _patched(spec):
        path, size, weight = spec
        if path == render.PT_SERIF_REGULAR:
            spec = (new_path, size, weight)
        return _ORIG_FONT(spec)
    return _patched


@contextlib.contextmanager
def font_variant(new_path):
    """Redirect every PT_SERIF_REGULAR lookup to `new_path` for one render.
    `new_path=None` is a no-op (real PT Serif Regular, unchanged).
    """
    if new_path is None:
        yield
        return
    render._font = _font_substitute_factory(new_path)
    try:
        yield
    finally:
        render._font = _ORIG_FONT


@contextlib.contextmanager
def legibility_variant(name, ink_stroke_idx=panel_format.IDX_BLACK):
    """Patch render._paint_text_backing + ImageDraw.text for one render,
    then restore both unconditionally. `name` in {"plate", "none",
    "outline", "shadow"}.
    """
    if name == "plate":
        yield  # real, unmodified behaviour - the current shipped technique
        return
    if name == "none":
        render._paint_text_backing = _no_backing
    elif name == "outline":
        render._paint_text_backing = _no_backing
        ImageDraw.ImageDraw.text = _outline_text_factory(ink_stroke_idx)
    elif name == "shadow":
        render._paint_text_backing = _no_backing
        ImageDraw.ImageDraw.text = _shadow_text_factory(ink_stroke_idx)
    else:
        raise ValueError(name)
    try:
        yield
    finally:
        render._paint_text_backing = _ORIG_PAINT_BACKING
        ImageDraw.ImageDraw.text = _ORIG_TEXT


# --- 3. Realistic sample content (mirrors render.py's own CLI preview) ----
FLIGHT = {"hex": "39a1b2", "callsign": "AFR1234"}
ROUTE = dict(render._PREVIEW_ROUTE)
PREV_FLIGHT = {"hex": "39c3d4", "callsign": "VLG5678"}
PREV_ROUTE = dict(render._PREVIEW_PREVIOUS_ROUTE)


def render_variant(theme_id, state, legibility, out_name, stroke_idx=panel_format.IDX_BLACK, font_path=None):
    previous_state = "arriving" if state == "departing" else "departing"
    with font_variant(font_path), legibility_variant(legibility, ink_stroke_idx=stroke_idx):
        canvas = render.build_canvas(
            FLIGHT, state, route=ROUTE,
            previous_flight=PREV_FLIGHT, previous_route=PREV_ROUTE, previous_state=previous_state,
            theme_id=theme_id,
        )
    path = os.path.join(OUT_DIR, out_name)
    canvas.convert("RGB").save(path)
    print("wrote", path)
    return path


def main():
    written = []

    # White candidate default - baseline technique (no coloured field to
    # fight, so no legibility trick is expected to matter, but render it
    # both ways to confirm).
    written.append(render_variant("white", "departing", "plate", "01-white-departing-plate.png"))
    written.append(render_variant("white", "arriving", "plate", "02-white-arriving-plate.png"))

    # Existing sky theme (Blue/Green), current shipped technique (solid
    # backing plate) - the baseline every other variant below is judged
    # against.
    written.append(render_variant("sky", "departing", "plate", "10-sky-departing-plate-BASELINE.png"))
    written.append(render_variant("sky", "arriving", "plate", "11-sky-arriving-plate-BASELINE.png"))

    # Sky theme with the backing plate simply removed (no replacement) -
    # shows why Phase 7 added it in the first place (dithered speckle
    # behind white text).
    written.append(render_variant("sky", "departing", "none", "20-sky-departing-none.png"))
    written.append(render_variant("sky", "arriving", "none", "21-sky-arriving-none.png"))

    # Sky theme, text outline/stroke instead of a solid box (black stroke
    # around white ink). Stroke width 3 is the default legibility_variant()
    # picks; also try 1 and 2 to see whether a thinner stroke stays clean
    # at the smallest caption size (PREVIOUS_LINE2_FONT, 16px) instead of
    # clumping into a blotch.
    written.append(render_variant("sky", "departing", "outline", "30-sky-departing-outline-w3.png"))
    written.append(render_variant("sky", "arriving", "outline", "31-sky-arriving-outline-w3.png"))

    def render_outline_width(width, state, out_name):
        previous_state = "arriving" if state == "departing" else "departing"
        render._paint_text_backing = _no_backing
        ImageDraw.ImageDraw.text = _outline_text_factory(panel_format.IDX_BLACK, width=width)
        try:
            canvas = render.build_canvas(
                FLIGHT, state, route=ROUTE,
                previous_flight=PREV_FLIGHT, previous_route=PREV_ROUTE, previous_state=previous_state,
                theme_id="sky",
            )
        finally:
            render._paint_text_backing = _ORIG_PAINT_BACKING
            ImageDraw.ImageDraw.text = _ORIG_TEXT
        path = os.path.join(OUT_DIR, out_name)
        canvas.convert("RGB").save(path)
        print("wrote", path)
        return path

    written.append(render_outline_width(1, "departing", "32-sky-departing-outline-w1.png"))
    written.append(render_outline_width(2, "departing", "33-sky-departing-outline-w2.png"))

    # Sky theme, drop-shadow instead of a solid box (offset black copy
    # behind white ink).
    written.append(render_variant("sky", "departing", "shadow", "40-sky-departing-shadow.png"))
    written.append(render_variant("sky", "arriving", "shadow", "41-sky-arriving-shadow.png"))

    # --- Font-weight axis: no backing plate, no outline/shadow trick at
    # all - just a heavier-stroke font doing the legibility work by
    # itself, the way Zilla Slab was originally chosen to do (VENDOR.md).
    written.append(render_variant(
        "sky", "departing", "none", "50-sky-departing-none-PTBOLD.png",
        font_path=render.PT_SERIF_BOLD))
    written.append(render_variant(
        "sky", "arriving", "none", "51-sky-arriving-none-PTBOLD.png",
        font_path=render.PT_SERIF_BOLD))
    written.append(render_variant(
        "sky", "departing", "none", "60-sky-departing-none-ZILLA-SEMIBOLD.png",
        font_path=ZILLA_SEMIBOLD))
    written.append(render_variant(
        "sky", "arriving", "none", "61-sky-arriving-none-ZILLA-SEMIBOLD.png",
        font_path=ZILLA_SEMIBOLD))
    written.append(render_variant(
        "sky", "departing", "none", "62-sky-departing-none-ZILLA-BOLD.png",
        font_path=ZILLA_BOLD))
    written.append(render_variant(
        "sky", "arriving", "none", "63-sky-arriving-none-ZILLA-BOLD.png",
        font_path=ZILLA_BOLD))

    print("\n%d renders written to %s" % (len(written), OUT_DIR))
    return written


if __name__ == "__main__":
    main()
