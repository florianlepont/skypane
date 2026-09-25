#!/usr/bin/env python3
"""Contract tests for server/panel_preview.py: proves
unpack_panel() is the exact inverse of panel_format.pack_panel() over a
full canvas containing all six legal palette indices (including a mixed
nibble pair inside one packed byte), that malformed input raises the
typed PanelDecodeError rather than crashing, that panel_png_bytes()
produces a real PNG with nearest-neighbour-only thumbnailing, and that a
real production render round-trips exactly.

Pillow is a hard dependency of every module under test, so this module
must be run under server/.venv's interpreter, not the bare system python3.
"""
import io
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PIL import Image, ImageDraw  # noqa: E402

import server.panel_format as panel_format  # noqa: E402
import server.panel_preview as panel_preview  # noqa: E402
import server.plane.render as render  # noqa: E402


def _draw_all_six_indices_canvas():
    """A full-canvas fixture painted in six horizontal bands, one per
    legal palette index (0-5), so every legal nibble code appears in the
    packed output - built in-process, no fixture file.
    """
    canvas = panel_format.new_canvas(panel_format.IDX_WHITE)
    draw = ImageDraw.Draw(canvas)
    indices = [
        panel_format.IDX_BLACK,
        panel_format.IDX_WHITE,
        panel_format.IDX_YELLOW,
        panel_format.IDX_RED,
        panel_format.IDX_BLUE,
        panel_format.IDX_GREEN,
    ]
    band_height = panel_format.HEIGHT // len(indices)
    for i, idx in enumerate(indices):
        top = i * band_height
        bottom = panel_format.HEIGHT if i == len(indices) - 1 else (i + 1) * band_height
        draw.rectangle([0, top, panel_format.WIDTH - 1, bottom - 1], fill=idx)
    return canvas


# --- Shared expensive fixtures ---------------------------------------------
# panel_png_bytes()/pack_panel() over the full 1200x1600 canvas are the
# slowest operations in this module; several tests below assert on
# different facets of the SAME deterministic output rather than each
# other's side effects, so a module-scoped fixture computes each shared
# artifact once instead of every test re-deriving it independently.


@pytest.fixture(scope="module")
def all_six_indices_raw():
    canvas = _draw_all_six_indices_canvas()
    return panel_format.pack_panel(canvas)


@pytest.fixture(scope="module")
def full_png_bytes(all_six_indices_raw):
    return panel_preview.panel_png_bytes(all_six_indices_raw)


@pytest.fixture(scope="module")
def thumb_png_bytes(all_six_indices_raw):
    return panel_preview.panel_png_bytes(all_six_indices_raw, max_width=240)


def test_a_drawn_canvas_packed_then_unpacked_yields_identical_per_pixel_index_data():
    canvas = panel_format.new_canvas(panel_format.IDX_WHITE)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([100, 100, 500, 900], fill=panel_format.IDX_BLUE)
    draw.rectangle([600, 200, 1100, 700], fill=panel_format.IDX_GREEN)
    raw = panel_format.pack_panel(canvas)
    unpacked = panel_preview.unpack_panel(raw)
    assert unpacked.mode == "P", "expected 'P' mode, got %r" % (unpacked.mode,)
    assert unpacked.size == (panel_format.WIDTH, panel_format.HEIGHT), (
        "expected size %r, got %r" % ((panel_format.WIDTH, panel_format.HEIGHT), unpacked.size)
    )
    original_data = list(canvas.getdata())
    unpacked_data = list(unpacked.getdata())
    assert unpacked_data == original_data, "unpacked index data does not match the original canvas, pixel-for-pixel"


def test_all_six_indices_with_mixed_pair_round_trips():
    """a canvas containing all six legal indices, including a mixed odd/even column pair, round-trips exactly."""
    canvas = _draw_all_six_indices_canvas()
    draw = ImageDraw.Draw(canvas)
    # Force an explicit mixed nibble pair: column 400 (even, left of a
    # packed byte) and column 401 (odd, right of the same packed byte)
    # get two different legal indices.
    draw.point((400, 10), fill=panel_format.IDX_RED)
    draw.point((401, 10), fill=panel_format.IDX_GREEN)
    raw = panel_format.pack_panel(canvas)
    unpacked = panel_preview.unpack_panel(raw)
    assert list(unpacked.getdata()) == list(canvas.getdata()), "round trip diverged on the all-six-indices canvas"


def test_wrong_length_raises_panel_decode_error():
    """unpack_panel() on wrong-length input raises PanelDecodeError, never AssertionError/IndexError."""
    with pytest.raises(panel_preview.PanelDecodeError):
        panel_preview.unpack_panel(b"\x00" * (panel_format.IMAGE_BYTES - 1))


def test_illegal_nibble_raises_panel_decode_error_naming_the_offending_code():
    raw = bytearray(panel_format.IMAGE_BYTES)
    raw[0] = 0x40  # high nibble 0x4 is illegal; low nibble 0x0 (black) is legal
    with pytest.raises(panel_preview.PanelDecodeError) as excinfo:
        panel_preview.unpack_panel(bytes(raw))
    message = str(excinfo.value)
    assert "0x4" in message or "4" in message, "PanelDecodeError message does not name the illegal code: %r" % (message,)


def test_panel_png_bytes_is_a_real_pillow_decodable_png_at_the_expected_dimensions(full_png_bytes):
    assert isinstance(full_png_bytes, bytes), "expected bytes, got %r" % (type(full_png_bytes),)
    png_signature = b"\x89PNG\r\n\x1a\n"
    assert full_png_bytes[:8] == png_signature, "first 8 bytes are not the PNG signature: %r" % (full_png_bytes[:8],)
    decoded = Image.open(io.BytesIO(full_png_bytes))
    decoded.load()
    assert decoded.size == (panel_format.WIDTH, panel_format.HEIGHT), (
        "decoded PNG size %r != expected %r" % (decoded.size, (panel_format.WIDTH, panel_format.HEIGHT))
    )


def test_thumbnail_is_proportionally_resized(thumb_png_bytes):
    decoded = Image.open(io.BytesIO(thumb_png_bytes))
    decoded.load()
    expected_height = round(panel_format.HEIGHT * (240 / float(panel_format.WIDTH)))
    assert decoded.width == 240, "expected thumbnail width 240, got %d" % (decoded.width,)
    assert abs(decoded.height - expected_height) <= 1, (
        "expected thumbnail height ~%d, got %d" % (expected_height, decoded.height)
    )


def test_read_panel_file_on_a_missing_file_returns_none_rather_than_raising():
    result = panel_preview.read_panel_file("/nonexistent/skypane-panel-preview-test-dir")
    assert result is None, "expected None on a missing panel file, got %r" % (result,)


def test_mixed_pair_catches_nibble_transposition():
    """a row with two different legal indices at column 0 and column 1 round-trips without a high/low nibble swap."""
    # A transposition bug would round-trip a uniform canvas perfectly and
    # only show up on a mixed pair, so this is the test that actually
    # catches it.
    canvas = panel_format.new_canvas(panel_format.IDX_BLACK)
    draw = ImageDraw.Draw(canvas)
    # Column 0 (left/high nibble) and column 1 (right/low nibble) of row 5
    # get two distinct legal indices.
    draw.point((0, 5), fill=panel_format.IDX_YELLOW)
    draw.point((1, 5), fill=panel_format.IDX_RED)
    raw = panel_format.pack_panel(canvas)
    unpacked = panel_preview.unpack_panel(raw)
    left = unpacked.getpixel((0, 5))
    right = unpacked.getpixel((1, 5))
    assert (left, right) == (panel_format.IDX_YELLOW, panel_format.IDX_RED), (
        "expected (yellow, red) at (col0, col1) of row 5, got (%r, %r)" % (left, right)
    )


def test_full_getdata_sequence_matches_over_all_six_indices():
    """the full getdata() sequence (not a sampled subset) matches exactly for an all-six-indices canvas."""
    canvas = _draw_all_six_indices_canvas()
    raw = panel_format.pack_panel(canvas)
    unpacked = panel_preview.unpack_panel(raw)
    original_data = list(canvas.getdata())
    unpacked_data = list(unpacked.getdata())
    assert len(unpacked_data) == panel_format.WIDTH * panel_format.HEIGHT, (
        "unpacked getdata() length %d != expected %d" % (len(unpacked_data), panel_format.WIDTH * panel_format.HEIGHT)
    )
    if unpacked_data != original_data:
        mismatches = sum(1 for a, b in zip(original_data, unpacked_data) if a != b)
        pytest.fail("%d of %d pixels mismatched over the full getdata() sequence" % (mismatches, len(original_data)))


def test_production_render_round_trips_exactly_against_build_canvas():
    """a real production render.render_panel(None, 'empty') round-trips index-for-index against build_canvas()."""
    raw = render.render_panel(None, "empty")
    unpacked = panel_preview.unpack_panel(raw)
    expected_canvas = render.build_canvas(None, "empty")
    assert list(unpacked.getdata()) == list(expected_canvas.getdata()), (
        "production render_panel(None, 'empty') round trip diverged from build_canvas(None, 'empty')"
    )


def test_thumbnail_colour_set_is_a_strict_subset_of_the_full_images_colour_set(full_png_bytes, thumb_png_bytes):
    full_decoded = Image.open(io.BytesIO(full_png_bytes))
    full_decoded.load()
    thumb_decoded = Image.open(io.BytesIO(thumb_png_bytes))
    thumb_decoded.load()
    full_colours = {rgb for _count, rgb in full_decoded.getcolors(maxcolors=1000)}
    thumb_colours = {rgb for _count, rgb in thumb_decoded.getcolors(maxcolors=1000)}
    extra = thumb_colours - full_colours
    assert not extra, "thumbnail introduced colours not present in the full image: %r" % (extra,)

