"""Palette legality check for the giant-lettering family.

Kept apart from the classic renderer's check: a very light field (yellow at
75% toward white) legitimately has more white than field-ink pixels, which
the classic "field ink is the most common index" rule would reject.
"""
from PIL import Image

from server import panel_format as pf

LEGAL_INDICES = frozenset({
    pf.IDX_BLACK, pf.IDX_WHITE, pf.IDX_YELLOW, pf.IDX_RED, pf.IDX_BLUE, pf.IDX_GREEN,
})


def assert_giant_palette(canvas: Image.Image, field_idx: int) -> None:
    """Every pixel is one of the six panel indices and the most common index
    is the field ink or white."""
    colors = canvas.getcolors(maxcolors=256) or []
    counts = {value: count for count, value in colors}
    illegal = set(counts) - LEGAL_INDICES
    assert not illegal, (
        "canvas contains illegal palette index(es) %r - expected a subset of %r"
        % (sorted(illegal), sorted(LEGAL_INDICES))
    )
    dominant = max(counts, key=lambda v: counts[v]) if counts else field_idx
    assert dominant in {field_idx, pf.IDX_WHITE}, (
        "dominant index %r is neither the field ink %r nor white" % (dominant, field_idx)
    )
