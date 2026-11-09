"""Field and small-text ink patterns for the giant-lettering pairings.

All patterns are "P" images holding panel palette indices only; no RGB
intermediate survives into the result.
"""
from functools import lru_cache
from typing import Tuple

from PIL import Image

from server import panel_format as pf
from server.pairings import Pairing
from server.plane import dither

# Fraction of the way yellow small text is dithered toward black.
YELLOW_TEXT_DARKEN = 0.45


def ink_index(name: str) -> int:
    """Panel palette index for a lowercase ink name such as "blue"."""
    return int(getattr(pf, "IDX_" + name.upper()))


def _flat(idx: int, size: Tuple[int, int]) -> Image.Image:
    return pf.new_canvas(idx, size)


def field_pattern(pairing: Pairing, size: Tuple[int, int] = (pf.WIDTH, pf.HEIGHT)) -> Image.Image:
    """The field behind the lettering: the pairing's ink dithered toward white
    by its lighten fraction, or flat white when the pairing has none."""
    idx = ink_index(pairing.field_ink)
    if pairing.field_lighten is None:
        return _flat(idx, size)
    return dither.dithered_state_background(idx, pairing.field_lighten, size)


@lru_cache(maxsize=8)
def _darkened_cached(idx: int, fraction: float, size: Tuple[int, int]) -> Image.Image:
    r, g, b = pf.PALETTE_RGB[idx * 3: idx * 3 + 3]
    blend = tuple(round(c * (1 - fraction)) for c in (r, g, b))
    flat = Image.new("RGB", size, blend)
    two = Image.new("P", (1, 1))
    two.putpalette([r, g, b, 0, 0, 0])
    quantised = flat.quantize(palette=two, dither=Image.Dither.FLOYDSTEINBERG)
    remap = bytes([idx, pf.IDX_BLACK] + [0] * 254)
    canvas = Image.frombytes("P", size, quantised.tobytes().translate(remap))
    canvas.putpalette(pf.padded_palette())
    return canvas


def small_text_ink_pattern(pairing: Pairing,
                           size: Tuple[int, int] = (pf.WIDTH, pf.HEIGHT)) -> Image.Image:
    """Ink for small text. Yellow has no darker ink, so it is dithered toward
    black to stay legible on its light field; other pairings use their
    lettering ink flat.
    """
    if pairing.small_text_dither_toward_black:
        idx = ink_index(pairing.lettering_ink)
        return _darkened_cached(idx, YELLOW_TEXT_DARKEN, tuple(size)).copy()
    return _flat(ink_index(pairing.lettering_ink), size)
