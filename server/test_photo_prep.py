"""FitSetting and PrepParams validation, and the default pre-processing."""

import colorsys
import math

import pytest
from PIL import Image, ImageStat

from photo_scenes import SKIN_TONES, face_scene, skin_swatch
from server import panel_format as pf
from server.photo.crop import FitSetting
from server.photo.prep import DEFAULT_PREP, PrepParams, prepare
from server.plane.dither import dither_to_full_panel_palette


def test_fitsetting_defaults():
    fit = FitSetting()
    assert (fit.mode, fit.pos_x, fit.pos_y) == ("fill", 0.5, 0.5)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pos_x": float("nan")},
        {"pos_y": float("nan")},
        {"pos_x": float("inf")},
        {"pos_y": float("-inf")},
        {"pos_x": -0.1},
        {"pos_y": 1.1},
        {"mode": "stretch"},
        {"pos_x": "0.5"},
    ],
)
def test_fitsetting_rejects_invalid(kwargs):
    with pytest.raises(ValueError):
        FitSetting(**kwargs)


def test_fitsetting_rounds_to_four_decimals():
    assert FitSetting(pos_x=0.12345, pos_y=0.99999).pos_x == 0.1235
    assert FitSetting(pos_x=0.12345, pos_y=0.99999).pos_y == 1.0


def test_prepparams_rejects_saturation_above_ceiling():
    PrepParams(1.0, 0.8, 1.3)
    with pytest.raises(ValueError):
        PrepParams(1.0, 0.8, 1.31)
    with pytest.raises(ValueError):
        PrepParams(1.0, 1.5, 1.0)
    with pytest.raises(ValueError):
        PrepParams(math.nan, 0.8, 1.0)


def test_default_prep_defaults_pinned():
    assert (DEFAULT_PREP.cutoff, DEFAULT_PREP.strength, DEFAULT_PREP.saturation) == (
        1.0,
        0.8,
        1.2,
    )


def _hue_degrees(rgb):
    h, _, _ = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    return h * 360


def _mean_rgb(img, box=None):
    region = img.crop(box) if box else img
    return tuple(ImageStat.Stat(region).mean)


@pytest.mark.parametrize("tone", list(SKIN_TONES))
def test_prepare_preserves_hue_per_tone(tone):
    scene, box = face_scene(tone)
    before = _hue_degrees(_mean_rgb(scene, box))
    after = _hue_degrees(_mean_rgb(prepare(scene, DEFAULT_PREP), box))
    delta = abs(before - after)
    assert min(delta, 360 - delta) <= 6


def test_prepare_keeps_size_and_mode():
    img = skin_swatch("III", (50, 30))
    out = prepare(img, DEFAULT_PREP)
    assert out.size == (50, 30)
    assert out.mode == "RGB"


@pytest.mark.parametrize("tone", ["I", "II", "III", "IV", "V"])
def test_skin_region_not_flat_index_tones_i_to_v(tone):
    scene, box = face_scene(tone)
    dithered = dither_to_full_panel_palette(prepare(scene, DEFAULT_PREP))
    assert dithered.mode == "P"
    indices = set(dithered.crop(box).tobytes())
    assert len(indices) > 1
    assert indices <= set(range(len(pf.PALETTE_RGB) // 3))
    assert isinstance(dithered, Image.Image)
