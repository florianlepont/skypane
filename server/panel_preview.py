#!/usr/bin/env python3
"""The mathematical inverse of `panel_format.pack_panel()`, plus a PNG
encoder that turns the live `state_dir/panel.bin` into bytes an HTTP
handler can write directly (CFG-10).

This module exists because `server/plane/render.py`'s `--preview` CLI flag
renders a hardcoded sample flight - it cannot answer "what is on the panel
right now" (06-RESEARCH.md Pattern 4 and its Anti-Patterns list explicitly
reject wrapping `render.py --preview` for this purpose). The only source of
truth for what the physical frame is currently displaying is the literal
960,000 packed bytes that `poll_loop.py`'s `write_panel_atomic()` writes to
`state_dir/panel.bin` and that `byos_server.py` serves to the device
verbatim - so this module unpacks exactly those bytes instead.

Colour accuracy caveat (D-P2-03): the RGB values `panel_png_bytes()`
produces come from `panel_format.PALETTE_RGB`, which D-P2-03 defines as
nominal, render-internal swatch colours - not colour-accurate against real
Spectra 6 glass. This module faithfully reproduces the *indices* on the
wire (proven by the round-trip harness in `test_panel_preview.py`), but the
resulting PNG is an index-accurate preview, not a colour-accurate one.
Plan 06-09's Preview page surfaces this same caveat as caption copy.

This module is imported inside an HTTP request handler: it emits nothing
to standard output and never writes to the filesystem (a stray console
write would pollute the service journal; a stray file write could race the
poll pipeline that owns `panel.bin`).
"""
import datetime
import io
import os
import sys

# Allow both `import server.panel_preview` (package import) and direct
# script execution, matching server/poll_loop.py's own bootstrap
# (poll_loop.py lines 31-38): sys.path[0] is server/ itself when this file
# is executed directly, so the repo root must be added by hand before the
# absolute `server.panel_format` import below can resolve.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PIL import Image

from server import panel_format

# The single source of truth for nibble<->index mapping: derived by
# inverting panel_format.INDEX_TO_NIBBLE, never by retyping the six pairs.
# This one derivation is what makes silent drift between pack_panel() and
# unpack_panel() impossible (T-06-03-02) - a future palette change that
# edits INDEX_TO_NIBBLE automatically keeps this in sync.
NIBBLE_TO_INDEX = {nibble: index for index, nibble in panel_format.INDEX_TO_NIBBLE.items()}


class PanelDecodeError(ValueError):
    """Raised when raw panel bytes cannot be turned into an image - wrong
    length or an illegal nibble code. Always this one typed exception,
    never AssertionError/IndexError, so the HTTP layer can catch a single
    type and return 06-UI-SPEC.md's "temporarily unavailable" copy instead
    of faulting on an unhandled exception (T-06-03-01).
    """


def unpack_panel(raw_bytes):
    """The exact inverse of panel_format.pack_panel(): walk the same
    row/column-pair loop in reverse, splitting each byte's high nibble
    (left pixel) and low nibble (right pixel) back into palette indices.
    Returns a "P"-mode (WIDTH x HEIGHT) Image with panel_format's palette
    already applied - callers needing colour call .convert("RGB")
    themselves so the round-trip check can compare index data directly.
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
    `max_width` (preserving aspect ratio, nearest-neighbour resampling -
    required, not a preference, since any smoothing filter would blend the
    six flat panel colours into intermediate values that do not exist on
    the device), and return real PNG bytes ready for an HTTP handler to
    write directly.
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
    """Read `panel.bin` from `state_dir` in binary. Returns None on any
    OSError (missing file, permission error, ...) rather than raising, so
    the caller can distinguish "no panel yet" (this function) from "panel
    present but unreadable/malformed" (unpack_panel()'s job - this
    function deliberately does not validate length).
    """
    path = os.path.join(state_dir, "panel.bin")
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def panel_file_mtime_iso(state_dir):
    """Return panel.bin's modification time as a timezone-aware UTC
    ISO-8601 second-precision string ("YYYY-MM-DDTHH:MM:SSZ"), or None
    when the file is missing. This is the Preview page's caption
    timestamp.
    """
    path = os.path.join(state_dir, "panel.bin")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    return datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
