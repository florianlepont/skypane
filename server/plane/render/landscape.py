# SPDX-License-Identifier: AGPL-3.0-only
"""Single entry point of the native landscape layout family.

Mirrors `layout.build_canvas` for a landscape `HardwareProfile`: active
states go to the flight card, every other state to the hold-screen
builders. No dimension is named here; the canvas size comes from the
profile.
"""
from types import SimpleNamespace

from server import device_config, hardware
from server.plane.render import landscape_card, landscape_common, landscape_hold, style

ACTIVE_STATES = ("departing", "arriving", "overhead")
HOLD_STATES = ("empty", "quiet_hours", "display_off", "battery_empty")
# The source-fault caption may extend to this fraction of the canvas width.
FAULT_CAPTION_RIGHT = 0.5


def _with_marks(canvas, size, ink, source_fault, battery_low):
    """Draw the battery-low glyph and source-fault badge in the bottom-left
    corner, in the hold's own ink, after the hold canvas is built (the hold
    builders cannot import the card geometry)."""
    if battery_low:
        landscape_card.draw_battery_low(canvas, size, ink)
    if source_fault:
        geom = SimpleNamespace(
            margin=landscape_common.margin_for(size),
            overlay_right=round(size[0] * FAULT_CAPTION_RIGHT),
        )
        landscape_card.draw_source_fault(canvas, size, geom, ink, "bold")
    return canvas


def build_landscape_canvas(
    profile, flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False, quiet_hours_until=None, state_dir=None,
):
    """Pre-pack "P"-mode canvas at `profile`'s size for `flight` in `state`
    ("departing" / "arriving" / "overhead" / "empty" / "quiet_hours" / "display_off" /
    "battery_empty").

    Raises ValueError for a profile whose layout family is not landscape
    or for an unknown state. A missing `flight` renders the empty screen;
    "battery_empty" ignores every other argument so its bytes stay
    constant for the whole parked episode.
    """
    if profile.layout_family != hardware.LAYOUT_LANDSCAPE:
        raise ValueError(
            "landscape renderer needs a landscape profile, got %r" % (profile.layout_family,)
        )
    if state not in ACTIVE_STATES + HOLD_STATES:
        raise ValueError("unknown state %r" % (state,))
    size = (profile.width, profile.height)
    if state == "battery_empty":
        return landscape_hold.build_battery_empty_canvas(size)
    if state == "display_off":
        return _with_marks(
            landscape_hold.build_display_off_canvas(size), size, style.DIMMED_INK,
            source_fault, battery_low)
    if state == "quiet_hours":
        return _with_marks(
            landscape_hold.build_quiet_hours_canvas(size, quiet_hours_until), size,
            style.DIMMED_INK, source_fault, battery_low)
    if flight is None or state == "empty":
        return _with_marks(
            landscape_hold.build_empty_canvas(size, runway_id), size, style.EMPTY_INK,
            source_fault, battery_low)
    return landscape_card.build_card_canvas(
        size, flight, state, route=route, previous_flight=previous_flight,
        previous_route=previous_route, previous_state=previous_state, theme_id=theme_id,
        runway_id=runway_id, source_fault=source_fault, battery_low=battery_low,
        state_dir=state_dir,
    )
