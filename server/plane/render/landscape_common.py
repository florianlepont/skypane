"""Shared geometry for the native landscape layout family.

Every dimension derives from the canvas size handed in, so the same code
serves any landscape panel; nothing here names a specific resolution.
Imports no portrait layout module.
"""
from typing import NamedTuple

MIN_MARGIN_PX = 16
MARGIN_FRACTION = 0.05
GLYPH_COLUMN_FRACTION = 0.30
COLUMN_GAP_FRACTION = 0.03
HEADING_HEIGHT_FRACTION = 0.085
BODY_HEIGHT_FRACTION = 0.050
MIN_HEADING_PX = 14
MIN_BODY_PX = 10


class HoldColumns(NamedTuple):
    """Horizontal split of a landscape canvas: a glyph column on the left
    and a text column on the right, both inside the outer margin."""

    margin: int
    glyph_center_x: int
    text_left: int
    text_right: int


def margin_for(size: tuple[int, int]) -> int:
    """Outer margin in pixels: a fraction of the short side, never below
    MIN_MARGIN_PX."""
    return max(MIN_MARGIN_PX, round(min(size) * MARGIN_FRACTION))


def hold_columns(size: tuple[int, int]) -> HoldColumns:
    """Split `size` into the glyph and text columns of a hold screen."""
    width, _height = size
    margin = margin_for(size)
    glyph_width = round(width * GLYPH_COLUMN_FRACTION)
    gap = round(width * COLUMN_GAP_FRACTION)
    return HoldColumns(
        margin=margin,
        glyph_center_x=margin + glyph_width // 2,
        text_left=margin + glyph_width + gap,
        text_right=width - margin,
    )


def heading_px(size: tuple[int, int]) -> int:
    """Initial heading font size for a canvas of `size`."""
    return max(MIN_HEADING_PX, round(size[1] * HEADING_HEIGHT_FRACTION))


def body_px(size: tuple[int, int]) -> int:
    """Initial body font size for a canvas of `size`."""
    return max(MIN_BODY_PX, round(size[1] * BODY_HEIGHT_FRACTION))


def assert_within_canvas(
    bbox: tuple[float, float, float, float], size: tuple[int, int], what: str
) -> None:
    """Raise AssertionError when `bbox` (left, top, right, bottom) leaves the
    canvas margins; `what` names the element in the message."""
    margin = margin_for(size)
    left, top, right, bottom = bbox
    width, height = size
    if left < margin or top < margin or right > width - margin or bottom > height - margin:
        raise AssertionError(
            f"{what} bbox {bbox} leaves the {margin}px margins of a {width}x{height} canvas"
        )
