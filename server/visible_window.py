# SPDX-License-Identifier: AGPL-3.0-only
"""Draw a screen inside the part of a panel that a mat leaves visible."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImageModule

    from server import hardware


def place(
    inner: "PILImageModule.Image",
    size: tuple[int, int],
    window: "hardware.VisibleWindow",
) -> "PILImageModule.Image":
    """A "P"-mode canvas of `size` with `inner` pasted at the window.

    `inner` must be the size of the window. The strips the mat hides repeat
    the nearest edge row or column of `inner`, so nothing but the screen's
    own field reaches them.
    """
    from PIL import Image

    if inner.size != (window.width, window.height):
        raise ValueError(f"inner {inner.size} is not the window size")
    out = Image.new("P", size)
    palette = inner.getpalette()
    if palette is not None:
        out.putpalette(palette)
    out.paste(inner, (window.x, window.y))
    right = window.x + window.width
    bottom = window.y + window.height
    _fill(out, (0, window.y, window.x, bottom), (window.x, window.y, window.x + 1, bottom))
    _fill(out, (right, window.y, size[0], bottom), (right - 1, window.y, right, bottom))
    _fill(out, (0, 0, size[0], window.y), (0, window.y, size[0], window.y + 1))
    _fill(out, (0, bottom, size[0], size[1]), (0, bottom - 1, size[0], bottom))
    return out


def _fill(
    out: "PILImageModule.Image", target: tuple[int, int, int, int], source: tuple[int, int, int, int]
) -> None:
    """Stretch the one-pixel `source` strip of `out` over the `target` box."""
    from PIL import Image

    width = target[2] - target[0]
    height = target[3] - target[1]
    if width <= 0 or height <= 0:
        return
    strip = out.crop(source).resize((width, height), Image.Resampling.NEAREST)
    out.paste(strip, target[:2])
