#!/usr/bin/env python3
"""Legibility floor over the whole theme catalogue.

Colours are the panel palette's, a dithered (soft) ink lightened toward
White by the renderer's own fraction. For every theme, the text drawn on
the field and, for a striped theme, the text drawn inside the stripe must
reach `TEXT_CONTRAST_FLOOR`; the stripe must also be told apart from the
field it crosses by at least `STRIPE_VISIBILITY_FLOOR` (a yellow stripe on
a yellow field is only just visible by design, so this is a visibility
check, not a legibility one).
"""
import inspect

import pytest

from server import panel_format, themes
from server.plane import dither

TEXT_CONTRAST_FLOOR = 2.7
STRIPE_VISIBILITY_FLOOR = 1.1
LIGHTEN_FRACTION = inspect.signature(dither.dithered_state_background).parameters[
    "lighten_fraction"].default


def _rgb(index, dithered=False):
    r, g, b = panel_format.PALETTE_RGB[index * 3: index * 3 + 3]
    if dithered and index != panel_format.IDX_WHITE:
        return tuple(round(v + (255 - v) * LIGHTEN_FRACTION) for v in (r, g, b))
    return (r, g, b)


def _luminance(colour):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = colour
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a, b):
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("theme_id", themes.THEME_IDS)
def test_text_on_the_field_reaches_the_floor(theme_id):
    field = _rgb(themes.theme_background_index("departing", theme_id), themes.theme_dithered(theme_id))
    ink = _rgb(themes.theme_ink_index(theme_id))
    assert _contrast(ink, field) >= TEXT_CONTRAST_FLOOR, theme_id


@pytest.mark.parametrize("theme_id", [t for t in themes.THEME_IDS if themes.theme_is_band(t)])
def test_text_inside_the_stripe_reaches_the_floor_and_the_stripe_shows(theme_id):
    band_index = themes.theme_band_index(theme_id)
    band = _rgb(band_index, themes.theme_band_dithered(theme_id))
    field = _rgb(themes.theme_background_index("departing", theme_id), themes.theme_dithered(theme_id))
    ink = _rgb(themes.theme_band_ink_index(theme_id))
    assert _contrast(ink, band) >= TEXT_CONTRAST_FLOOR, theme_id
    assert _contrast(band, field) >= STRIPE_VISIBILITY_FLOOR, theme_id


def test_yellow_stripes_take_black_text_and_no_other_stripe_does():
    for theme_id in themes.THEME_IDS:
        band = themes.theme_band_index(theme_id)
        if band is None:
            continue
        black = themes.theme_band_ink_index(theme_id) == panel_format.IDX_BLACK
        assert black == (band == panel_format.IDX_YELLOW), theme_id
