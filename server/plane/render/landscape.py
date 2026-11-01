"""Single entry point of the native landscape layout family.

Mirrors `layout.build_canvas` for a landscape `HardwareProfile`: active
states go to the flight card, every other state to the hold-screen
builders. No dimension is named here; the canvas size comes from the
profile.
"""
from server import device_config, hardware
from server.plane.render import landscape_card, landscape_hold

ACTIVE_STATES = ("departing", "arriving", "overhead")
HOLD_STATES = ("empty", "quiet_hours", "display_off", "battery_empty")


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
        return landscape_hold.build_display_off_canvas(size)
    if state == "quiet_hours":
        return landscape_hold.build_quiet_hours_canvas(size, quiet_hours_until)
    if flight is None or state == "empty":
        return landscape_hold.build_empty_canvas(size, runway_id)
    return landscape_card.build_card_canvas(
        size, flight, state, route=route, previous_flight=previous_flight,
        previous_route=previous_route, previous_state=previous_state, theme_id=theme_id,
        runway_id=runway_id, source_fault=source_fault, battery_low=battery_low,
        state_dir=state_dir,
    )
