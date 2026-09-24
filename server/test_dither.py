#!/usr/bin/env python3
"""Contract tests for server/plane/dither.py's full-6-color palette dither
helper (D-25/D-26, PLANE-01/PLANE-02).

dither.py transitively imports Pillow, so this module must be run under
server/.venv's interpreter, not the bare system python3.

Phase 3 D-21 (03-CONTEXT.md): this module's earlier two-tone dithered
"mood background" (`build_mood_background()`, D-17/D-18) was retired when
the active-state background became a flat single-color fill - this module
no longer tests it. Only `panel_palette_image()`/`dither_to_full_panel_palette()`
survive, now reused by render.py's real-illustration compositing path.

Note: Pillow's Image.getcolors() returns (count, value) pairs - count
first, value second.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PIL import Image  # noqa: E402

from server import panel_format as pf  # noqa: E402
from server.plane import dither  # noqa: E402


def _index_set(canvas):
    return {value for _count, value in canvas.getcolors()}


def test_panel_palette_image_is_unpadded():
    """panel_palette_image() carries exactly PALETTE_RGB's 6 entries, unpadded."""
    # 03-RESEARCH.md Pitfall 2: a zero-padded filler entry (padded to 256)
    # can win nearest-neighbour matching for near-black source pixels.
    img = dither.panel_palette_image()
    palette = img.getpalette()
    expected = list(pf.PALETTE_RGB)
    assert palette == expected, (
        "panel_palette_image()'s palette is %r, expected exactly PALETTE_RGB %r (unpadded)" % (palette, expected)
    )


def test_full_palette_dither_stays_within_legal_indices():
    """dither_to_full_panel_palette() on a hue-rich synthetic image yields indices that are a subset of {0,1,2,3,4,5}."""
    hue_rich = Image.new("RGB", (64, 64))
    pixels = hue_rich.load()
    for y in range(64):
        for x in range(64):
            pixels[x, y] = (x * 4 % 256, y * 4 % 256, (x + y) * 2 % 256)
    quantized = dither.dither_to_full_panel_palette(hue_rich)
    idx_set = _index_set(quantized)
    assert idx_set.issubset({0, 1, 2, 3, 4, 5}), (
        "dither_to_full_panel_palette() produced out-of-range indices: %r" % (idx_set,)
    )


def test_flat_source_quantizes_to_single_index():
    """a flat single-color RGB source quantizes to exactly that color's own index."""
    # The nearest-neighbour match must be exact for an already-legal color,
    # not smeared across neighbours by dithering noise.
    flat = Image.new("RGB", (16, 16), tuple(pf.PALETTE_RGB[pf.IDX_RED * 3 : pf.IDX_RED * 3 + 3]))
    quantized = dither.dither_to_full_panel_palette(flat)
    idx_set = _index_set(quantized)
    assert idx_set == {pf.IDX_RED}, (
        "flat Red-colored source quantized to index set %r, expected {IDX_RED}" % (idx_set,)
    )


def test_dither_to_full_panel_palette_is_deterministic_for_the_same_input_image():
    hue_rich = Image.new("RGB", (32, 32))
    pixels = hue_rich.load()
    for y in range(32):
        for x in range(32):
            pixels[x, y] = (x * 8 % 256, y * 8 % 256, 128)
    first = dither.dither_to_full_panel_palette(hue_rich).tobytes()
    second = dither.dither_to_full_panel_palette(hue_rich).tobytes()
    assert first == second, "two dither_to_full_panel_palette() calls on the same input produced different bytes"


def test_calibration_preview_writes_exactly_one_palette_swatch_png_and_returns_its_path(tmp_path):
    paths = dither.write_calibration_preview(str(tmp_path))
    assert len(paths) == 1, "write_calibration_preview() returned %d paths, expected 1: %r" % (len(paths), paths)
    path = paths[0]
    assert os.path.isfile(path), "write_calibration_preview() reported %r but it does not exist on disk" % (path,)
    assert path.lower().endswith(".png"), "write_calibration_preview() reported a non-PNG path: %r" % (path,)


def test_build_mood_background_no_longer_exists_on_server_plane_dither():
    """build_mood_background() no longer exists on server.plane.dither (D-21 retirement)."""
    # A live-drift check that the D-21 retirement was actually completed,
    # not just intended.
    assert not hasattr(dither, "build_mood_background"), (
        "dither.build_mood_background() still exists - D-21 retired it, this must be dead code left behind"
    )

