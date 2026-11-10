"""Giant-lettering render family: oversized destination lettering set in
Anton, with the aircraft placed over it. `build_canvas` is the entry point
the layout dispatcher calls.
"""
from typing import Optional, Tuple

from PIL import Image

from server import screen_layouts
from server.pairings import Pairing, pairing_for_theme
from server.plane.render.giant import compose, compose_c, compose_landscape


PORTRAIT_COMPOSERS = {**compose.COMPOSERS, "c": compose_c.compose_c}
LANDSCAPE_COMPOSERS = compose_landscape.COMPOSERS


def _table(size: Tuple[int, int]):
    return PORTRAIT_COMPOSERS if size[0] < size[1] else LANDSCAPE_COMPOSERS


def supports(size: Tuple[int, int], layout: str) -> bool:
    """Whether a giant layout is composed at `size`: portrait and landscape
    canvases each have their own compositors."""
    return size[0] != size[1] and screen_layouts.is_giant_layout(layout)


def build_canvas(size: Tuple[int, int], layout: str, flight: object, state: str,
                 route: object = None, pairing: Optional[Pairing] = None,
                 theme_id: Optional[str] = None, state_dir: Optional[str] = None,
                 source_fault: bool = False, battery_low: bool = False) -> Image.Image:
    """"P"-mode canvas of `size` for an active flight in the giant layout
    `layout`, in `pairing` (or the pairing of `theme_id`). A layout without a
    compositor of its own renders as the default layout's."""
    chosen = pairing if pairing is not None else pairing_for_theme(theme_id)
    table = _table(size)
    composer = table.get(layout) or table[screen_layouts.DEFAULT_LAYOUT_ID]
    return composer(size, flight, state, route, chosen, state_dir=state_dir,
                    source_fault=source_fault, battery_low=battery_low)
