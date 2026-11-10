"""Landscape (800x480) geometry of the giant-lettering layouts.

Horizontal values are fractions of the width, vertical values fractions of
the height, so another landscape size can reuse them. The destination is one
stretched line in every layout.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

REF_W, REF_H = 800, 480

Frac4 = Tuple[float, float, float, float]


@dataclass(frozen=True)
class Whole:
    """Whole aircraft: painted width and centre."""
    width: float
    center_x: float
    center_y: float


@dataclass(frozen=True)
class Halves:
    """Nose half from the right edge and rear half from the left edge: widths
    of the whole aircraft behind each half, the anchors of the cockpit tip and
    the tail end, and the vertical placement."""
    nose_plane: float
    rear_plane: float
    nose_left: float
    rear_right: float
    nose_center_y: float
    rear_bottom_y: float


@dataclass(frozen=True)
class Footer:
    """Flight number and airline name. `x` is the left edge, or the right edge
    when `align_right`; the tops and sizes are fractions of the height."""
    x: float
    align_right: bool
    flight_top: float
    flight_px: float
    airline_top: float
    airline_px: float


@dataclass(frozen=True)
class LandscapeSpec:
    box: Frac4
    footer: Footer
    whole: Optional[Whole] = None
    halves: Optional[Halves] = None
    diagonal: bool = False


MARGIN = 28 / REF_W
FLIGHT_PX = 64 / REF_H
AIRLINE_PX = 26 / REF_H
DIRECTION_PX = 24 / REF_H
DIRECTION_TOP = 12 / REF_H
# The lettering starts below the direction word in every layout.
LETTERING_TOP = 52 / REF_H

_HALVES = Halves(nose_plane=800 / REF_W, rear_plane=540 / REF_W, nose_left=416 / REF_W,
                 rear_right=258 / REF_W, nose_center_y=105 / REF_H, rear_bottom_y=456 / REF_H)
_LEFT_FOOTER = Footer(MARGIN, False, 356 / REF_H, FLIGHT_PX, 426 / REF_H, AIRLINE_PX)
_RIGHT_FOOTER = Footer(1 - MARGIN, True, 360 / REF_H, FLIGHT_PX, 428 / REF_H, AIRLINE_PX)

SPECS = {
    "b": LandscapeSpec(
        box=(16 / REF_W, LETTERING_TOP, 1 - 16 / REF_W, 330 / REF_H),
        footer=Footer(MARGIN, False, 358 / REF_H, FLIGHT_PX, 428 / REF_H, AIRLINE_PX),
        whole=Whole(600 / REF_W, 0.5, 190 / REF_H)),
    "a": LandscapeSpec(
        box=(16 / REF_W, LETTERING_TOP, 1 - 16 / REF_W, 340 / REF_H),
        footer=Footer(430 / REF_W, False, 356 / REF_H, FLIGHT_PX, 426 / REF_H, AIRLINE_PX),
        halves=_HALVES),
    "c": LandscapeSpec(
        box=(16 / REF_W, LETTERING_TOP, 1 - 16 / REF_W, 330 / REF_H),
        footer=_LEFT_FOOTER,
        whole=Whole(430 / REF_W, 550 / REF_W, 400 / REF_H)),
    "a_diagonal": LandscapeSpec(
        box=(16 / REF_W, LETTERING_TOP, 1 - 16 / REF_W, 340 / REF_H),
        footer=_RIGHT_FOOTER, halves=_HALVES, diagonal=True),
}
