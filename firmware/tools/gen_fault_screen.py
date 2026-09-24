#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
"""Quick task 260924-u7n (DEVICE-06): generates
`firmware/main/fault_screen_mask.h` - the committed 1-bpp ink mask
firmware/main/fault_screen.c stamps onto its own on-device dithered dark
field to draw the NO CONNECTION hold screen with zero server round-trip.

Source of truth: `server.plane.render._build_no_connection_canvas(flat=True)`
- the same composition (`_build_hold_canvas()`) DISPLAY OFF / QUIET HOURS /
BATTERY EMPTY go through, called flat (no dither) so the extracted mask is
an exact ink/no-ink boolean per pixel, not a dithered approximation of one.
`server/test_fault_screen_mask.py` proves this generator's output matches
the committed header byte-for-byte (T-u7n-03) - rerunning this tool must
always leave `git diff --stat firmware/main/fault_screen_mask.h` empty.

--- The dither spec (shared with firmware/main/fault_screen.c) ---------------

Both `firmware_equivalent_image()` below and the C module implement this
exact integer Floyd-Steinberg recipe against one constant target level
L = 102 (== round(255 * 0.4), server/plane/dither.py's own lighten_fraction
toward White) - there is deliberately no reference to the real dithered
server canvas; the device has no way to reproduce Pillow's own
Floyd-Steinberg internals, so both sides implement this one from-scratch
spec instead:

- All arithmetic is fixed-point in 1/16 units (`v16`, `e`, etc. are 16x
  the 0..255 pixel scale) so no floating point is needed on-device.
- Two error-accumulator rows, `WIDTH + 2` entries each, indexed `x + 1` so
  `x - 1` and `x + 1` never go out of bounds; both start at zero for every
  render (the C side keeps them `static`, not stack, since the app_main
  task stack is small - irrelevant here but kept for spec parity).
- Plain left-to-right raster order, no serpentine.
- Per pixel: `v16 = L * 16 + cur[x + 1]`; the pixel is White if
  `v16 >= 128 * 16`, giving quantised value `q16 = 255 * 16` (White) or
  `0` (Black); error `e = v16 - q16`.
- The error's four shares use **truncating** (toward zero) integer
  division by 16, matching C's `/` operator on a signed integer - NOT
  Python's floor-toward-negative-infinity `//`, so this module's
  `_trunc16()` helper is used everywhere a C `int16_t x / 16` appears in
  the spec: `s7 = trunc16(e * 7)`, `s3 = trunc16(e * 3)`, `s5 = trunc16(e * 5)`,
  and the last share is the exact remainder `e - (s7 + s3 + s5)` so all
  four sum to `e` precisely (no energy lost or gained, which a bare
  four-way `/16` truncation would otherwise leak).
- Diffused to: `cur[x + 2] += s7`, `nxt[x] += s3`, `nxt[x + 1] += s5`,
  `nxt[x + 2] += e - (s7 + s3 + s5)`.
- After each row, `cur`/`nxt` swap and the new `nxt` is zeroed.
- Dithering runs across every pixel of the full field, including pixels
  the mask will later override - the field is identical to what an
  unmasked dither would produce everywhere, matching
  firmware/main/fault_screen.c's own approach: masked pixels still
  contribute to (and receive) diffused error exactly as if they carried
  no mask at all, so the two sides can never drift on that account.
- Final pixel value: if the pixel lies inside the mask's bounding box AND
  its packed mask bit is 1, the pixel is White (the mask always wins);
  otherwise the pixel is whatever the dither step above produced.

This module's own dither is deliberately NOT vectorised (no numpy) -
correctness against the spec above matters far more than speed for an
offline 1200x1600-pixel one-shot preview tool, and staying in plain
Python keeps this file trivially auditable against the C it mirrors.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PIL import Image  # noqa: E402

import server.panel_format as pf  # noqa: E402
import server.plane.render as render  # noqa: E402

HEADER_PATH = os.path.join(HERE, "..", "main", "fault_screen_mask.h")
DEFAULT_PREVIEW_PATH = os.path.join(
    REPO_ROOT,
    ".planning",
    "quick",
    "260924-u7n-device-06-local-no-connection-fault-scre",
    "no-connection-preview.png",
)

# The dither spec's one constant target level (server/plane/dither.py's own
# `round(255 * 0.4)` lighten-toward-White blend, at 0% - the field's own
# ink - vs 100% - pure White). See the module docstring's dither spec for
# the full recipe this feeds.
DITHER_TARGET_LEVEL = 102


def render_mask():
    """Render `_build_no_connection_canvas(flat=True)`, extract the boolean
    ink mask (`pixel index == pf.IDX_WHITE`), crop to its bounding box via
    `Image.getbbox()`, and pack it MSB-first, one bit per pixel, row stride
    `(w + 7) // 8`, padding bits zero. Returns `(x, y, w, h, bits)`.
    """
    canvas = render._build_no_connection_canvas(flat=True)
    # A 1-bit "1" mode image where ink (White) pixels are 255 (truthy) is
    # exactly what Image.getbbox() needs to find the tightest ink-only
    # bounding box - .point() with a 256-entry LUT is a vectorised
    # per-pixel remap, no getdata()/putdata() Python loop.
    lut = [0] * 256
    lut[pf.IDX_WHITE] = 255
    mask_img = canvas.point(lut, mode="L").convert("1")

    bbox = mask_img.getbbox()
    if bbox is None:
        raise ValueError("no-connection canvas has no White (ink) pixels - nothing to mask")
    x0, y0, x1, y1 = bbox
    w = x1 - x0
    h = y1 - y0

    cropped = mask_img.crop(bbox)
    stride = (w + 7) // 8
    bits = bytearray(stride * h)
    px = cropped.load()
    for row in range(h):
        base = row * stride
        for col in range(w):
            # Pillow's "1" mode stores 0/255; truthy == ink.
            if px[col, row]:
                bits[base + col // 8] |= 0x80 >> (col % 8)
    return x0, y0, w, h, bytes(bits)


def render_header_text():
    """Return the deterministic generated-header text: SPDX + GENERATED
    banner, the include guard, `#include <stdint.h>`, the
    `FP_FAULT_MASK_X/Y/W/H/STRIDE` macros, and the packed
    `fp_fault_mask_bits[]` array, 16 bytes per line as `0x%02x,`. No
    timestamps, no absolute paths - the output must be byte-for-byte
    reproducible on any machine (including CI), which is exactly what
    `server/test_fault_screen_mask.py`'s drift test relies on.
    """
    x, y, w, h, bits = render_mask()
    stride = (w + 7) // 8

    lines = []
    lines.append("/* SPDX-FileCopyrightText: 2026 Florian Lepont")
    lines.append(" * SPDX-License-Identifier: Apache-2.0 */")
    lines.append("/* GENERATED by firmware/tools/gen_fault_screen.py from")
    lines.append(" * server/plane/render.py _build_no_connection_canvas(flat=True) - DO NOT EDIT;")
    lines.append(" * regenerate with: server/.venv/bin/python3 firmware/tools/gen_fault_screen.py */")
    lines.append("#pragma once")
    lines.append("#ifndef FP_FAULT_SCREEN_MASK_H")
    lines.append("#define FP_FAULT_SCREEN_MASK_H")
    lines.append("")
    lines.append("#include <stdint.h>")
    lines.append("")
    lines.append("#define FP_FAULT_MASK_X %d" % x)
    lines.append("#define FP_FAULT_MASK_Y %d" % y)
    lines.append("#define FP_FAULT_MASK_W %d" % w)
    lines.append("#define FP_FAULT_MASK_H %d" % h)
    lines.append("#define FP_FAULT_MASK_STRIDE %d" % stride)
    lines.append("")
    lines.append(
        "static const uint8_t fp_fault_mask_bits[FP_FAULT_MASK_STRIDE * FP_FAULT_MASK_H] = {"
    )
    for i in range(0, len(bits), 16):
        chunk = bits[i : i + 16]
        lines.append("    " + "".join("0x%02x," % b for b in chunk))
    lines.append("};")
    lines.append("")
    lines.append("#endif /* FP_FAULT_SCREEN_MASK_H */")
    lines.append("")
    return "\n".join(lines)


def _trunc16(numerator):
    """Truncating (toward zero) integer division by 16 - matches C's `/`
    operator on a signed integer, which Python's floor-toward-negative-
    infinity `//` does not for negative operands. See the module
    docstring's dither spec for why this matters.
    """
    if numerator >= 0:
        return numerator // 16
    return -((-numerator) // 16)


def firmware_equivalent_image():
    """Python port of the exact C dither algorithm (see the module
    docstring's shared spec) plus the mask stamp - a 1200x1600 "1"-mode
    (Black/White only) `PIL.Image` reproducing exactly what
    `firmware/main/fault_screen.c`'s `fp_fault_screen_render()` would blit,
    for the side-by-side preview.
    """
    width, height = pf.WIDTH, pf.HEIGHT
    x0, y0, w, h, bits = render_mask()
    stride = (w + 7) // 8

    def mask_bit_set(col, row):
        byte = bits[row * stride + col // 8]
        return bool(byte & (0x80 >> (col % 8)))

    level16 = DITHER_TARGET_LEVEL * 16
    out = bytearray(width * height)  # 0 = Black, 255 = White (mode "L")

    cur = [0] * (width + 2)
    nxt = [0] * (width + 2)

    for row in range(height):
        for col in range(width):
            v16 = level16 + cur[col + 1]
            is_white = v16 >= 128 * 16
            q16 = 255 * 16 if is_white else 0
            e = v16 - q16

            s7 = _trunc16(e * 7)
            s3 = _trunc16(e * 3)
            s5 = _trunc16(e * 5)
            s1 = e - (s7 + s3 + s5)

            cur[col + 2] += s7
            nxt[col] += s3
            nxt[col + 1] += s5
            nxt[col + 2] += s1

            in_mask = (
                x0 <= col < x0 + w
                and y0 <= row < y0 + h
                and mask_bit_set(col - x0, row - y0)
            )
            out[row * width + col] = 255 if (in_mask or is_white) else 0

        cur, nxt = nxt, cur
        for i in range(len(nxt)):
            nxt[i] = 0

    img = Image.frombytes("L", (width, height), bytes(out))
    return img.convert("1")


def _write_preview(preview_path):
    """Write the firmware-equivalent image side by side with the server's
    own dithered `_build_no_connection_canvas()`, mirroring 260923-fr4's
    side-by-side preview convention (server preview left, firmware
    reproduction right, joined via server.panel_preview's decode path for
    the server side so the comparison uses the same colour conversion the
    companion's own preview route uses).
    """
    server_canvas = render._build_no_connection_canvas()
    from server import panel_format as _pf

    server_rgb = server_canvas.convert("RGB")
    fw_rgb = firmware_equivalent_image().convert("RGB")

    gutter = 40
    combined = Image.new("RGB", (_pf.WIDTH * 2 + gutter, _pf.HEIGHT), (200, 200, 200))
    combined.paste(server_rgb, (0, 0))
    combined.paste(fw_rgb, (_pf.WIDTH + gutter, 0))
    os.makedirs(os.path.dirname(preview_path), exist_ok=True)
    combined.save(preview_path)
    return preview_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preview",
        default=DEFAULT_PREVIEW_PATH,
        help="Where to write the server-vs-firmware side-by-side preview PNG",
    )
    parser.add_argument(
        "--no-preview", action="store_true", help="Skip writing the preview PNG"
    )
    args = parser.parse_args()

    x, y, w, h, bits = render_mask()
    print("mask bbox: x=%d y=%d w=%d h=%d" % (x, y, w, h))
    if w * h > 100_000 * 8:  # a bbox producing >100KB of packed mask data
        raise SystemExit(
            "mask bbox is implausibly large (w=%d h=%d) - stopping instead of "
            "committing a bloated header; investigate the canvas composition first" % (w, h)
        )

    header_text = render_header_text()
    header_path = os.path.normpath(HEADER_PATH)
    with open(header_path, "w", encoding="utf-8") as f:
        f.write(header_text)
    header_bytes = len(header_text.encode("utf-8"))
    print("wrote %s (%d bytes)" % (header_path, header_bytes))

    if not args.no_preview:
        preview_path = _write_preview(args.preview)
        print("wrote %s" % (preview_path,))


if __name__ == "__main__":
    main()
