#!/usr/bin/env python3
"""The five field/lettering pairings of the giant-lettering screen and the
mapping from every stored theme id onto one of them.

Pairing ids deliberately reuse existing `server.themes.THEMES` ids, so every
validator that accepts a theme id keeps working and stored configuration is
never rewritten: `pairing_for_theme` is a pure read-time lookup.

Assumed defaults - this module is the single place to adjust them:
  * every green theme maps to the grey pairing (no green pairing exists);
  * every black theme, plain or striped, maps to the grey pairing (black
    lettering on a light grey field).

Leaf module: stdlib plus `server.themes` only.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

# Allow both `import server.pairings` and direct script execution.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server.panel_format import IDX_BLACK, IDX_BLUE, IDX_GREEN, IDX_RED, IDX_WHITE, IDX_YELLOW
from server.themes import DEFAULT_THEME_ID, THEMES

# Fraction of the way a field's ink is dithered toward white.
FIELD_LIGHTEN_DEFAULT = 0.4
FIELD_LIGHTEN_YELLOW = 0.75


@dataclass(frozen=True)
class Pairing:
    """One field colour with the ink that letters on it.

    `field_ink` and `lettering_ink` are panel palette names (the suffix of a
    `server.panel_format.IDX_*` constant, lowercase). `field_lighten` is the
    fraction dithered toward white, or None for a flat field.
    """

    id: str
    field_ink: str
    lettering_ink: str
    field_lighten: float | None
    small_text_dither_toward_black: bool
    band_allowed: bool


PAIRINGS: dict[str, Pairing] = {
    "grey": Pairing("grey", "black", "black", FIELD_LIGHTEN_DEFAULT, False, True),
    "blue_light": Pairing("blue_light", "blue", "blue", FIELD_LIGHTEN_DEFAULT, False, True),
    "red_light": Pairing("red_light", "red", "red", FIELD_LIGHTEN_DEFAULT, False, True),
    # Yellow has no darker ink than black, so its field is much lighter and
    # small text is dithered toward black to stay legible.
    "yellow_light": Pairing("yellow_light", "yellow", "yellow", FIELD_LIGHTEN_YELLOW, True, True),
    "white": Pairing("white", "white", "black", None, False, False),
}

# Pairing id by the panel palette index of a theme's main colour. Black and
# green have no pairing of their own and both land on the grey pairing.
_PAIRING_BY_INDEX: dict[int, str] = {
    IDX_BLACK: "grey",
    IDX_YELLOW: "yellow_light",
    IDX_RED: "red_light",
    IDX_GREEN: "grey",
    IDX_BLUE: "blue_light",
}


def _pairing_id(entry: dict[str, object]) -> str:
    """The pairing id for one registry entry, from its colours alone.

    A theme on a coloured field takes the field's colour; a theme on paper
    with a stripe takes the stripe's colour; plain paper is the white
    pairing. Reading the entry (rather than listing ids) keeps every theme
    the registry gains later mapped.
    """
    field = entry["departing_index"]
    band = entry.get("band_index")
    colour = band if field == IDX_WHITE and band is not None else field
    if colour == IDX_WHITE:
        return "white"
    assert isinstance(colour, int)
    return _PAIRING_BY_INDEX[colour]


# Every registered theme id and its pairing id, read from the registry.
PAIRING_FOR_THEME: dict[str, str] = {theme_id: _pairing_id(entry) for theme_id, entry in THEMES.items()}


def pairing_for_theme(theme_id: str | None) -> Pairing:
    """The pairing for a stored theme id; an unknown or missing id gets the
    default theme's pairing. Pure: nothing stored is rewritten.
    """
    if theme_id is None or theme_id not in THEMES:
        theme_id = DEFAULT_THEME_ID
    return PAIRINGS[PAIRING_FOR_THEME[theme_id]]
