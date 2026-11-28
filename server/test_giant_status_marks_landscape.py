# SPDX-License-Identifier: AGPL-3.0-only
"""Landscape giant status screens: the battery-low glyph and source-fault
badge sit at the top right, on blank pixels, readable and apart."""
import pytest
from PIL import ImageChops

from server.plane.render import landscape_common, style
from server.plane.render.giant import status

SIZE = (800, 480)
PORTRAIT = (1200, 1600)
KINDS = ("watching", "quiet_hours", "display_off")
MARKS = (
    {"battery_low": True},
    {"source_fault": True},
    {"battery_low": True, "source_fault": True},
)
INK_FLAT = style.DIMMED_INK


def _build(kind, size=SIZE, flat=True, **marks):
    return status.build_status(kind, size, quiet_hours_until="07:00", flat=flat, **marks)


def _ink_of(kind):
    return style.EMPTY_INK if kind == "watching" else style.DIMMED_INK


def _diff_box(kind, marks, flat=True):
    diff = ImageChops.difference(_build(kind, flat=flat, **marks), _build(kind, flat=flat))
    return diff.getbbox()


@pytest.mark.parametrize("marks", MARKS)
@pytest.mark.parametrize("kind", KINDS)
def test_marks_are_visible_in_the_top_right(kind, marks):
    for flat in (True, False):
        box = _diff_box(kind, marks, flat)
        assert box is not None
        margin = landscape_common.margin_for(SIZE)
        assert (box[0] + box[2]) / 2 > SIZE[0] // 2
        assert box[1] >= margin and box[3] <= 150
        assert box[2] <= SIZE[0] - margin


@pytest.mark.parametrize("marks", MARKS)
@pytest.mark.parametrize("kind", KINDS)
def test_marks_only_paint_on_blank_pixels(kind, marks):
    plain = _build(kind)
    marked = _build(kind, **marks)
    ink = _ink_of(kind)
    box = marked_box = ImageChops.difference(marked, plain).getbbox()
    assert box is not None
    pad = 3
    region = (max(0, box[0] - pad), max(0, box[1] - pad), box[2] + pad, box[3] + pad)
    px = plain.load()
    # The plain flat render holds only text and icon ink: the whole box the
    # marks occupy, with a margin, must be free of it.
    for x in range(region[0], min(region[2], SIZE[0])):
        for y in range(region[1], min(region[3], SIZE[1])):
            assert px[x, y] != ink, (x, y, marked_box)


@pytest.mark.parametrize("marks", MARKS)
@pytest.mark.parametrize("kind", KINDS)
def test_nothing_new_bottom_left(kind, marks):
    for flat in (True, False):
        diff = ImageChops.difference(_build(kind, flat=flat, **marks), _build(kind, flat=flat))
        corner = diff.crop((0, SIZE[1] // 2, SIZE[0] // 2, SIZE[1]))
        assert corner.getbbox() is None


@pytest.mark.parametrize("kind", KINDS)
def test_both_marks_do_not_overlap_and_caption_is_whole(kind):
    battery = ImageChops.difference(_build(kind, battery_low=True), _build(kind)).getbbox()
    both_img = _build(kind, battery_low=True, source_fault=True)
    fault = ImageChops.difference(both_img, _build(kind, battery_low=True)).getbbox()
    both = ImageChops.difference(both_img, _build(kind)).getbbox()
    assert battery and fault and both
    apart = (battery[2] <= fault[0] or fault[2] <= battery[0]
             or battery[3] <= fault[1] or fault[3] <= battery[1])
    assert apart
    # Union of the single-mark footprints equals the both-marks footprint.
    union = (min(battery[0], fault[0]), min(battery[1], fault[1]),
             max(battery[2], fault[2]), max(battery[3], fault[3]))
    assert both == union
    # The caption is not cut short: its full text width is painted.
    from server.plane.render import text
    font = text._font((text._role_weight_path("bold"), max(10, round(SIZE[1] * 0.03)), None))
    caption_w = font.getlength("Check the companion page")
    assert fault[2] - fault[0] >= caption_w
    # The landscape caption is the short one, not the long portrait text.
    assert fault[2] - fault[0] < font.getlength(style.SOURCE_FAULT_TEXT)


def test_landscape_caption_reads_check_the_companion_page(monkeypatch):
    from PIL import ImageDraw
    drawn = []
    real = ImageDraw.ImageDraw.text

    def spy(self, xy, text, *args, **kwargs):
        drawn.append(text)
        return real(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
    _build("watching", source_fault=True)
    assert "Check the companion page" in drawn
    assert style.SOURCE_FAULT_TEXT not in drawn


@pytest.mark.parametrize("kind", KINDS)
def test_portrait_marks_stay_at_the_bottom(kind):
    plain = status.build_status(kind, PORTRAIT, flat=True)
    marked = status.build_status(kind, PORTRAIT, flat=True, battery_low=True, source_fault=True)
    box = ImageChops.difference(marked, plain).getbbox()
    assert box is not None and box[1] > PORTRAIT[1] // 2
