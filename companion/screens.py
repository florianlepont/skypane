"""companion/screens.py — the companion's screen-type registry (phase 18).

SkyPane will eventually drive more than one kind of screen (the plane
frame today; a RER departures board and others later), and each kind
carries its own set of settings. This module is the seam that lets the
Display and Device pages render *per screen type* instead of assuming
"the one frame": every screen type declares which settings groups it
supports, in which order, and the page builders in
companion/pages/config_page.py walk that declaration rather than a
hard-coded list.

Today there is exactly one screen type and one physical device, and the
on-disk device config (server/device_config.py) is still a single
document, so the registry below is deliberately small: it changes how
the pages are *composed*, not where the values live. When a second
device arrives, the next step is a per-screen state directory (or a
per-screen key in the config) selected by `screen_id` — this module is
the one place that lookup will need to grow.

Everything here is plain data plus one lookup helper; nothing renders.
"""

# Settings-group identifiers. config_page.py's builders are keyed on
# these exact strings (see config_page.GROUP_BUILDERS). Adding a group
# means adding a builder there AND listing the id on every screen type
# that supports it here.
GROUP_THEME = "theme"
GROUP_QUIET_HOURS = "quiet_hours"
GROUP_DISPLAY = "display"
GROUP_RUNWAY = "runway"
GROUP_LED = "led"
GROUP_WAKE_INTERVAL = "wake_interval"
GROUP_CALENDAR = "calendar"

# Everyday groups render on the Display page; advanced groups on the
# Device page. The split is a property of the GROUP, not of the screen
# type: a screen type simply lists which groups it has.
EVERYDAY_GROUPS = (GROUP_THEME, GROUP_QUIET_HOURS, GROUP_DISPLAY)
ADVANCED_GROUPS = (GROUP_RUNWAY, GROUP_LED, GROUP_WAKE_INTERVAL, GROUP_CALENDAR)

DEFAULT_SCREEN_ID = "plane-frame"

SCREEN_TYPES = {
    DEFAULT_SCREEN_ID: {
        "label": "Plane frame",
        "description": (
            "The e-ink frame showing the aircraft currently using the "
            "watched Orly runway."),
        # Display-page groups, in render order.
        "everyday_groups": (GROUP_THEME, GROUP_QUIET_HOURS, GROUP_DISPLAY),
        # Device-page groups, in render order.
        "advanced_groups": (GROUP_RUNWAY, GROUP_LED, GROUP_WAKE_INTERVAL, GROUP_CALENDAR),
        # Whether the Device page also shows the per-flight colour rules
        # editor and the manual refresh ("poll now") control — both are
        # plane-specific today.
        "has_colour_rules": True,
        "has_manual_poll": True,
    },
}

SCREEN_IDS = tuple(SCREEN_TYPES)


def screen_type(screen_id=None):
    """The screen-type record for `screen_id`, falling back to the default
    screen for None or an unknown id — never raises, never returns None,
    so a page builder can always read `["everyday_groups"]` off the
    result. Unknown ids fall back rather than raising because the id
    may one day come from a URL; a hostile value must degrade, not
    500.
    """
    if screen_id in SCREEN_TYPES:
        return SCREEN_TYPES[screen_id]
    return SCREEN_TYPES[DEFAULT_SCREEN_ID]


def current_screen_id(ctx=None):
    """The screen the companion is currently configuring. Single-device
    today, so always DEFAULT_SCREEN_ID; reads `ctx.get("screen_id")`
    first so the request layer can start threading a selection through
    without this function's callers changing.
    """
    if isinstance(ctx, dict):
        candidate = ctx.get("screen_id")
        if candidate in SCREEN_TYPES:
            return candidate
    return DEFAULT_SCREEN_ID
