"""Behaviour tests for the giant-lettering drawing primitives."""
import pytest
from PIL import Image, ImageDraw

from server import panel_format as pf
from server.pairings import PAIRINGS
from server.plane.render import layout
from server.plane.render.giant import field, lettering, palette_check

BOX_W = 600
SLOT_H = 150


def _band_canvas_mask(size):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle((0, 0, size[0] // 2 - 1, size[1]), fill=255)
    return mask


def test_line_mask_is_exact_size_and_strictly_binary():
    mask = lettering.line_mask("MARSEILLE", BOX_W, SLOT_H)
    assert mask.size == (BOX_W, SLOT_H)
    assert mask.mode == "L"
    assert set(mask.tobytes()) <= {0, 255}
    assert 255 in set(mask.tobytes())


def test_line_fills_the_slot_edge_to_edge():
    bbox = lettering.line_mask("HAMBURG", BOX_W, SLOT_H).getbbox()
    assert bbox[0] <= 2 and bbox[2] >= BOX_W - 2
    assert bbox[1] <= 2 and bbox[3] >= SLOT_H - 2


def test_accented_line_keeps_the_letter_height_of_a_plain_line():
    plain, plain_over = lettering.line_layer("SAINT-ETIENNE", BOX_W, SLOT_H)
    accented, accent_over = lettering.line_layer("SAINT-ÉTIENNE", BOX_W, SLOT_H)
    assert plain_over <= 3  # round-letter overshoot only
    assert accent_over > 10 * max(plain_over, 1)
    for layer, over in ((plain, plain_over), (accented, accent_over)):
        caps = layer.crop((0, over, BOX_W, over + SLOT_H))
        bbox = caps.getbbox()
        assert bbox[3] - bbox[1] >= SLOT_H - 2
    assert accented.height == SLOT_H + accent_over


def test_downsample_option_stays_binary():
    layer, _ = lettering.line_layer("NICE", BOX_W, SLOT_H, downsample_2x=True)
    assert layer.width == BOX_W
    assert set(layer.tobytes()) <= {0, 255}


def test_empty_and_oversized_lines_are_rejected():
    with pytest.raises(ValueError):
        lettering.line_mask("", BOX_W, SLOT_H)
    with pytest.raises(ValueError):
        lettering.line_mask("A" * (lettering.MAX_LINE_CHARS + 1), BOX_W, SLOT_H)
    with pytest.raises(ValueError):
        lettering.paint_lines(pf.new_canvas(pf.IDX_WHITE, (100, 100)),
                              ["A", "B", "C", "D"], (0, 0, 100, 100), pf.IDX_BLACK)


def test_unsupported_glyphs_are_reported_so_callers_can_fall_back():
    assert lettering.supported_lines(["PARIS", "ORLY"])
    assert not lettering.supported_lines(["東京"])
    assert not lettering.supported_lines([])


def test_paint_uses_only_the_ink_index_without_a_band():
    canvas = pf.new_canvas(pf.IDX_WHITE, (BOX_W + 40, 500))
    lettering.paint_lines(canvas, ["NEW", "YORK"], (20, 20, BOX_W + 20, 480), pf.IDX_BLUE)
    assert {v for _c, v in canvas.getcolors()} == {pf.IDX_WHITE, pf.IDX_BLUE}


def test_two_tone_paint_splits_ink_and_field_shade_at_the_band():
    size = (BOX_W + 40, 500)
    canvas = pf.new_canvas(pf.IDX_WHITE, size)
    band = _band_canvas_mask(size)
    shade = pf.new_canvas(pf.IDX_YELLOW, size)
    lettering.paint_lines(canvas, ["OLD"], (20, 20, BOX_W + 20, 480), pf.IDX_BLACK,
                          band_mask=band, band_field_pattern=shade)
    split_x = size[0] // 2
    left = canvas.crop((0, 0, split_x, size[1]))
    right = canvas.crop((split_x, 0, size[0], size[1]))
    assert {v for _c, v in left.getcolors()} == {pf.IDX_WHITE, pf.IDX_YELLOW}
    assert {v for _c, v in right.getcolors()} == {pf.IDX_WHITE, pf.IDX_BLACK}


def test_accents_paint_above_the_slot_top():
    size = (BOX_W + 40, 600)
    canvas = pf.new_canvas(pf.IDX_WHITE, size)
    lettering.paint_lines(canvas, ["ÉTE"], (20, 200, BOX_W + 20, 200 + SLOT_H + LINE_GAP), pf.IDX_BLACK)
    above = canvas.crop((0, 0, size[0], 199))
    assert pf.IDX_BLACK in {v for _c, v in above.getcolors()}


LINE_GAP = lettering.LINE_GAP_PX


SMALL = (200, 200)


def _counts(img):
    return {v: c for c, v in img.getcolors()}


@pytest.mark.parametrize("pairing_id", ["grey", "blue_light", "red_light"])
def test_default_fields_dither_ink_with_white_and_keep_ink_dominant(pairing_id):
    pairing = PAIRINGS[pairing_id]
    ink = field.ink_index(pairing.field_ink)
    counts = _counts(field.field_pattern(pairing, SMALL))
    assert set(counts) == {ink, pf.IDX_WHITE}
    assert counts[ink] > counts[pf.IDX_WHITE]


def test_yellow_field_is_mostly_white_and_white_field_is_flat():
    counts = _counts(field.field_pattern(PAIRINGS["yellow_light"], SMALL))
    assert set(counts) == {pf.IDX_YELLOW, pf.IDX_WHITE}
    assert counts[pf.IDX_WHITE] > counts[pf.IDX_YELLOW]
    assert _counts(field.field_pattern(PAIRINGS["white"], SMALL)) == {pf.IDX_WHITE: 200 * 200}


def test_yellow_small_text_is_dithered_toward_black_others_are_flat():
    counts = _counts(field.small_text_ink_pattern(PAIRINGS["yellow_light"], SMALL))
    assert set(counts) == {pf.IDX_YELLOW, pf.IDX_BLACK}
    share = counts[pf.IDX_BLACK] / (SMALL[0] * SMALL[1])
    assert 0.35 < share < 0.55
    assert _counts(field.small_text_ink_pattern(PAIRINGS["blue_light"], SMALL)) == {pf.IDX_BLUE: 40000}
    assert _counts(field.small_text_ink_pattern(PAIRINGS["white"], SMALL)) == {pf.IDX_BLACK: 40000}


def test_small_text_pattern_is_a_fresh_copy():
    first = field.small_text_ink_pattern(PAIRINGS["yellow_light"], SMALL)
    first.paste(pf.IDX_RED, (0, 0, 50, 50))
    again = field.small_text_ink_pattern(PAIRINGS["yellow_light"], SMALL)
    assert pf.IDX_RED not in _counts(again)


def test_yellow_light_field_passes_the_giant_check_but_not_the_legacy_one():
    canvas = field.field_pattern(PAIRINGS["yellow_light"], SMALL)
    palette_check.assert_giant_palette(canvas, pf.IDX_YELLOW)
    with pytest.raises(AssertionError):
        layout._assert_legal_palette(canvas, pf.IDX_YELLOW)


@pytest.mark.parametrize("pairing_id", list(PAIRINGS))
def test_every_pairing_field_passes_the_giant_check(pairing_id):
    pairing = PAIRINGS[pairing_id]
    palette_check.assert_giant_palette(field.field_pattern(pairing, SMALL),
                                       field.ink_index(pairing.field_ink))


def test_out_of_palette_index_is_rejected():
    canvas = pf.new_canvas(pf.IDX_WHITE, (20, 20))
    canvas.paste(9, (0, 0, 5, 5))
    with pytest.raises(AssertionError, match="illegal"):
        palette_check.assert_giant_palette(canvas, pf.IDX_WHITE)


def test_dominant_index_must_be_field_ink_or_white():
    canvas = pf.new_canvas(pf.IDX_RED, (20, 20))
    with pytest.raises(AssertionError, match="dominant"):
        palette_check.assert_giant_palette(canvas, pf.IDX_BLUE)
