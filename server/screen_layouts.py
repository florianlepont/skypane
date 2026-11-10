#!/usr/bin/env python3
"""The screen layouts a frame can show and the one default they share.

  * classic    the original layout.
  * a          giant lettering: the nose from the right edge and the rear
               half of the aircraft from the left edge.
  * b          giant lettering: the whole aircraft centred.
  * c          giant lettering on top, the aircraft along the bottom.
  * a_diagonal layout a with the diagonal band.

A frame that never chose a layout resolves to `DEFAULT_LAYOUT_ID`; that
constant is the only place the default is written down.

Leaf module: stdlib only.
"""
from __future__ import annotations

CLASSIC_LAYOUT_ID = "classic"
DEFAULT_LAYOUT_ID = "b"
LAYOUT_IDS: tuple[str, ...] = (CLASSIC_LAYOUT_ID, "a", "b", "c", "a_diagonal")


def normalise_layout_id(value: object) -> str:
    """`value` unchanged if it is a known layout id, else `DEFAULT_LAYOUT_ID`.
    Never raises.
    """
    if isinstance(value, str) and value in LAYOUT_IDS:
        return value
    return DEFAULT_LAYOUT_ID


def is_giant_layout(layout_id: str) -> bool:
    """True for every layout that uses the giant lettering."""
    return layout_id != CLASSIC_LAYOUT_ID
