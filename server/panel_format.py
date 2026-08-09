"""Single source of truth for the Spectra 6 panel byte format and palette.

This module and stub-server/make_test_panel.py must agree on WIDTH/HEIGHT/
ROW_BYTES/IMAGE_BYTES and the six nibble codes - both encode the exact same
docs/PROTOCOL.md section 1 wire format. stub-server/ is deliberately NOT
imported from server/ here (the dependency direction would be backwards -
stub-server/ is Phase 1's vendored device-facing reference server, server/
is Phase 2's real rendering pipeline); the constants are duplicated instead,
per 02-PATTERNS.md's explicit planner-discretion call. If either file's
values ever drift, PROTOCOL.md is the tiebreaker.
"""

WIDTH = 1200
HEIGHT = 1600
ROW_BYTES = WIDTH // 2  # 600
IMAGE_BYTES = ROW_BYTES * HEIGHT  # 960000

# The six legal Spectra 6 nibble codes (docs/PROTOCOL.md section 1) - the
# only values that may ever appear, packed two per byte, on the wire.
BLACK = 0x0
WHITE = 0x1
YELLOW = 0x2
RED = 0x3
BLUE = 0x5
GREEN = 0x6

# --- Pillow palette bridge -------------------------------------------------
#
# D-P2-03 (locked, 02-01-PLAN.md): these sRGB triples are render-internal
# only - nominal, approximate swatch colors that exist purely so Pillow's
# "P"-mode ImageDraw has a palette to attach to, and so an optional
# developer preview PNG (render.py --preview) is viewable on a normal
# monitor. They NEVER cross the wire to the device. What the device
# receives is exclusively the INDEX_TO_NIBBLE-mapped nibble codes above.
# Real panel colour fidelity is verified on glass in plan 02-05, not here.
PALETTE_RGB = [
    0, 0, 0,        # index 0 -> nibble 0x0 black
    255, 255, 255,  # index 1 -> nibble 0x1 white
    255, 255, 0,    # index 2 -> nibble 0x2 yellow
    255, 0, 0,      # index 3 -> nibble 0x3 red
    0, 0, 255,      # index 4 -> nibble 0x5 blue  (index/nibble differ!)
    0, 255, 0,      # index 5 -> nibble 0x6 green (index/nibble differ!)
]

# Pillow "P"-mode palette indices are contiguous from 0; the wire format's
# nibble codes are not contiguous (0x4 is skipped). This is the one and
# only place that bridges the two numbering schemes.
INDEX_TO_NIBBLE = {0: BLACK, 1: WHITE, 2: YELLOW, 3: RED, 4: BLUE, 5: GREEN}

# Named index constants so no drawing code in render.py ever writes a bare
# integer palette index.
IDX_BLACK = 0
IDX_WHITE = 1
IDX_YELLOW = 2
IDX_RED = 3
IDX_BLUE = 4
IDX_GREEN = 5

_PALETTE_SIZE = 256


def new_canvas(bg_index):
    """Return a fresh "P"-mode (1200x1600) canvas, palette already applied,
    filled with bg_index. Callers draw directly onto this with integer
    palette-index fills (02-RESEARCH.md Architecture Pattern 1) - never
    compose in RGB and quantize afterward.
    """
    from PIL import Image

    canvas = Image.new("P", (WIDTH, HEIGHT), color=bg_index)
    padded = list(PALETTE_RGB) + [0, 0, 0] * (_PALETTE_SIZE - len(PALETTE_RGB) // 3)
    canvas.putpalette(padded)
    return canvas


def pack_panel(canvas):
    """Pack a "P"-mode (1200x1600) canvas into the exact 960,000-byte
    docs/PROTOCOL.md section 1 wire format: 1600 rows x 600 bytes, 2 px per
    byte, the LEFT pixel of each pair in the HIGH nibble
    (byte = (left_nibble << 4) | right_nibble). 02-RESEARCH.md's verified
    Architecture Pattern 3, copied here as render.py's shared packing step.
    """
    px = list(canvas.getdata())
    out = bytearray(ROW_BYTES * HEIGHT)
    for row in range(HEIGHT):
        base = row * WIDTH
        obase = row * ROW_BYTES
        for col in range(0, WIDTH, 2):
            left = INDEX_TO_NIBBLE[px[base + col]]
            right = INDEX_TO_NIBBLE[px[base + col + 1]]
            out[obase + col // 2] = (left << 4) | right
    assert len(out) == IMAGE_BYTES
    return bytes(out)
