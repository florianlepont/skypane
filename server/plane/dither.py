#!/usr/bin/env python3
"""Palette quantization: the shared full-6-color Floyd-Steinberg dithering
helper the per-airline illustration path (render.draw_illustration())
consumes.

Quantizes against `panel_format.PALETTE_RGB` directly, in the canvas's
own index order, so the quantized image's local indices already are the
canvas's real indices - no `.point()` remap, which would risk silently
scrambling colors. Padding the target palette to 256 entries is an
active footgun (a zero filler entry can win nearest-neighbour matching
for near-black pixels), so `panel_palette_image()` uses exactly
`PALETTE_RGB`'s 6 entries.
"""
from PIL import Image

from server import panel_format as pf

WIDTH = pf.WIDTH
HEIGHT = pf.HEIGHT

# Pure and deterministic for a given (bg_idx, lighten_fraction), so
# memoizing is sound. Every lookup MUST return a fresh .copy(): callers
# draw onto the canvas, and the cached object must not be mutated.
_STATE_BACKGROUND_CACHE = {}


def panel_palette_image():
    """1x1 "P" image whose palette is exactly PALETTE_RGB's 6 entries,
    nothing appended (a 256-entry pad is an active footgun: a zero filler
    entry can win nearest-neighbour matching for near-black pixels).
    """
    img = Image.new("P", (1, 1))
    img.putpalette(list(pf.PALETTE_RGB))
    return img


def dither_to_full_panel_palette(source_rgb):
    """Quantize `source_rgb` against the panel's full 6-color palette via
    Floyd-Steinberg dithering. No remap: PALETTE_RGB's order already is
    IDX_BLACK..IDX_GREEN.
    """
    return source_rgb.quantize(palette=panel_palette_image(), dither=Image.FLOYDSTEINBERG)


def dithered_state_background(bg_idx, lighten_fraction=0.4):
    """Full WIDTHxHEIGHT "P"-mode canvas: `bg_idx`'s ink lightened toward
    White via Floyd-Steinberg dithering, since no software value can
    change how dark the physical ink itself reads on real glass.
    `lighten_fraction` is the blend weight toward White; keep it under
    0.5 so `bg_idx` stays the dominant index (see
    `_assert_legal_palette()` in render.py).
    """
    cache_key = (bg_idx, lighten_fraction)
    cached = _STATE_BACKGROUND_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()

    r, g, b = pf.PALETTE_RGB[bg_idx * 3 : bg_idx * 3 + 3]
    blend = (
        round(r + (255 - r) * lighten_fraction),
        round(g + (255 - g) * lighten_fraction),
        round(b + (255 - b) * lighten_fraction),
    )
    flat_rgb = Image.new("RGB", (WIDTH, HEIGHT), blend)

    # Quantize against ONLY {bg_idx's own ink, White}, never the full
    # 6-color palette: darkened Blue/Green land close enough in RGB space
    # that the generic quantizer can pick the wrong one.
    two_color_palette = Image.new("P", (1, 1))
    two_color_palette.putpalette([r, g, b, 255, 255, 255])
    dithered = flat_rgb.quantize(palette=two_color_palette, dither=Image.FLOYDSTEINBERG)

    # Remap local indices (0=bg_idx's ink, 1=White) onto the canvas's real
    # index space via translate(), then reattach the full panel palette.
    remap = bytes([bg_idx, pf.IDX_WHITE] + [0] * 254)
    canvas = Image.frombytes("P", (WIDTH, HEIGHT), dithered.tobytes().translate(remap))
    canvas.putpalette(pf.padded_palette())

    _STATE_BACKGROUND_CACHE[cache_key] = canvas
    return canvas.copy()


def write_calibration_preview(out_dir):
    """Write a six-swatch calibration PNG into `out_dir`: one horizontal
    band per palette index, in index order (the contract, not any
    label). Returns the list of written paths (one).
    """
    import os

    os.makedirs(out_dir, exist_ok=True)
    print(
        "WARNING: preview colours are nominal render-internal RGB triples "
        "(D-P2-03) - not a colour-accurate preview of the physical panel."
    )

    swatch_band_h = 100
    num_indices = len(pf.PALETTE_RGB) // 3
    swatches = Image.new("RGB", (WIDTH, swatch_band_h * num_indices))
    for idx in range(num_indices):
        r, g, b = pf.PALETTE_RGB[idx * 3 : idx * 3 + 3]
        band = Image.new("RGB", (WIDTH, swatch_band_h), (r, g, b))
        swatches.paste(band, (0, idx * swatch_band_h))
    swatches_path = os.path.join(out_dir, "palette-swatches.png")
    swatches.save(swatches_path)
    return [swatches_path]
