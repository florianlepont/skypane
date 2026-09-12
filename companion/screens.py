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
# 20-11-PLAN.md Task 1 (D-26/D-28): the Notifications group — a Device-
# page-only group (never everyday), positioned per D-10's list (LED,
# wake interval, notifications, manual refresh). "Manual refresh" is not
# a group in this registry (it is a plain `.page-section` `render()`
# renders directly, gated by `has_manual_poll` below), so this tuple's
# own trailing member is this one.
GROUP_NOTIFICATIONS = "notifications"

# Everyday groups render on the Display page; advanced groups on the
# Device page. The split is a property of the GROUP, not of the screen
# type: a screen type simply lists which groups it has.
#
# 20-07-PLAN.md Task 1 (D-10/D-11): Runway and Calendar move here from
# ADVANCED_GROUPS — a household member finds every everyday setting on
# Display now (Look/What it watches/When it is on), and Device keeps
# only hardware, data and diagnostics groups. grep-confirmed (2026-09-11)
# unused by any production code or test — kept here for documentation/
# honesty only; these two module-level tuples gate nothing themselves,
# unlike each screen type's own "everyday_groups"/"advanced_groups" keys
# below, which config_page.scope_groups() actually reads.
EVERYDAY_GROUPS = (GROUP_THEME, GROUP_CALENDAR, GROUP_RUNWAY, GROUP_DISPLAY, GROUP_QUIET_HOURS)
# 20-11-PLAN.md Task 1 (D-26): GROUP_NOTIFICATIONS joins this documentation-
# only tuple too, for the same "kept for honesty, gates nothing itself"
# reason the comment above already states.
ADVANCED_GROUPS = (GROUP_LED, GROUP_WAKE_INTERVAL, GROUP_NOTIFICATIONS)

DEFAULT_SCREEN_ID = "plane-frame"

SCREEN_TYPES = {
    DEFAULT_SCREEN_ID: {
        "label": "Plane frame",
        "description": (
            "The e-ink frame showing the aircraft currently using the "
            "watched Orly runway."),
        # Display-page groups, in render order (20-07-PLAN.md Task 1,
        # D-10/D-11: Runway and Calendar joined this tuple this phase —
        # the per-supersection grouping (Look/What it watches/When it is
        # on) is config_page.render()'s own concern, but this order does
        # not contradict it: theme and calendar under "Look", runway
        # under "What it watches", display and quiet_hours under "When
        # it is on").
        "everyday_groups": (
            GROUP_THEME, GROUP_CALENDAR, GROUP_RUNWAY, GROUP_DISPLAY, GROUP_QUIET_HOURS),
        # Device-page groups, in render order. 20-11-PLAN.md Task 1
        # (D-26/D-28): GROUP_NOTIFICATIONS joins after GROUP_WAKE_INTERVAL —
        # D-10's list order is LED, wake interval, notifications, manual
        # refresh, and "manual refresh" is rendered directly by render()'s
        # own has_manual_poll branch below, never through this tuple.
        "advanced_groups": (GROUP_LED, GROUP_WAKE_INTERVAL, GROUP_NOTIFICATIONS),
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
