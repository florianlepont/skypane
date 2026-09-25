#!/usr/bin/env python3
"""The mathematical inverse of `panel_format.pack_panel()`, plus a PNG
encoder that turns the live `state_dir/panel.bin` into bytes an HTTP
handler can write directly.

No production caller currently - kept on disk as tested infrastructure
(`test_panel_preview.py`). Unlike `render.py --preview` (a hardcoded
sample flight), this unpacks the literal bytes `poll_loop.py` wrote to
`panel.bin` - the only source of truth for what the frame is displaying.

Colour caveat: `panel_format.PALETTE_RGB` is a nominal, render-internal
swatch, not colour-accurate against real Spectra 6 glass - the *indices*
are faithfully reproduced (round-trip proven), the RGB is not.

Imported inside an HTTP request handler: never writes to stdout or the
filesystem (a stray file write could race the poll pipeline that owns
`panel.bin`).
"""
import datetime
import io
import os
import sys

# Allow both package import and direct execution, matching
# server/poll_loop.py's own bootstrap.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PIL import Image

from server import panel_format

# Derived by inverting panel_format.INDEX_TO_NIBBLE, never retyped, so a
# future palette change keeps this in sync automatically.
NIBBLE_TO_INDEX = {nibble: index for index, nibble in panel_format.INDEX_TO_NIBBLE.items()}


class PanelDecodeError(ValueError):
    """Wrong length or an illegal nibble code. Always this one typed
    exception, so the HTTP layer can catch a single type.
    """


def unpack_panel(raw_bytes):
    """The exact inverse of panel_format.pack_panel(). Returns a "P"-mode
    Image with panel_format's palette applied; callers needing colour
    call .convert("RGB") themselves so the round-trip check can compare
    index data directly.
    """
    expected = panel_format.IMAGE_BYTES
    actual = len(raw_bytes)
    if actual != expected:
        raise PanelDecodeError(
            "panel data is %d bytes, expected %d" % (actual, expected)
        )

    width = panel_format.WIDTH
    height = panel_format.HEIGHT
    row_bytes = panel_format.ROW_BYTES

    indices = bytearray(width * height)
    for row in range(height):
        obase = row * row_bytes
        base = row * width
        for col in range(0, width, 2):
            offset = obase + col // 2
            byte_val = raw_bytes[offset]
            left_nibble = (byte_val >> 4) & 0xF
            right_nibble = byte_val & 0xF
            if left_nibble not in NIBBLE_TO_INDEX:
                raise PanelDecodeError(
                    "illegal nibble code 0x%X at byte offset %d" % (left_nibble, offset)
                )
            if right_nibble not in NIBBLE_TO_INDEX:
                raise PanelDecodeError(
                    "illegal nibble code 0x%X at byte offset %d" % (right_nibble, offset)
                )
            indices[base + col] = NIBBLE_TO_INDEX[left_nibble]
            indices[base + col + 1] = NIBBLE_TO_INDEX[right_nibble]

    image = Image.new("P", (width, height))
    image.putpalette(panel_format.padded_palette())
    image.putdata(bytes(indices))
    return image


def panel_png_bytes(raw_bytes, max_width=None):
    """Unpack `raw_bytes`, convert to RGB, optionally resize to
    `max_width` (nearest-neighbour, required - any smoothing would blend
    the six flat panel colours into values that don't exist on the
    device), return PNG bytes.
    """
    image = unpack_panel(raw_bytes).convert("RGB")
    if max_width is not None and image.width > max_width:
        ratio = max_width / float(image.width)
        new_size = (max_width, max(1, round(image.height * ratio)))
        image = image.resize(new_size, resample=Image.NEAREST)
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def read_panel_file(state_dir):
    """Read `panel.bin` from `state_dir` in binary, or None on any
    OSError. Does not validate length - that's unpack_panel()'s job.
    """
    path = os.path.join(state_dir, "panel.bin")
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def panel_file_mtime_iso(state_dir):
    """panel.bin's mtime as a UTC ISO-8601 second-precision string, or
    None if missing.
    """
    path = os.path.join(state_dir, "panel.bin")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    return datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
