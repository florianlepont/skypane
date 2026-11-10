"""How a stored photo is fitted to a panel.

``pos_x`` / ``pos_y`` are object-position fractions of the slack left after
scaling: 0 is flush left/top, 1 flush right/bottom, 0.5 centred. Only the
axis that has slack matters for a given panel aspect, so one pair serves
both the portrait and the landscape panel. Bands mode ignores them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MODES = ("fill", "bands")
_DECIMALS = 4


def _checked_pos(name: str, value: float) -> float:
    # ImageOps.fit silently resets bad centering to 0.5, so reject here.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be a finite number in [0, 1]")
    return round(float(value), _DECIMALS)


@dataclass(frozen=True)
class FitSetting:
    """Validated fit mode and crop position."""

    mode: str = "fill"
    pos_x: float = 0.5
    pos_y: float = 0.5

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        object.__setattr__(self, "pos_x", _checked_pos("pos_x", self.pos_x))
        object.__setattr__(self, "pos_y", _checked_pos("pos_y", self.pos_y))
