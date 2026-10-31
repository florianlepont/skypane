"""Landscape hold screens render natively at the profile's size."""
import dataclasses
from collections import Counter

import pytest

from server import hardware
from server import panel_format as pf
from server.plane import dither
from server.plane.render import landscape_hold as lh

PROFILE = hardware.get_profile(
    hardware.SIM_LANDSCAPE_KEY, {hardware.SIM_ENV_VAR: "1"}
)
SIZE = (PROFILE.width, PROFILE.height)

BUILDERS = {
    "empty": lambda s: lh.build_empty_canvas(s),
    "quiet": lambda s: lh.build_quiet_hours_canvas(s, "07:00"),
    "quiet_none": lambda s: lh.build_quiet_hours_canvas(s, None),
    "display_off": lambda s: lh.build_display_off_canvas(s),
    "battery_empty": lambda s: lh.build_battery_empty_canvas(s),
    "no_connection": lambda s: lh.build_no_connection_canvas(s),
    "updating": lambda s: lh.build_updating_canvas(s),
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_size_packing_palette(name):
    canvas = BUILDERS[name](SIZE)
    assert canvas.size == SIZE
    assert len(pf.pack_panel(canvas)) == 192000
    assert set(canvas.tobytes()) <= set(pf.INDEX_TO_NIBBLE)


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_deterministic(name):
    assert BUILDERS[name](SIZE).tobytes() == BUILDERS[name](SIZE).tobytes()


def test_empty_field_is_white():
    counts = Counter(BUILDERS["empty"](SIZE).tobytes())
    assert counts.most_common(1)[0][0] == pf.IDX_WHITE


def test_dimmed_field_is_dark_dominant():
    counts = Counter(BUILDERS["display_off"](SIZE).tobytes())
    assert counts.most_common(1)[0][0] == pf.IDX_BLACK


def test_ink_stays_inside_margins():
    from server.plane.render import landscape_common as common

    margin = common.margin_for(SIZE)
    canvas = BUILDERS["empty"](SIZE)
    mask = canvas.point(lambda v: 255 if v != pf.IDX_WHITE else 0)
    left, top, right, bottom = mask.getbbox()
    assert left >= margin and top >= margin
    assert right <= SIZE[0] - margin and bottom <= SIZE[1] - margin


def test_glyph_left_text_right():
    canvas = BUILDERS["empty"](SIZE)
    mask = canvas.point(lambda v: 255 if v != pf.IDX_WHITE else 0)
    left_half = mask.crop((0, 0, SIZE[0] // 4, SIZE[1])).getbbox()
    far_right = mask.crop((SIZE[0] // 2, 0, SIZE[0], SIZE[1])).getbbox()
    assert left_half is not None and far_right is not None


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_other_even_size(name):
    other = dataclasses.replace(PROFILE, width=1024, height=600)
    size = (other.width, other.height)
    canvas = BUILDERS[name](size)
    assert canvas.size == size
    assert len(pf.pack_panel(canvas)) == 1024 // 2 * 600


def test_sizes_do_not_poison_each_other():
    BUILDERS["display_off"]((1024, 600))
    assert dither.dithered_state_background(pf.IDX_BLACK).size == (1200, 1600)
