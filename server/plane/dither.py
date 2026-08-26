#!/usr/bin/env python3
"""Palette quantization: the two-tone dithered mood background (this plan,
03-02) and the shared full-6-color dithering helper the per-airline
illustration path (03-03) will consume.

This module owns two structurally DIFFERENT quantization paths, and it is
important a later reader does not "fix" one into the other:

- The **background** path (`build_mood_background()` below) targets a
  throwaway two-entry sub-palette `[White, state_base_rgb]`. Because that
  palette's local 0/1 numbering has no relationship to the canvas's real
  palette-index constants, the quantized result MUST be remapped with a
  `.point()` call onto the real `pf.IDX_WHITE`/`pf.IDX_BLUE`/`pf.IDX_GREEN`
  indices. Skipping the remap here would leave every mood-background pixel
  pointing at the wrong canvas color.
- The **illustration** path (`dither_to_full_panel_palette()` below, wired
  into `render.py` by 03-03) targets `panel_format.PALETTE_RGB` directly,
  in the canvas's own index order (`[Black, White, Yellow, Red, Blue,
  Green]` == `IDX_BLACK..IDX_GREEN`). Its quantized local indices already
  ARE the canvas's real indices, so it must NEVER remap - adding a `.point()`
  call there would risk silently scrambling colors (03-RESEARCH.md
  Pitfall 3).

Why the background isn't just quantized against the full 6-color palette
like the illustration is (D-17, D-18): `03-UI-SPEC.md`'s original
"Background generation recipe" specified exactly that - a light-to-base
vertical gradient plus noise, quantized against the full 6-color palette.
That recipe was executed at real 1200x1600 scale against the D-13 interim
triples during this plan's planning pass. Measured index distributions:

    departing (blue), LIGHT_TINT_MIX 0.35: 37.8% Blue, 38.7% White,
        4.5% Yellow+Red, 15.4% stray Green - marginal.
    arriving (green), LIGHT_TINT_MIX 0.35: 16.1% Green, 24.9% White,
        23.4% Yellow+Red, 17.4% Black, 18.2% Blue - FAILS. Not a green
        field at all; six-colour static.

The cause is structural, not a tuning miss: the interim Green is a dark
desaturated olive with no near neighbour in a 6-entry palette whose entries
are far apart, so Floyd-Steinberg error diffusion approximates it by mixing
Black, Yellow, Blue and Green. Tuning the tint mix moves this in the wrong
direction. The two-entry sub-palette below sidesteps the problem entirely:
quantizing against only `[White, state_base_rgb]` cannot introduce any
other hue, by construction. Measured at MOOD_LIGHT_TINT_MIX = 0.40:
departing 80.6% Blue / 19.4% White, arriving 80.6% Green / 19.4% White,
zero Yellow, Red, Black, or cross-hue pixels. This is still a genuinely
Floyd-Steinberg-dithered, gently-graded, non-flat field in the state's hue
(D-17) - what changes is only the quantization target, not the visual
recipe - and it is what keeps `02-UI-SPEC.md`'s Color contract fully intact
outside the aircraft zone: the panel contains only `{bg_idx, IDX_WHITE}`
everywhere except the illustration (D-18).
"""
import os
import random

from PIL import Image

from server import panel_format as pf
from server.plane import runway_config

WIDTH = pf.WIDTH
HEIGHT = pf.HEIGHT

# --- Mood background recipe constants (D-17/D-18) ---------------------------

# Derived from panel_format.PALETTE_RGB by slicing the Blue/Green entries
# (never re-typed as literals) - so a later on-glass calibration pass that
# edits PALETTE_RGB (03-04) automatically moves the mood hue with it. This
# is the coupling that makes that checkpoint actually change the rendered
# background, not just the developer preview.
MOOD_BASE_RGB = {
    runway_config.STATE_DEPARTING: tuple(pf.PALETTE_RGB[pf.IDX_BLUE * 3 : pf.IDX_BLUE * 3 + 3]),
    runway_config.STATE_ARRIVING: tuple(pf.PALETTE_RGB[pf.IDX_GREEN * 3 : pf.IDX_GREEN * 3 + 3]),
}

# For reference only (03-01-PLAN.md's D-13 interim triples, sliced above):
# index 4 -> Blue, index 5 -> Green. See panel_format.PALETTE_RGB itself for
# the live values - never re-typed here.

# How far toward White the top of the gradient leans. Measured and adopted
# during this plan's planning pass (see module docstring) - a starting
# point for 03-04's on-glass calibration checkpoint, not asserted final.
MOOD_LIGHT_TINT_MIX = 0.40

# Per-channel jitter amplitude applied before dithering, so Floyd-Steinberg
# produces a soft organic texture rather than mechanical banding across a
# perfectly smooth ramp.
MOOD_NOISE_AMPLITUDE = 10

# Fixed seed for the module-local Random instance the noise is drawn from.
# Unseeded (or global-`random`-reseedable) randomness here would change the
# panel's SHA-256 on every render, which makes poll_loop.py write a new
# panel every cycle and wakes the device for a ~31.5 second full refresh it
# does not need - a battery-life defect, not a cosmetic one (see
# server.plane.render's module docstring for the SHA-256-gated write path).
MOOD_NOISE_SEED = 1380

# Per-state target canvas index the two-entry quantized local index 1 maps
# onto. Defined here (not imported from render.py) so this module never
# imports server.plane.render - that would be a circular import, since
# render.py (03-02 Task 2) imports this module.
_MOOD_TARGET_IDX = {
    runway_config.STATE_DEPARTING: pf.IDX_BLUE,
    runway_config.STATE_ARRIVING: pf.IDX_GREEN,
}

# Precomputed once at import time: maps a raw random byte (0..255) onto a
# uniform jitter offset in [-MOOD_NOISE_AMPLITUDE, +MOOD_NOISE_AMPLITUDE].
_JITTER_OF_BYTE = [
    int(round(raw / 255.0 * (2 * MOOD_NOISE_AMPLITUDE) - MOOD_NOISE_AMPLITUDE))
    for raw in range(256)
]

# Cache of built mood-background canvases, keyed by state. Populated lazily
# by build_mood_background() - the ~100ms cost is paid once per process.
_mood_background_cache = {}


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
    indices. Adding a remap here is the specific bug 03-RESEARCH.md
    Pitfall 3 describes - this is the illustration path (wired by 03-03),
    structurally different from build_mood_background() below.
    """
    return source_rgb.quantize(palette=panel_palette_image(), dither=Image.FLOYDSTEINBERG)


def _build_channel_plane(raw_bytes, top_c, base_c):
    """Build one WIDTH*HEIGHT "L"-mode channel plane: a vertical linear
    interpolation from `top_c` (row 0) to `base_c` (row HEIGHT - 1), plus
    per-pixel jitter drawn from `raw_bytes` (already-generated random bytes
    from the module-local Random instance) via `_JITTER_OF_BYTE`, clamped
    to 0..255.

    Implementation note: this does the same thing a per-pixel Python loop
    calling Random.randint() would, but at a scale (WIDTH*HEIGHT*3 = ~5.76M
    values) where that loop costs seconds, not milliseconds - measured
    directly during this plan's planning pass. Instead, one row-specific
    256-entry lookup table (raw noise byte -> clamped final channel byte)
    is built per row and applied to that row's slice of `raw_bytes` via
    `bytes.translate()`, which runs at C speed. The randomness itself still
    comes from the module-local Random instance (via a single bulk
    `randbytes()` call per channel plane, not the reseedable global
    `random` functions) - only the per-pixel *application* of that
    randomness is vectorized this way.
    """
    plane = bytearray(WIDTH * HEIGHT)
    for row in range(HEIGHT):
        frac = row / (HEIGHT - 1)
        base_val = int(round(top_c + (base_c - top_c) * frac))
        row_table = bytes(
            0 if (base_val + jitter) < 0 else (255 if (base_val + jitter) > 255 else (base_val + jitter))
            for jitter in _JITTER_OF_BYTE
        )
        start = row * WIDTH
        plane[start : start + WIDTH] = raw_bytes[start : start + WIDTH].translate(row_table)
    return bytes(plane)


def _build_mood_source_rgb(state):
    """Private. Build the 1200x1600 RGB source gradient for `state` - a
    linear interpolation from a light tint of the state's hue (row 0) to
    the full base hue (row HEIGHT - 1), with per-channel jitter drawn from
    a module-local `random.Random(MOOD_NOISE_SEED)` instance so the result
    is deterministic and never depends on (or perturbs) the reseedable
    global `random` module. Assumes `state` is already a known
    MOOD_BASE_RGB key - callers validate first.
    """
    base = MOOD_BASE_RGB[state]
    top = tuple(int(c + (255 - c) * MOOD_LIGHT_TINT_MIX) for c in base)

    rng = random.Random(MOOD_NOISE_SEED)
    plane_size = WIDTH * HEIGHT
    # Three independent raw-noise byte streams, one per channel, drawn in
    # bulk from the module-local Random instance (MOOD_NOISE_SEED) - a
    # single call per channel rather than one call per pixel.
    raw_r = rng.randbytes(plane_size)
    raw_g = rng.randbytes(plane_size)
    raw_b = rng.randbytes(plane_size)

    r_plane = _build_channel_plane(raw_r, top[0], base[0])
    g_plane = _build_channel_plane(raw_g, top[1], base[1])
    b_plane = _build_channel_plane(raw_b, top[2], base[2])

    # Merge the three planes at C speed rather than interleaving bytes in a
    # Python loop, then build the image from bytes rather than per-pixel
    # putpixel() calls, which are orders of magnitude slower at this size.
    return Image.merge(
        "RGB",
        (
            Image.frombytes("L", (WIDTH, HEIGHT), r_plane),
            Image.frombytes("L", (WIDTH, HEIGHT), g_plane),
            Image.frombytes("L", (WIDTH, HEIGHT), b_plane),
        ),
    )


def build_mood_background(state):
    """Return a fresh 1200x1600 "P"-mode canvas: a deterministic,
    Floyd-Steinberg-dithered, two-tone gradient in `state`'s hue, containing
    only `{pf.IDX_WHITE, pf.IDX_BLUE}` (departing) or
    `{pf.IDX_WHITE, pf.IDX_GREEN}` (arriving), with the same 768-entry
    padded palette a panel_format.new_canvas() canvas carries.

    Memoized per state in a module-level cache, so the ~100ms build cost is
    paid once per process and the result is provably identical across
    calls - callers always receive a `.copy()` of the cached canvas, never
    the shared instance itself, since they draw on it and handing out the
    shared object would let one render's captions leak into the next.

    Raises ValueError naming the received state if it is not a known key -
    an unknown state must never silently return a wrong-coloured canvas.
    """
    if state not in MOOD_BASE_RGB:
        raise ValueError(
            "unknown mood-background state %r (expected one of %r)" % (state, sorted(MOOD_BASE_RGB))
        )

    if state not in _mood_background_cache:
        source_rgb = _build_mood_source_rgb(state)

        # A throwaway two-entry target palette: local index 0 = White,
        # local index 1 = the state's base hue. This local numbering has
        # NO relationship to the canvas's real palette indices, which is
        # exactly why the remap below (unlike dither_to_full_panel_palette()
        # above) is required, not optional (03-RESEARCH.md Pitfall 3).
        mood_palette_img = Image.new("P", (1, 1))
        mood_palette_img.putpalette([255, 255, 255] + list(MOOD_BASE_RGB[state]))

        quantized = source_rgb.quantize(palette=mood_palette_img, dither=Image.FLOYDSTEINBERG)

        # Remap local 0 -> pf.IDX_WHITE, local 1 -> the state's real canvas
        # index, via a full 256-entry .point() table (every other value is
        # unreachable but must still be defined for Pillow's LUT API).
        target_idx = _MOOD_TARGET_IDX[state]
        remap_table = [target_idx if local_idx == 1 else pf.IDX_WHITE for local_idx in range(256)]
        canvas = quantized.point(remap_table)

        # point() preserves pixel values but not palette metadata - the
        # canvas must carry the same 768-entry padded palette a
        # new_canvas() canvas does, so a mood-background canvas and a
        # new_canvas() canvas are palette-identical (both for --preview
        # rendering and so downstream code never has to special-case which
        # kind of canvas it received).
        canvas.putpalette(pf.padded_palette())

        _mood_background_cache[state] = canvas

    return _mood_background_cache[state].copy()


def write_calibration_preview(out_dir):
    """Write three calibration PNGs into `out_dir` for 03-04's on-glass
    calibration pass: a six-swatch image (six equal horizontal bands, one
    per palette index in index order, rendered from PALETTE_RGB - the band
    order is the contract, not any label) to hold against the panel showing
    `stub-server/make_test_panel.py --pattern palette`, plus
    `mood-departing.png` and `mood-arriving.png` (the RGB conversion of
    each state's build_mood_background() canvas). Returns the list of
    written paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    print(
        "WARNING: preview colours are nominal render-internal RGB triples "
        "(D-P2-03) - not a colour-accurate preview of the physical panel."
    )

    written = []

    swatch_band_h = 100
    num_indices = len(pf.PALETTE_RGB) // 3
    swatches = Image.new("RGB", (WIDTH, swatch_band_h * num_indices))
    for idx in range(num_indices):
        r, g, b = pf.PALETTE_RGB[idx * 3 : idx * 3 + 3]
        band = Image.new("RGB", (WIDTH, swatch_band_h), (r, g, b))
        swatches.paste(band, (0, idx * swatch_band_h))
    swatches_path = os.path.join(out_dir, "palette-swatches.png")
    swatches.save(swatches_path)
    written.append(swatches_path)

    for state, filename in (
        (runway_config.STATE_DEPARTING, "mood-departing.png"),
        (runway_config.STATE_ARRIVING, "mood-arriving.png"),
    ):
        path = os.path.join(out_dir, filename)
        build_mood_background(state).convert("RGB").save(path)
        written.append(path)

    return written
