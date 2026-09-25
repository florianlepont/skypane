"""Single source of truth for the Spectra 6 panel byte format and palette.

Duplicates (never imports) stub-server/make_test_panel.py's WIDTH/HEIGHT/
ROW_BYTES/IMAGE_BYTES and nibble codes, since stub-server/ is device-facing
and importing it here would invert the dependency. Both encode
docs/PROTOCOL.md section 1's wire format; PROTOCOL.md is the tiebreaker
if they ever drift.
"""

WIDTH = 1200
HEIGHT = 1600
ROW_BYTES = WIDTH // 2  # 600
IMAGE_BYTES = ROW_BYTES * HEIGHT  # 960000

# The six legal Spectra 6 nibble codes, packed two per byte on the wire.
BLACK = 0x0
WHITE = 0x1
YELLOW = 0x2
RED = 0x3
BLUE = 0x5
GREEN = 0x6

# --- Pillow palette bridge -------------------------------------------------
#
# Render-internal only - approximate swatch colors for Pillow's "P"-mode
# palette and the optional preview PNG. Never cross the wire; the device
# only ever sees the INDEX_TO_NIBBLE nibble codes above.
#
# Yellow/red (2/3) are a low-confidence community estimate. Blue/green
# (4/5) were darkened after a real on-glass photo showed the actual ink
# is more muted than any monitor preview - still approximate, no
# colorimeter used.
PALETTE_RGB = [
    0, 0, 0,        # black
    255, 255, 255,  # white
    240, 224, 80,   # yellow (interim, on-glass confirmed)
    160, 32, 32,    # red (interim, on-glass confirmed)
    45, 95, 155,    # blue (darkened from (70,125,185) - real ink more muted)
    50, 105, 65,    # green (darkened from (80,140,95) - real ink more muted)
]

# Bridges Pillow's contiguous "P"-mode indices to the wire format's
# non-contiguous nibble codes (0x4 is skipped).
INDEX_TO_NIBBLE = {0: BLACK, 1: WHITE, 2: YELLOW, 3: RED, 4: BLUE, 5: GREEN}

# Named so no drawing code in render.py writes a bare palette integer.
IDX_BLACK = 0
IDX_WHITE = 1
IDX_YELLOW = 2
IDX_RED = 3
IDX_BLUE = 4
IDX_GREEN = 5

_PALETTE_SIZE = 256

# Built from INDEX_TO_NIBBLE at import time for pack_panel()'s vectorised
# path. An unknown index maps to nibble 0 rather than raising - safe,
# since render.py already rejects an illegal index before this runs.
_HIGH_NIBBLE_TABLE = bytes(INDEX_TO_NIBBLE.get(i, 0) << 4 for i in range(256))
_LOW_NIBBLE_TABLE = bytes(INDEX_TO_NIBBLE.get(i, 0) for i in range(256))


def padded_palette():
    """The 768-int (256 * 3) zero-padded RGB palette Pillow's "P"-mode
    putpalette() expects, built from PALETTE_RGB.
    """
    return list(PALETTE_RGB) + [0, 0, 0] * (_PALETTE_SIZE - len(PALETTE_RGB) // 3)


def new_canvas(bg_index):
    """A fresh "P"-mode (1200x1600) canvas, palette applied, filled with
    bg_index. Draw with integer palette-index fills, never RGB.
    """
    from PIL import Image

    canvas = Image.new("P", (WIDTH, HEIGHT), color=bg_index)
    canvas.putpalette(padded_palette())
    return canvas


def pack_panel(canvas):
    """Pack a "P"-mode (1200x1600) canvas into the exact 960,000-byte
    docs/PROTOCOL.md section 1 wire format: 1600 rows x 600 bytes, 2 px
    per byte, left pixel in the high nibble.

    Vectorised (~0.085s -> ~0.003s per panel): translate() maps every
    even/odd-offset byte through the nibble tables in C, and the combine
    step ORs two big-endian integers rather than looping per byte - safe
    because a palette-index byte's high-nibble bits (0xF0) never overlap
    the low-nibble bits (0x0F) of its pair, so no bit ever carries between
    output bytes.
    """
    raw = canvas.tobytes()
    assert len(raw) == WIDTH * HEIGHT
    hi = raw[0::2].translate(_HIGH_NIBBLE_TABLE)
    lo = raw[1::2].translate(_LOW_NIBBLE_TABLE)
    out = (int.from_bytes(hi, "big") | int.from_bytes(lo, "big")).to_bytes(len(hi), "big")
    assert len(out) == IMAGE_BYTES
    return out
