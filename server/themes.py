#!/usr/bin/env python3
"""The theme registry and its presentation accessors.

`THEMES`' keys are stable on-disk values in `device_config.json` -
`tests/`-style renames are never safe here; append a new entry instead of
renaming an existing one. `server/device_config.py` re-exports every name
this module defines for read access, so every existing caller and test
keeps working unchanged; nothing outside this module rebinds `THEMES`,
`THEME_IDS` or `DEFAULT_THEME_ID`.

Leaf module: stdlib plus `server.panel_format` only.
"""
from __future__ import annotations

import os
import sys

# Allow both `import server.themes` (package import) and direct script
# execution: sys.path[0] is server/ itself when this file is executed
# directly, so the repo root must be added by hand before the absolute
# `server.panel_format` import below can resolve.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server.panel_format import IDX_BLACK, IDX_BLUE, IDX_GREEN, IDX_RED, IDX_WHITE, IDX_YELLOW

DEFAULT_THEME_ID = "white"

# --- Theme registry ----------------------------------------------------
#
# Always reference panel_format's IDX_* constants, never a bare integer.
# "dithered" selects a flat field vs. the same ink dithered ~40% toward
# White (a flat saturated field reads too harsh at full-panel coverage).
# "weight" isn't derivable from "dithered" alone: flat fields read best
# Regular; dithered fields need Bold except Yellow, which stays legible
# Regular even dithered.
#
# The old two-tone "sky" pairing is retired; a stale `"theme": "sky"`
# degrades safely to DEFAULT_THEME_ID via device_config.normalise_theme_id().
THEMES: dict[str, dict[str, object]] = {
    "white": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "White",
        "dithered": False,
        "weight": "regular",
    },
    "black": {
        "departing_index": IDX_BLACK,
        "arriving_index": IDX_BLACK,
        "ink_index": IDX_WHITE,
        "label": "Black",
        "dithered": False,
        "weight": "regular",
    },
    "grey": {
        "departing_index": IDX_BLACK,
        "arriving_index": IDX_BLACK,
        "ink_index": IDX_WHITE,
        "label": "Grey",
        "dithered": True,
        "weight": "bold",
    },
    "yellow": {
        "departing_index": IDX_YELLOW,
        "arriving_index": IDX_YELLOW,
        "ink_index": IDX_BLACK,
        "label": "Yellow",
        "dithered": False,
        "weight": "regular",
    },
    "yellow_light": {
        "departing_index": IDX_YELLOW,
        "arriving_index": IDX_YELLOW,
        "ink_index": IDX_BLACK,
        "label": "Yellow Light",
        "dithered": True,
        "weight": "regular",
    },
    "red": {
        "departing_index": IDX_RED,
        "arriving_index": IDX_RED,
        "ink_index": IDX_WHITE,
        "label": "Red",
        "dithered": False,
        "weight": "regular",
    },
    "red_light": {
        "departing_index": IDX_RED,
        "arriving_index": IDX_RED,
        "ink_index": IDX_WHITE,
        "label": "Red Light",
        "dithered": True,
        "weight": "bold",
    },
    "green": {
        "departing_index": IDX_GREEN,
        "arriving_index": IDX_GREEN,
        "ink_index": IDX_WHITE,
        "label": "Green",
        "dithered": False,
        "weight": "regular",
    },
    "green_light": {
        "departing_index": IDX_GREEN,
        "arriving_index": IDX_GREEN,
        "ink_index": IDX_WHITE,
        "label": "Green Light",
        "dithered": True,
        "weight": "bold",
    },
    "blue": {
        "departing_index": IDX_BLUE,
        "arriving_index": IDX_BLUE,
        "ink_index": IDX_WHITE,
        "label": "Blue",
        "dithered": False,
        "weight": "regular",
    },
    "blue_light": {
        "departing_index": IDX_BLUE,
        "arriving_index": IDX_BLUE,
        "ink_index": IDX_WHITE,
        "label": "Blue Light",
        "dithered": True,
        "weight": "bold",
    },
    # Diagonal-band themes: base canvas renders as build_canvas("white");
    # only label, band_index and band_dithered vary between these 5. Read
    # via theme_is_band()/theme_band_index()/theme_band_dithered() below,
    # never by indexing THEMES directly.
    "band_blue": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Blue",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_BLUE,
        "band_dithered": False,
    },
    "band_blue_light": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Blue Light",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_BLUE,
        "band_dithered": True,
    },
    "band_green_light": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Green Light",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_GREEN,
        "band_dithered": True,
    },
    "band_red": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Red",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_RED,
        "band_dithered": False,
    },
    "band_black": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "Band Black",
        "dithered": False,
        "weight": "regular",
        "band_index": IDX_BLACK,
        "band_dithered": False,
    },
    # Two "tone-on-tone" themes whose field is not White: base-canvas
    # fields copied from the matching `_light` theme (ink/weight too -
    # draw_main_text_block() forces white ink for every band theme, so a
    # row's own ink_index only colours outside the band). band_index
    # equals the field colour on purpose; band_dithered is False for a
    # solid diagonal.
    "band_blue_field": {
        "departing_index": IDX_BLUE,
        "arriving_index": IDX_BLUE,
        "ink_index": IDX_WHITE,
        "label": "Band Blue Field",
        "dithered": True,
        "weight": "bold",
        "band_index": IDX_BLUE,
        "band_dithered": False,
    },
    "band_red_field": {
        "departing_index": IDX_RED,
        "arriving_index": IDX_RED,
        "ink_index": IDX_WHITE,
        "label": "Band Red Field",
        "dithered": True,
        "weight": "bold",
        "band_index": IDX_RED,
        "band_dithered": False,
    },
}

THEME_IDS = tuple(THEMES)


# --- Presentation accessors -------------------------------------------
#
# Every accessor below takes an already-normalised id and never raises
# for a valid, registry-member id.


def theme_background_index(state: str, theme_id: str) -> int:
    """The theme's background palette index for `state`
    ("departing"/"arriving"). Raises `ValueError` for any other state.
    """
    theme = THEMES[theme_id]
    if state == "departing":
        return theme["departing_index"]
    if state == "arriving":
        return theme["arriving_index"]
    raise ValueError("unknown state %r (expected 'departing' or 'arriving')" % (state,))


def theme_ink_index(theme_id: str) -> int:
    return THEMES[theme_id]["ink_index"]


def theme_label(theme_id: str) -> str:
    return THEMES[theme_id]["label"]


def theme_dithered(theme_id: str) -> bool:
    """Whether `theme_id`'s background is dithered rather than flat - see
    THEMES' own comment.
    """
    return THEMES[theme_id]["dithered"]


def theme_weight(theme_id: str) -> str:
    """`theme_id`'s PT Serif weight ("regular"/"bold"); not derivable from
    `theme_dithered()` alone - see THEMES' own comment.
    """
    return THEMES[theme_id]["weight"]


def theme_is_band(theme_id: str) -> bool:
    """Whether `theme_id` is a diagonal-band theme - true iff its THEMES
    entry carries the band-only `"band_index"` key.
    """
    return "band_index" in THEMES[theme_id]


def theme_band_index(theme_id: str) -> int | None:
    """`theme_id`'s diagonal band colour as a panel_format.IDX_* constant,
    or `None` for a non-band theme.
    """
    return THEMES[theme_id].get("band_index")


def theme_band_dithered(theme_id: str) -> bool:
    """Whether `theme_id`'s diagonal band is dithered; `False` for a
    non-band theme.
    """
    return THEMES[theme_id].get("band_dithered", False)
