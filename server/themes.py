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
from typing import cast

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
# Every entry is built by `_build_theme()` from three choices: the main
# colour, the background (plain white paper, a flat full field, or a soft
# field dithered ~40% toward White) and the diagonal stripe (none, solid or
# soft). Always reference panel_format's IDX_* constants, never a bare
# integer. "weight" isn't derivable from "dithered" alone: flat fields read
# best Regular; dithered fields need Bold except Yellow, which stays legible
# Regular even dithered.
#
# The ids are stored values: the first 18 specs below are frozen in name,
# order and content, and new themes are only ever appended. The ten
# combinations that cannot exist (a stripe on a full field, a soft stripe
# on a soft field) would render exactly like the same theme without the
# stripe, so they have no theme.
#
# The old two-tone "sky" pairing is retired; a stale `"theme": "sky"`
# degrades safely to DEFAULT_THEME_ID via device_config.normalise_theme_id().
BACKGROUND_PAPER = "paper"
BACKGROUND_FULL = "full"
BACKGROUND_SOFT = "soft"
STRIPE_NONE = "none"
STRIPE_SOLID = "solid"
STRIPE_SOFT = "soft"

_COLOUR_INDEXES = {
    "black": IDX_BLACK,
    "yellow": IDX_YELLOW,
    "red": IDX_RED,
    "green": IDX_GREEN,
    "blue": IDX_BLUE,
}


def _build_theme(colour: str | None, background: str, stripe: str, label: str) -> dict[str, object]:
    """One registry entry. A paper background is White with black text; a
    full or soft field takes the colour, with black text on yellow and white
    text elsewhere. A stripe adds the band keys (its colour is the main
    colour). `colour` is `None` only for plain paper.
    """
    if background == BACKGROUND_PAPER:
        field, ink, dithered, weight = IDX_WHITE, IDX_BLACK, False, "regular"
    else:
        assert colour is not None
        field = _COLOUR_INDEXES[colour]
        ink = IDX_BLACK if field == IDX_YELLOW else IDX_WHITE
        dithered = background == BACKGROUND_SOFT
        weight = "bold" if dithered and field != IDX_YELLOW else "regular"
    theme: dict[str, object] = {
        "departing_index": field,
        "arriving_index": field,
        "ink_index": ink,
        "label": label,
        "dithered": dithered,
        "weight": weight,
    }
    if stripe != STRIPE_NONE:
        assert colour is not None
        theme["band_index"] = _COLOUR_INDEXES[colour]
        theme["band_dithered"] = stripe == STRIPE_SOFT
    return theme


# (id, colour, background, stripe, label) - the 18 historical themes first
# (ids frozen), then the themes added since, in the order they were added.
# Appending only.
_LEGACY_SPECS: tuple[tuple[str, str | None, str, str, str], ...] = (
    ("white", None, BACKGROUND_PAPER, STRIPE_NONE, "White"),
    ("black", "black", BACKGROUND_FULL, STRIPE_NONE, "Black"),
    ("grey", "black", BACKGROUND_SOFT, STRIPE_NONE, "Grey"),
    ("yellow", "yellow", BACKGROUND_FULL, STRIPE_NONE, "Yellow"),
    ("yellow_light", "yellow", BACKGROUND_SOFT, STRIPE_NONE, "Yellow Light"),
    ("red", "red", BACKGROUND_FULL, STRIPE_NONE, "Red"),
    ("red_light", "red", BACKGROUND_SOFT, STRIPE_NONE, "Red Light"),
    ("green", "green", BACKGROUND_FULL, STRIPE_NONE, "Green"),
    ("green_light", "green", BACKGROUND_SOFT, STRIPE_NONE, "Green Light"),
    ("blue", "blue", BACKGROUND_FULL, STRIPE_NONE, "Blue"),
    ("blue_light", "blue", BACKGROUND_SOFT, STRIPE_NONE, "Blue Light"),
    ("band_blue", "blue", BACKGROUND_PAPER, STRIPE_SOLID, "Band Blue"),
    ("band_blue_light", "blue", BACKGROUND_PAPER, STRIPE_SOFT, "Band Blue Light"),
    ("band_green_light", "green", BACKGROUND_PAPER, STRIPE_SOFT, "Band Green Light"),
    ("band_red", "red", BACKGROUND_PAPER, STRIPE_SOLID, "Band Red"),
    ("band_black", "black", BACKGROUND_PAPER, STRIPE_SOLID, "Band Black"),
    ("band_blue_field", "blue", BACKGROUND_SOFT, STRIPE_SOLID, "Band Blue Field"),
    ("band_red_field", "red", BACKGROUND_SOFT, STRIPE_SOLID, "Band Red Field"),
)

# Id suffix and label suffix of each readable striped (background, stripe)
# pair, for the themes generated rather than listed above.
_STRIPED_NAMING = {
    (BACKGROUND_PAPER, STRIPE_SOLID): ("", ""),
    (BACKGROUND_PAPER, STRIPE_SOFT): ("_light", " Light"),
    (BACKGROUND_SOFT, STRIPE_SOLID): ("_field", " Field"),
    (BACKGROUND_FULL, STRIPE_SOFT): ("_on_full", " On Full"),
}

# The generated themes, in registry order: (colour, background, stripe).
_ADDED_COMBINATIONS = tuple(
    (colour, background, stripe)
    for background, stripe, colours in (
        (BACKGROUND_PAPER, STRIPE_SOLID, ("yellow", "green")),
        (BACKGROUND_PAPER, STRIPE_SOFT, ("black", "yellow", "red")),
        (BACKGROUND_SOFT, STRIPE_SOLID, ("black", "yellow", "green")),
        (BACKGROUND_FULL, STRIPE_SOFT, ("black", "yellow", "red", "green", "blue")),
    )
    for colour in colours
)


def _generated_specs() -> list[tuple[str, str | None, str, str, str]]:
    specs: list[tuple[str, str | None, str, str, str]] = []
    for colour, background, stripe in _ADDED_COMBINATIONS:
        id_suffix, label_suffix = _STRIPED_NAMING[(background, stripe)]
        specs.append((
            "band_%s%s" % (colour, id_suffix), colour, background, stripe,
            "Band %s%s" % (colour.capitalize(), label_suffix)))
    return specs


THEMES: dict[str, dict[str, object]] = {
    theme_id: _build_theme(colour, background, stripe, label)
    for theme_id, colour, background, stripe, label in (*_LEGACY_SPECS, *_generated_specs())
}

THEME_IDS = tuple(THEMES)


# --- Presentation accessors -------------------------------------------
#
# Every accessor below takes an already-normalised id and never raises
# for a valid, registry-member id.


def theme_background_index(state: str, theme_id: str) -> int:
    """The theme's background palette index for `state`
    ("departing"/"arriving"/"overhead"). Raises `ValueError` for any other
    state. Overhead uses the departing colour (every theme sets both equal).
    """
    theme = THEMES[theme_id]
    if state in ("departing", "overhead"):
        return cast(int, theme["departing_index"])
    if state == "arriving":
        return cast(int, theme["arriving_index"])
    raise ValueError("unknown state %r (expected 'departing', 'arriving' or 'overhead')" % (state,))


def theme_ink_index(theme_id: str) -> int:
    return cast(int, THEMES[theme_id]["ink_index"])


def theme_label(theme_id: str) -> str:
    return cast(str, THEMES[theme_id]["label"])


def theme_dithered(theme_id: str) -> bool:
    """Whether `theme_id`'s background is dithered rather than flat - see
    THEMES' own comment.
    """
    return cast(bool, THEMES[theme_id]["dithered"])


def theme_weight(theme_id: str) -> str:
    """`theme_id`'s PT Serif weight ("regular"/"bold"); not derivable from
    `theme_dithered()` alone - see THEMES' own comment.
    """
    return cast(str, THEMES[theme_id]["weight"])


def theme_is_band(theme_id: str) -> bool:
    """Whether `theme_id` is a diagonal-band theme - true iff its THEMES
    entry carries the band-only `"band_index"` key.
    """
    return "band_index" in THEMES[theme_id]


def theme_band_index(theme_id: str) -> int | None:
    """`theme_id`'s diagonal band colour as a panel_format.IDX_* constant,
    or `None` for a non-band theme.
    """
    return cast("int | None", THEMES[theme_id].get("band_index"))


def theme_band_dithered(theme_id: str) -> bool:
    """Whether `theme_id`'s diagonal band is dithered; `False` for a
    non-band theme.
    """
    return cast(bool, THEMES[theme_id].get("band_dithered", False))


def band_text_ink(band_index: int | None) -> int:
    """The ink for text drawn inside a stripe of colour `band_index`: black
    on a yellow stripe (white on yellow is illegible), white otherwise.
    """
    return IDX_BLACK if band_index == IDX_YELLOW else IDX_WHITE


def theme_band_ink_index(theme_id: str) -> int:
    """The ink for text inside `theme_id`'s stripe; white for a non-band
    theme, where it is unused.
    """
    return band_text_ink(theme_band_index(theme_id))


# --- Ink requirements --------------------------------------------------
#
# A hardware profile lists the inks its panel can show; a theme is only
# offered when every ink it draws with is available.


def theme_required_inks(theme_id: str) -> frozenset[int]:
    """Palette indices `theme_id` draws with: its two backgrounds, text ink
    and band colour with its text ink (if any), plus White (the paper every theme sits on).
    """
    inks = {
        theme_background_index("departing", theme_id),
        theme_background_index("arriving", theme_id),
        theme_ink_index(theme_id),
        IDX_WHITE,
    }
    band = theme_band_index(theme_id)
    if band is not None:
        inks.add(band)
        inks.add(band_text_ink(band))
    return frozenset(inks)


def themes_for_inks(inks: frozenset[int]) -> tuple[str, ...]:
    """Theme ids, in registry order, whose required inks are all in `inks`."""
    return tuple(t for t in THEME_IDS if theme_required_inks(t) <= inks)


def theme_or_default(theme_id: str, inks: frozenset[int]) -> str:
    """`theme_id` when it exists and `inks` can show it, else the default.

    Pure: stored configuration is never rewritten.
    """
    if theme_id in themes_for_inks(inks):
        return theme_id
    return DEFAULT_THEME_ID
