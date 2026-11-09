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


FRAME_SIZES = [(1200, 1600), (800, 480)]


def _nose(name, canvas_size):
    path = _illustration_path(name)
    cut = aircraft.nose_cut(canvas_size, aircraft.cut_fraction_for_path(path))
    plane = aircraft.load_content(path, round(canvas_size[0] * aircraft.NOSE_PLANE_WIDTH_FRAC))
    return aircraft.split_halves(plane, cut)[0]


def _rear(name, canvas_size):
    path = _illustration_path(name)
    cut = aircraft.rear_cut(canvas_size, aircraft.cut_fraction_for_path(path))
    plane = aircraft.load_content(path, round(canvas_size[0] * aircraft.REAR_PLANE_WIDTH_FRAC))
    return aircraft.split_halves(plane, cut)[1]


def _halves(name, canvas_size):
    return _nose(name, canvas_size), _rear(name, canvas_size)


def _palette_canvas(size):
    from server import panel_format

    canvas = Image.new("P", size, panel_format.IDX_BLUE)
    canvas.putpalette(panel_format.PALETTE_RGB)
    return canvas


@pytest.mark.parametrize("size", FRAME_SIZES)
def test_cut_columns_lie_outside_the_canvas(size):
    nose, rear = _halves("air-france.png", size)
    n_left, n_top, n_right, n_bottom = aircraft.nose_half(size, nose.size)
    r_left, r_top, r_right, r_bottom = aircraft.rear_half(size, rear.size)
    assert n_right >= size[0]
    assert n_left < size[0]
    assert r_left <= 0
    assert r_right > 0
    assert n_bottom - n_top == nose.size[1] and r_bottom - r_top == rear.size[1]


def test_rear_half_sits_below_the_nose_half_in_portrait():
    size = (1200, 1600)
    nose, rear = _halves("generic-a320.png", size)
    assert aircraft.rear_half(size, rear.size)[1] > aircraft.nose_half(size, nose.size)[3]


@pytest.mark.parametrize("size", FRAME_SIZES)
def test_whole_aircraft_fits_and_centres_in_the_box(size):
    box = (50, 100, size[0] - 50, 400)
    fitted, rect = aircraft.whole_aircraft(box, (2000, 600))
    assert rect[2] - rect[0] == fitted[0] and rect[3] - rect[1] == fitted[1]
    assert box[0] <= rect[0] and rect[2] <= box[2] and box[1] <= rect[1] and rect[3] <= box[3]
    assert abs((rect[0] - box[0]) - (box[2] - rect[2])) <= 1
    assert abs(fitted[0] / fitted[1] - 2000 / 600) < 0.05


@pytest.mark.parametrize("size", FRAME_SIZES)
@pytest.mark.parametrize("name", ["air-france.png", "gendarmerie-nationale.png", "generic-atr72.png"])
def test_painted_halves_use_only_palette_indices(size, name):
    nose, rear = _halves(name, size)
    canvas = _palette_canvas(size)
    halo = aircraft.halo_radius(size)
    n_left, n_top, _, _ = aircraft.nose_half(size, nose.size)
    r_left, r_top, _, _ = aircraft.rear_half(size, rear.size)
    aircraft.paint_aircraft(canvas, nose, n_left, n_top, halo)
    aircraft.paint_aircraft(canvas, rear, r_left, r_top, halo)
    used = {index for _, index in canvas.getcolors()}
    assert used <= set(range(6))
    assert canvas.size == size
    assert canvas.getbbox() is not None
    assert len(used) > 1


def test_halo_is_a_solid_white_ring_around_the_body():
    from server import panel_format

    body = Image.new("RGBA", (60, 20), (200, 0, 0, 255))
    canvas = _palette_canvas((100, 60))
    aircraft.paint_aircraft(canvas, body, 20, 20, 4)
    assert canvas.getpixel((19, 30)) == panel_format.IDX_WHITE
    assert canvas.getpixel((16, 30)) == panel_format.IDX_WHITE
    assert canvas.getpixel((10, 30)) == panel_format.IDX_BLUE
    assert {i for _, i in canvas.getcolors()} <= set(range(6))


def test_whole_aircraft_paints_clean_palette():
    size = (1200, 1600)
    plane = aircraft.load_content(_illustration_path("easyjet.png"), 1120)
    fitted, rect = aircraft.whole_aircraft((40, 600, 1160, 1000), plane.size)
    canvas = _palette_canvas(size)
    aircraft.paint_aircraft(canvas, plane.resize(fitted, Image.LANCZOS), rect[0], rect[1], aircraft.halo_radius(size))
    assert {i for _, i in canvas.getcolors()} <= set(range(6))


PORTRAIT = (1200, 1600)


@pytest.mark.parametrize("name", ILLUSTRATIONS)
def test_halves_have_the_validated_extent_for_every_illustration(name):
    width = PORTRAIT[0]
    nose, rear = _halves(name, PORTRAIT)
    n_left, _, n_right, _ = aircraft.nose_half(PORTRAIT, nose.size)
    r_left, _, r_right, _ = aircraft.rear_half(PORTRAIT, rear.size)
    # Cockpit tip near 130 px; the nose half bleeds off the right edge.
    assert 110 <= n_left <= 150
    assert n_right > width
    # The rear half bleeds off the left edge and its tail ends near 595 px.
    assert r_left < 0
    assert 570 <= r_right <= 620
    # The cut columns stay within half a canvas width of the frame.
    assert n_right - width <= width // 2
    assert -r_left <= width // 2
    # The halves do not overlap horizontally on the rows they share.
    n_top, n_bottom = aircraft.nose_half(PORTRAIT, nose.size)[1::2]
    r_top, r_bottom = aircraft.rear_half(PORTRAIT, rear.size)[1::2]
    assert r_top >= n_bottom or r_bottom <= n_top or r_right <= n_left
