"""Behaviour tests for aircraft cutting and placement in the giant layouts."""
import os

import pytest
from PIL import Image

from server.plane import illustrations
from server.plane.render.giant import aircraft

ILLUSTRATIONS = sorted(
    name for name in os.listdir(illustrations.ILLUSTRATION_DIR) if name.endswith(".png")
)

# Cut column height may exceed the fuselage median by at most this factor.
MAX_CUT_HEIGHT_RATIO = 1.3


def _illustration_path(name):
    return os.path.join(illustrations.ILLUSTRATION_DIR, name)


def _load(name, width=800):
    with Image.open(_illustration_path(name)) as source:
        rgba = source.convert("RGBA")
    return rgba.resize((width, round(width * rgba.size[1] / rgba.size[0])), Image.LANCZOS)


def test_every_vendored_illustration_is_visited():
    assert ILLUSTRATIONS
    assert len(ILLUSTRATIONS) == len(
        [n for n in os.listdir(illustrations.ILLUSTRATION_DIR) if n.endswith(".png")]
    )


@pytest.mark.parametrize("name", ILLUSTRATIONS)
def test_cut_goes_through_bare_fuselage(name):
    rgba = _load(name)
    fraction = aircraft.cut_fraction(rgba)
    assert aircraft.CUT_SEARCH_MIN <= fraction <= aircraft.CUT_SEARCH_MAX

    content = aircraft.opaque_content(rgba)
    heights = aircraft.column_heights(content)
    column = min(len(heights) - 1, round(fraction * len(heights)))
    assert heights[column] <= MAX_CUT_HEIGHT_RATIO * aircraft.fuselage_median(content)


def test_cut_fraction_for_path_matches_and_is_cached():
    path = _illustration_path(ILLUSTRATIONS[0])
    first = aircraft.cut_fraction_for_path(path)
    assert aircraft.cut_fraction_for_path(path) == first
    assert aircraft.CUT_SEARCH_MIN <= first <= aircraft.CUT_SEARCH_MAX


def test_cut_fraction_falls_back_on_empty_and_missing_art():
    assert aircraft.cut_fraction(Image.new("RGBA", (200, 50), (0, 0, 0, 0))) == aircraft.CUT_FALLBACK
    assert aircraft.cut_fraction_for_path("/nonexistent/none.png") in (
        aircraft.CUT_FALLBACK,
        aircraft.cut_fraction_for_path("/nonexistent/other.png"),
    )


def test_cut_avoids_a_wide_wing_in_synthetic_art():
    # Fuselage 20 px deep with a 120 px deep "wing" around the middle of the
    # span, tapering to a thin tail section.
    art = Image.new("RGBA", (1000, 200), (0, 0, 0, 0))
    art.paste((255, 0, 0, 255), (0, 90, 1000, 110))
    art.paste((255, 0, 0, 255), (420, 40, 560, 160))
    fraction = aircraft.cut_fraction(art)
    heights = aircraft.column_heights(art)
    assert heights[round(fraction * len(heights))] <= 1.1 * aircraft.fuselage_median(art)
