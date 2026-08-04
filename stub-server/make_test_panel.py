#!/usr/bin/env python3
"""Deterministic Spectra 6 panel .bin generator for stub-server testing.

Original to this repository (not vendored) - see stub-server/VENDOR.md.
Stdlib-only. Produces a file in the exact PROTOCOL.md section 1 format:

    - Exactly 960,000 bytes, no header, no compression.
    - 1600 rows of 600 bytes each (1200 pixels/row, 2 px/byte).
    - The LEFT pixel of each byte-pair occupies the HIGH nibble:
      byte = (left_px << 4) | right_px.
    - Only the six legal Spectra 6 nibble codes: 0x0 black, 0x1 white,
      0x2 yellow, 0x3 red, 0x5 blue, 0x6 green.

Two patterns are supported:

    palette (default) - six full-height vertical bands, 200 px wide
        each, left to right: black, white, yellow, red, blue, green.
        A correct blit shows six clean stripes; a swapped nibble order
        or a wrong master/slave chip-select split is instantly visible
        on the glass.

    quadrants - four coloured quadrants (red, blue, green, yellow)
        inside a one-pixel black border. Used as the second distinct
        test image for the stub server's hash-change check.

The same pattern always produces identical bytes, and therefore an
identical SHA-256 digest - this generator has no randomness.

Usage:
    python3 make_test_panel.py --pattern palette --out /tmp/panel.bin
    python3 make_test_panel.py --pattern quadrants --out /tmp/panel2.bin
"""
import argparse
import hashlib
import sys

WIDTH = 1200
HEIGHT = 1600
ROW_BYTES = WIDTH // 2  # 600
IMAGE_BYTES = ROW_BYTES * HEIGHT  # 960000

BLACK, WHITE, YELLOW, RED, BLUE, GREEN = 0x0, 0x1, 0x2, 0x3, 0x5, 0x6


def _solid_byte(code):
    return (code << 4) | code


def build_palette():
    """Six full-height vertical bands, 200 px (100 bytes) wide each."""
    band_codes = [BLACK, WHITE, YELLOW, RED, BLUE, GREEN]
    bytes_per_band = 200 // 2  # 100
    assert len(band_codes) * bytes_per_band == ROW_BYTES
    row = bytes(_solid_byte(code) for code in band_codes for _ in range(bytes_per_band))
    assert len(row) == ROW_BYTES
    return row * HEIGHT


def _interior_row(left_code, right_code):
    """One interior row: col0 and col(WIDTH-1) are the black border,
    columns 1..WIDTH-2 split evenly between left_code and right_code.
    WIDTH (1200) and the half-width (599 interior columns each side)
    line up exactly on byte-pair boundaries, so no byte mixes border
    with fill except the two edge bytes.
    """
    half = WIDTH // 2  # 600 — the left/right split lands exactly here
    row = bytearray(ROW_BYTES)
    row[0] = (BLACK << 4) | left_code               # col0 (border), col1 (left)
    left_val = _solid_byte(left_code)
    right_val = _solid_byte(right_code)
    for i in range(1, half // 2):
        row[i] = left_val                            # cols 2..(half-1), left color
    for i in range(half // 2, ROW_BYTES - 1):
        row[i] = right_val                            # cols half..(WIDTH-3), right color
    row[ROW_BYTES - 1] = (right_code << 4) | BLACK    # col(WIDTH-2) (right), col(WIDTH-1) (border)
    assert len(row) == ROW_BYTES
    return bytes(row)


def build_quadrants():
    """Four coloured quadrants inside a one-pixel black border."""
    border_row = bytes(ROW_BYTES)  # all zero nibbles == solid black
    top_row = _interior_row(RED, BLUE)
    bottom_row = _interior_row(GREEN, YELLOW)

    interior_rows = HEIGHT - 2  # rows 1..HEIGHT-2
    top_half = interior_rows // 2
    bottom_half = interior_rows - top_half

    data = border_row + (top_row * top_half) + (bottom_row * bottom_half) + border_row
    assert len(data) == IMAGE_BYTES
    return data


PATTERNS = {
    "palette": build_palette,
    "quadrants": build_quadrants,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pattern", choices=sorted(PATTERNS), default="palette")
    ap.add_argument("--out", required=True, help="output path for the generated .bin")
    args = ap.parse_args()

    data = PATTERNS[args.pattern]()
    if len(data) != IMAGE_BYTES:
        sys.exit("internal error: generated %d bytes, expected %d" % (len(data), IMAGE_BYTES))

    with open(args.out, "wb") as fh:
        fh.write(data)

    digest = hashlib.sha256(data).hexdigest()
    print("wrote %s (%d bytes, pattern=%s)" % (args.out, len(data), args.pattern))
    print("sha256 %s" % digest)


if __name__ == "__main__":
    main()
