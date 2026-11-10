"""Photo render path: panel sizes, fit modes, determinism."""

import io

import pytest
from PIL import Image, ImageOps

from photo_scenes import (
    RED, corner_markers, face_scene, left_right, to_stored_jpeg, top_bottom,
)
from server import hardware, image_container
from server import panel_format as pf
from server.photo.crop import FitSetting
from server.photo.prep import DEFAULT_PREP, prepare
from server.plane.dither import dither_to_full_panel_palette
from server.photo.render import (
    BAND_INDEX, preview_png, render_photo, render_photo_packed,
)

PORTRAIT = hardware.get_profile(hardware.LEGACY_KEY)
LANDSCAPE = hardware.get_profile(
    hardware.SIM_LANDSCAPE_KEY, {hardware.SIM_ENV_VAR: "1"})
SIZES = [(PORTRAIT.width, PORTRAIT.height), (LANDSCAPE.width, LANDSCAPE.height)]
PALETTE_INDICES = set(range(len(pf.PALETTE_RGB) // 3))


def _stored():
    return to_stored_jpeg(corner_markers((600, 400)))


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("mode", ["fill", "bands"])
def test_render_panel_sizes_palette_only(size, mode):
    out = render_photo(_stored(), size, FitSetting(mode=mode))
    assert out.mode == "P"
    assert out.size == size
    assert set(out.tobytes()) <= PALETTE_INDICES


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("mode", ["fill", "bands"])
def test_packed_length_and_nibbles(size, mode):
    packed = render_photo_packed(_stored(), size, FitSetting(mode=mode))
    assert len(packed) == size[0] // 2 * size[1]
    nibbles = set(pf.INDEX_TO_NIBBLE.values())
    assert {b >> 4 for b in packed} <= nibbles
    assert {b & 0xF for b in packed} <= nibbles


def test_container_round_trip_portrait():
    w, h = PORTRAIT.width, PORTRAIT.height
    packed = render_photo_packed(_stored(), (w, h))
    view = image_container.decode_container(
        image_container.encode_container(packed, w, h), w, h)
    assert view.payload == packed
    assert view.legacy is False
    assert (view.width, view.height) == (w, h)


def test_sim_landscape_profile_maps_to_800x480(monkeypatch):
    monkeypatch.delenv(hardware.SIM_ENV_VAR, raising=False)
    assert hardware.SIM_LANDSCAPE_KEY not in hardware.available_types()
    profile = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY, {hardware.SIM_ENV_VAR: "1"})
    assert (profile.width, profile.height) == (800, 480)
    assert hardware.get_profile(hardware.LEGACY_KEY).width == hardware.PORTRAIT_SIZE[0]
    assert hardware.get_profile(hardware.LEGACY_KEY).height == hardware.PORTRAIT_SIZE[1]
    out = render_photo(_stored(), (profile.width, profile.height))
    assert out.mode == "P"
    assert out.size == (profile.width, profile.height)


def test_render_is_deterministic_and_leaves_input_alone():
    stored = _stored()
    copy = bytes(stored)
    a = render_photo(stored, SIZES[0])
    b = render_photo(stored, SIZES[0])
    assert a.tobytes() == b.tobytes()
    assert stored == copy


def _share(img, box, colour_idx):
    data = img.crop(box).tobytes()
    return data.count(colour_idx) / max(1, len(data))


def test_fill_crop_position_moves_portrait_window():
    stored = to_stored_jpeg(left_right((400, 400)))
    w, h = SIZES[0]
    outs = [render_photo(stored, (w, h), FitSetting(pos_x=p)) for p in (0.0, 0.5, 1.0)]
    assert len({o.tobytes() for o in outs}) == 3
    red_idx = _dominant(outs[0].crop((0, 0, 100, 100)))
    blue_idx = _dominant(outs[2].crop((w - 100, 0, w, 100)))
    assert red_idx != blue_idx
    # The window is 3/4 of the square source wide: red covers 2/3 of it at
    # pos 0, 1/2 at pos 0.5 and 1/3 at pos 1.
    shares = [_share(o, (0, 0, w, h), red_idx) for o in outs]
    assert shares[0] > 0.6 > shares[1] + 0.05
    assert shares[1] > 0.4
    assert shares[2] < 0.4
    assert _share(outs[2], (0, 0, w, h), blue_idx) > 0.6


def _dominant(img):
    data = img.tobytes()
    return max(set(data), key=data.count)


def test_fill_crop_position_uses_pos_y_for_landscape():
    stored = to_stored_jpeg(top_bottom((400, 400)))
    size = SIZES[1]
    top = render_photo(stored, size, FitSetting(pos_y=0.0))
    bottom = render_photo(stored, size, FitSetting(pos_y=1.0))
    assert top.tobytes() != bottom.tobytes()
    assert _dominant(top) != _dominant(bottom)
    assert render_photo(stored, size, FitSetting(pos_x=0.0)).tobytes() == render_photo(
        stored, size, FitSetting(pos_x=1.0)).tobytes()


@pytest.mark.parametrize("size", SIZES)
def test_bands_show_whole_photo_with_exact_white_bands(size):
    src = corner_markers((600, 400))
    stored = to_stored_jpeg(src)
    out = render_photo(stored, size, FitSetting(mode="bands"))
    inner = ImageOps.contain(Image.open(io.BytesIO(stored)), size, Image.Resampling.LANCZOS)
    left = (size[0] - inner.width) // 2
    top = (size[1] - inner.height) // 2
    area = (left, top, left + inner.width, top + inner.height)
    # Everything outside the photo area is exactly the band colour.
    assert BAND_INDEX == pf.IDX_WHITE
    mask = Image.new("L", size, 255)
    mask.paste(0, area)
    outside = Image.composite(out, Image.new("P", size, BAND_INDEX), mask)
    assert set(outside.tobytes()) <= {BAND_INDEX}
    # All four corner markers are visible at the corners of the photo area.
    m = 6
    corners = (
        ((area[0] + 2, area[1] + 2), pf.IDX_RED),
        ((area[2] - m - 2, area[1] + 2), pf.IDX_GREEN),
        ((area[0] + 2, area[3] - m - 2), pf.IDX_BLUE),
        ((area[2] - m - 2, area[3] - m - 2), pf.IDX_YELLOW),
    )
    for (cx, cy), expected in corners:
        assert _dominant(out.crop((cx, cy, cx + m, cy + m))) == expected


def test_bands_ignore_crop_position():
    stored = _stored()
    size = SIZES[0]
    a = render_photo(stored, size, FitSetting(mode="bands", pos_x=0.0, pos_y=0.0))
    b = render_photo(stored, size, FitSetting(mode="bands", pos_x=1.0, pos_y=1.0))
    assert a.tobytes() == b.tobytes()


def test_bands_prep_histogram_comes_from_photo_area_only():
    scene, _ = face_scene("III", dull=True, size=(300, 400))
    stored = to_stored_jpeg(scene)
    size = SIZES[1]
    out = render_photo(stored, size, FitSetting(mode="bands"))
    inner = ImageOps.contain(
        Image.open(io.BytesIO(stored)).convert("RGB"), size, Image.Resampling.LANCZOS)
    expected = dither_to_full_panel_palette(prepare(inner, DEFAULT_PREP))
    left = (size[0] - inner.width) // 2
    top = (size[1] - inner.height) // 2
    area = (left, top, left + inner.width, top + inner.height)
    assert out.crop(area).tobytes() == expected.tobytes()


@pytest.mark.parametrize("size", [(0, 100), (101, 100), (100, 0), (-2, 100), (2402, 100), (100, 2401)])
def test_invalid_size_raises(size):
    with pytest.raises(ValueError):
        render_photo(_stored(), size)


@pytest.mark.parametrize("data", [b"", b"not an image", b"\x89PNG\r\n\x1a\n" + b"\0" * 20])
def test_undecodable_stored_copy_raises(data):
    with pytest.raises(ValueError):
        render_photo(data, SIZES[1])


def test_png_stored_copy_is_rejected():
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), RED).save(buf, "PNG")
    with pytest.raises(ValueError):
        render_photo(buf.getvalue(), SIZES[1])


def test_preview_png_round_trips():
    out = render_photo(_stored(), SIZES[1])
    png = Image.open(io.BytesIO(preview_png(out)))
    assert png.format == "PNG"
    assert png.size == out.size
    assert png.tobytes() == out.tobytes()
