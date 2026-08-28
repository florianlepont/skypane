#!/usr/bin/env python3
"""Palette quantization: the shared full-6-color Floyd-Steinberg dithering
helper the per-airline illustration path (render.draw_illustration())
consumes.

Quantizes a Pillow "RGB" image against `panel_format.PALETTE_RGB` directly,
in the canvas's own index order (`[Black, White, Yellow, Red, Blue, Green]`
== `IDX_BLACK..IDX_GREEN`). The quantized image's local indices already ARE
the canvas's real indices, so no `.point()` remap is ever applied here -
adding one would risk silently scrambling colors (03-RESEARCH.md Pitfall 3).

Padding the target palette to 256 entries is an active footgun (a zero
filler entry can win nearest-neighbour matching for near-black source
pixels, 03-RESEARCH.md Pitfall 2) - `panel_palette_image()` below builds the
palette image from exactly `PALETTE_RGB`'s 6 entries, nothing appended.

Phase 3 D-21 (03-CONTEXT.md): this module previously also owned a
two-tone dithered "mood background" gradient (`build_mood_background()`,
D-17/D-18) that painted the active-state background field. D-21 replaced
that with a flat single-color fill (`panel_format.new_canvas()`, drawn
directly in render.py) after the developer confirmed a flat field on real
rendered previews - the mood-background recipe and its supporting constants
have been removed rather than left dead in this file.
"""
from PIL import Image

from server import panel_format as pf

WIDTH = pf.WIDTH
HEIGHT = pf.HEIGHT


def panel_palette_image():
    """Return a 1x1 "P" image whose palette is exactly panel_format's
    6-entry PALETTE_RGB, with nothing appended. Padding this to 256 entries
    is an active footgun (a zero filler entry can win nearest-neighbour
    matching for near-black source pixels) - see 03-RESEARCH.md Pitfall 2.
    """
    img = Image.new("P", (1, 1))
    img.putpalette(list(pf.PALETTE_RGB))
    return img


def dither_to_full_panel_palette(source_rgb):
    """Quantize `source_rgb` (a Pillow "RGB" image) against the panel's
    full 6-color legal palette via Floyd-Steinberg dithering. No `.point()`
    call, no remap: PALETTE_RGB's order already is IDX_BLACK..IDX_GREEN, so
    the quantized image's local indices already are the canvas's real
    indices.
    """
    return source_rgb.quantize(palette=panel_palette_image(), dither=Image.FLOYDSTEINBERG)


def dithered_state_background(bg_idx, lighten_fraction=0.4):
    """Return a full WIDTHxHEIGHT "P"-mode canvas whose background field is
    `bg_idx`'s ink lightened toward White via Floyd-Steinberg dithering,
    rather than a flat fill (`panel_format.new_canvas()`).

    Phase 7 07-01 on-glass finding: at full-panel coverage the flat fill's
    raw ink (Blue/Green) reads noticeably darker/more saturated than the
    developer wants, and no software value can change the physical ink
    itself - the only way to visually lighten it is to dither a blend
    toward White. `lighten_fraction` is the blend weight toward White (0 =
    the flat fill's own color, 1 = pure White); keep it comfortably under
    0.5 so `bg_idx` stays the dominant index on the resulting canvas
    (`_assert_legal_palette()`'s dominance invariant in render.py) rather
    than White outnumbering it.
    """
    r, g, b = pf.PALETTE_RGB[bg_idx * 3 : bg_idx * 3 + 3]
    blend = (
        round(r + (255 - r) * lighten_fraction),
        round(g + (255 - g) * lighten_fraction),
        round(b + (255 - b) * lighten_fraction),
    )
    flat_rgb = Image.new("RGB", (WIDTH, HEIGHT), blend)

    # Quantize against ONLY {bg_idx's own ink, White} - never the full
    # 6-color palette. Once Blue and Green were both darkened during the
    # same on-glass session (07-01), they landed close enough together in
    # RGB space that the generic 6-color quantizer picked Blue as the
    # nearest match for a lightened-Green target, leaving the arriving
    # state's background almost entirely the wrong ink. A dedicated 2-entry
    # palette makes that impossible regardless of how any other ink is tuned.
    two_color_palette = Image.new("P", (1, 1))
    two_color_palette.putpalette([r, g, b, 255, 255, 255])
    dithered = flat_rgb.quantize(palette=two_color_palette, dither=Image.FLOYDSTEINBERG)

    # dithered's local indices are 0 (bg_idx's ink) / 1 (White) only - remap
    # onto the canvas's real index space, then reattach the full panel
    # palette so downstream index-fill drawing (ImageDraw with IDX_* fills)
    # behaves exactly like a panel_format.new_canvas() canvas.
    local_indices = dithered.getdata()
    canvas = Image.new("P", (WIDTH, HEIGHT))
    canvas.putdata([bg_idx if v == 0 else pf.IDX_WHITE for v in local_indices])
    canvas.putpalette(pf.padded_palette())
    return canvas


def write_calibration_preview(out_dir):
    """Write a six-swatch calibration PNG into `out_dir` for the on-glass
    calibration pass: six equal horizontal bands, one per palette index in
    index order, rendered from PALETTE_RGB - the band order is the
    contract, not any label. Returns the list of written paths (one).
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
