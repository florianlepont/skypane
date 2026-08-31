#!/usr/bin/env python3
"""Follow-up throwaway script for spike 001: sweep every one of the 6 real
Spectra 6 palette colours as a FLAT (non-dithered) full-panel background,
using the already-validated legibility fix (PT Serif Bold, no backing
plate, no outline/shadow) from explore.py. Does not modify any repo file.

Flat, not dithered, is deliberate here: Phase 7's dithered-lighten fix
(server/plane/dither.py's dithered_state_background()) exists because the
FLAT Blue/Green fill looked too dark/saturated on real glass at full-panel
coverage. Showing the flat versions again is a real re-open of that
question, not a step backward - worth seeing since the whole rendering
approach (bold text, optionally-white default) has changed since that
finding, and Yellow/Red have never been tried as full-panel backgrounds
at all (previously confirmed on real glass only as small accent icons).

Run: source server/.venv/bin/activate && python
.planning/spikes/001-panel-theme-colours/explore_colours.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import device_config, panel_format  # noqa: E402
from server.plane import render, dither  # noqa: E402

OUT_DIR = os.path.join(_HERE, "renders", "colours")
os.makedirs(OUT_DIR, exist_ok=True)

# --- Validated legibility fix from explore.py (PT Serif Bold, no plate) ---
_ORIG_FONT = render._font


def _font_sub(spec):
    path, size, weight = spec
    if path == render.PT_SERIF_REGULAR:
        spec = (render.PT_SERIF_BOLD, size, weight)
    return _ORIG_FONT(spec)


render._font = _font_sub


def _no_backing(draw, bbox, bg_idx, pad=4):
    pass


render._paint_text_backing = _no_backing

# --- Flat (non-dithered) background, for this sweep only -------------------
_ORIG_DITHERED_BG = dither.dithered_state_background


def _flat_background(bg_idx, lighten_fraction=0.4):
    return panel_format.new_canvas(bg_idx)


# --- Register one throwaway single-colour theme per palette entry ---------
SWATCHES = [
    ("sw-black", panel_format.IDX_BLACK, panel_format.IDX_WHITE, "Black"),
    ("sw-white", panel_format.IDX_WHITE, panel_format.IDX_BLACK, "White"),
    ("sw-yellow", panel_format.IDX_YELLOW, panel_format.IDX_BLACK, "Yellow"),
    ("sw-red", panel_format.IDX_RED, panel_format.IDX_WHITE, "Red"),
    ("sw-blue", panel_format.IDX_BLUE, panel_format.IDX_WHITE, "Blue (current departing)"),
    ("sw-green", panel_format.IDX_GREEN, panel_format.IDX_WHITE, "Green (current arriving)"),
]
for theme_id, bg_idx, ink_idx, label in SWATCHES:
    device_config.THEMES[theme_id] = {
        "departing_index": bg_idx,
        "arriving_index": bg_idx,
        "ink_index": ink_idx,
        "label": label,
    }

FLIGHT = {"hex": "39a1b2", "callsign": "AFR1234"}
ROUTE = dict(render._PREVIEW_ROUTE)
PREV_FLIGHT = {"hex": "39c3d4", "callsign": "VLG5678"}
PREV_ROUTE = dict(render._PREVIEW_PREVIOUS_ROUTE)


def main():
    written = []
    dither.dithered_state_background = _flat_background
    try:
        for theme_id, bg_idx, ink_idx, label in SWATCHES:
            canvas = render.build_canvas(
                FLIGHT, "departing", route=ROUTE,
                previous_flight=PREV_FLIGHT, previous_route=PREV_ROUTE, previous_state="arriving",
                theme_id=theme_id,
            )
            out_name = "%s-flat-BOLD-noplate.png" % theme_id
            path = os.path.join(OUT_DIR, out_name)
            canvas.convert("RGB").save(path)
            print("wrote", path, "(%s)" % label)
            written.append(path)
    finally:
        dither.dithered_state_background = _ORIG_DITHERED_BG

    print("\n%d renders written to %s" % (len(written), OUT_DIR))
    return written


if __name__ == "__main__":
    main()
