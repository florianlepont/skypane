"""Pre-processing applied between the crop and the dither.

Tone is stretched on luminance (hue preserving), blended with the original
so dull scenes are lifted without over-cooking skin, then saturation is
raised a little to survive the six-colour palette.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageEnhance, ImageOps

MAX_SATURATION = 1.3


@dataclass(frozen=True)
class PrepParams:
    """cutoff: percent clipped at each histogram end; strength: blend weight
    of the stretched image in [0, 1]; saturation: colour enhancement factor."""

    cutoff: float
    strength: float
    saturation: float

    def __post_init__(self) -> None:
        for name in ("cutoff", "strength", "saturation"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if not 0.0 <= self.cutoff <= 49.0:
            raise ValueError("cutoff must be in [0, 49]")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("strength must be in [0, 1]")
        if not 0.0 <= self.saturation <= MAX_SATURATION:
            raise ValueError(f"saturation must be in [0, {MAX_SATURATION}]")


# Provisional defaults: they are fixed by the skin-tone record in
# docs/PHOTO-RENDERING.md and may change until that record is written.
DEFAULT_PREP = PrepParams(1.0, 0.8, 1.2)


def prepare(img_rgb: Image.Image, params: PrepParams) -> Image.Image:
    """Return a stretched, blended and saturated copy of an RGB image."""
    stretched = ImageOps.autocontrast(img_rgb, cutoff=params.cutoff, preserve_tone=True)
    mixed = Image.blend(img_rgb, stretched, params.strength)
    return ImageEnhance.Color(mixed).enhance(params.saturation)
