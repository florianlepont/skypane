"""Behaviour tests for the calm status screens (giant family)."""
import time

import pytest

from server import panel_format as pf
from server.plane.render.giant import icons, status
from server.plane.render.giant.palette_check import assert_giant_palette

PORTRAIT = (1200, 1600)
LANDSCAPE = (800, 480)
SIZES = (PORTRAIT, LANDSCAPE)


def _ink_columns(canvas, ink, box):
    """Leftmost column inside `box` holding an ink pixel, or None."""
    x0, y0, x1, y1 = box
    px = canvas.load()
    for x in range(x0, x1):
        if any(px[x, y] == ink for y in range(y0, y1)):
            return x
    return None


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("kind", status.KINDS)
def test_every_kind_renders_with_legal_palette(kind, size):
    canvas = status.build_status(kind, size, quiet_hours_until="07:00")
    assert canvas.size == size and canvas.mode == "P"
    assert_giant_palette(canvas, pf.IDX_WHITE if kind == "watching" else pf.IDX_BLACK)


@pytest.mark.parametrize("size", SIZES)
def test_watching_is_black_on_white_only(size):
    colors = {value for _count, value in status.build_status("watching", size).getcolors()}
    assert colors == {pf.IDX_WHITE, pf.IDX_BLACK}


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("kind", [k for k in status.KINDS if k != "watching"])
def test_dark_screens_use_only_black_and_white(kind, size):
    colors = {value for _count, value in status.build_status(kind, size).getcolors()}
    assert colors == {pf.IDX_WHITE, pf.IDX_BLACK}


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("kind", ["no_connection", "updating"])
def test_flat_variants_have_exactly_two_colours(kind, size):
    colors = {value for _count, value in status.build_status(kind, size, flat=True).getcolors()}
    assert colors == {pf.IDX_WHITE, pf.IDX_BLACK}
    dithered = status.build_status(kind, size)
    assert dithered.tobytes() != status.build_status(kind, size, flat=True).tobytes()


@pytest.mark.parametrize("size", SIZES)
def test_battery_empty_is_a_pure_function_of_size(size):
    first = status.build_status("battery_empty", size)
    again = status.build_status(
        "battery_empty", size, quiet_hours_until="09:30", source_fault=True,
        battery_low=True, runway_id="06-24")
    assert first.tobytes() == again.tobytes()


@pytest.mark.parametrize("size", SIZES)
def test_text_is_flush_left_at_the_margin(size):
    geom = status._geometry(size)
    canvas = status.build_status("display_off", size, flat=True)
    # Giant lines: from the top of the lettering slot to the body.
    box = (0, geom.giant_top, size[0], geom.giant_bottom)
    left = _ink_columns(canvas, pf.IDX_WHITE, box)
    # Ink starts at the margin, give or take a pixel of rounding.
    assert abs(left - geom.margin) <= 1


def test_portrait_margin_is_110_and_landscape_margin_is_33():
    assert status._geometry(PORTRAIT).margin == 110
    assert status._geometry(LANDSCAPE).margin == 33
    assert status._geometry(LANDSCAPE).icon_h == 60
    assert status._geometry(PORTRAIT).icon_h == 120


@pytest.mark.parametrize("size", SIZES)
def test_giant_lines_stay_inside_the_margins(size):
    geom = status._geometry(size)
    for kind in ("no_connection", "updating", "retired", "watching"):
        canvas = status.build_status(kind, size, flat=True)
        ink = pf.IDX_WHITE
        if kind == "watching":
            canvas = status.build_status(kind, size)
            ink = pf.IDX_BLACK
        px = canvas.load()
        for x in list(range(0, geom.margin - 1)) + list(range(size[0] - geom.margin + 1, size[0])):
            assert all(px[x, y] != ink for y in range(geom.giant_top, geom.giant_bottom))


def test_quiet_hours_body_needs_a_time():
    with_time = status.build_status("quiet_hours", PORTRAIT, quiet_hours_until="07:00")
    without = status.build_status("quiet_hours", PORTRAIT)
    assert with_time.tobytes() != without.tobytes()
    assert status._body_lines("quiet_hours", "3", None) == ()
    assert status._body_lines("quiet_hours", "3", "07:00") == ("Back at 07:00",)


def test_watching_headline_follows_the_runway():
    assert status._headline("watching", "3") == (("RUNWAY", "3"), "WATCHING")
    assert status._headline("watching", "06-24")[0] == ("RUNWAY", "06/24")


def test_status_marks_change_the_picture():
    for size in SIZES:
        plain = status.build_status("watching", size)
        assert status.build_status("watching", size, battery_low=True).tobytes() != plain.tobytes()
        assert status.build_status("watching", size, source_fault=True).tobytes() != plain.tobytes()


def test_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        status.build_status("pairing", PORTRAIT)


@pytest.mark.parametrize("kind", sorted(icons.ICONS))
def test_icons_are_binary_clean_masks_of_the_requested_height(kind):
    mask = icons.icon_mask(kind, 120)
    assert {v for _c, v in mask.getcolors()} == {0, 255}
    assert 118 <= mask.height <= 124
    assert mask.getbbox() == (0, 0, mask.width, mask.height)


def test_icon_edges_are_not_stair_stepped():
    # A scaled ring has the same ink area as the ideal annulus within a few
    # percent; nearest-neighbour upscaling of the 76px glyph would not keep
    # the stroke width.
    mask = icons.icon_mask("display_off", 120)
    area = sum(1 for v in mask.getdata() if v)
    assert 3000 < area < 4200


def test_rendering_all_screens_is_fast():
    start = time.monotonic()
    for kind in status.KINDS:
        for size in SIZES:
            status.build_status(kind, size, quiet_hours_until="07:00")
    assert time.monotonic() - start < 10
