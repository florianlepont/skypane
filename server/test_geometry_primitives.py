"""Size-aware canvas, packing and dithered-background primitives."""
import subprocess
import sys

import pytest

from server import panel_format as pf
from server.plane import dither


def test_default_canvas_is_legacy_size():
    assert pf.new_canvas(pf.IDX_WHITE).size == (1200, 1600)


def test_sized_canvas_and_pack_lengths():
    small = pf.new_canvas(pf.IDX_WHITE, size=(800, 480))
    assert small.size == (800, 480)
    assert len(pf.pack_panel(small)) == 192000
    assert len(pf.pack_panel(pf.new_canvas(pf.IDX_WHITE))) == 960000


def test_pack_nibbles_left_pixel_high():
    canvas = pf.new_canvas(pf.IDX_BLACK, size=(4, 2))
    canvas.putpixel((1, 0), pf.IDX_WHITE)
    assert pf.pack_panel(canvas)[0] == 0x01


def test_odd_width_rejected():
    with pytest.raises(ValueError):
        pf.pack_panel(pf.new_canvas(pf.IDX_WHITE, size=(5, 4)))


def _default_bytes():
    return dither.dithered_state_background(pf.IDX_BLUE).tobytes()


def test_dither_cache_mixed_sizes_both_orders():
    code = (
        "import sys\n"
        "from server import panel_format as pf\n"
        "from server.plane import dither\n"
        "if sys.argv[1] == 'small_first':\n"
        "    dither.dithered_state_background(pf.IDX_BLUE, size=(800, 480))\n"
        "img = dither.dithered_state_background(pf.IDX_BLUE)\n"
        "assert img.size == (1200, 1600)\n"
        "if sys.argv[1] == 'default_first':\n"
        "    assert dither.dithered_state_background(pf.IDX_BLUE, size=(800, 480)).size == (800, 480)\n"
        "sys.stdout.buffer.write(__import__('hashlib').sha256(img.tobytes()).digest())\n"
    )
    outs = [
        subprocess.run(
            [sys.executable, "-c", code, order], check=True, capture_output=True
        ).stdout
        for order in ("small_first", "default_first")
    ]
    assert outs[0] == outs[1]


def test_sized_background_in_process_does_not_poison_default():
    small = dither.dithered_state_background(pf.IDX_GREEN, size=(800, 480))
    assert small.size == (800, 480)
    assert dither.dithered_state_background(pf.IDX_GREEN).size == (1200, 1600)
