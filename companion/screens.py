"""The companion's screen-type registry: lets Display/Device pages
render *per screen type* instead of assuming one fixed frame. Each
screen type declares which settings groups it supports, in which
order; config_page.py's builders walk that declaration.

Today there is exactly one screen type and one physical device, so
this stays small — it changes how pages are composed, not where
values live. Plain data plus one lookup helper; nothing renders.
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
# A Device-page-only group (never everyday). "Manual refresh" is not a
# group in this registry (it is a plain `.page-section` `render()`
# renders directly, gated by `has_manual_poll` below).
GROUP_NOTIFICATIONS = "notifications"

# Documentation only — these two tuples gate nothing; each screen
# type's own "everyday_groups"/"advanced_groups" below is what
# config_page.scope_groups() reads. GROUP_DISPLAY is not listed: the
# Frame strip is the only on/off control, but the constant stays
# defined since handle_post() still validates a crafted value against it.
EVERYDAY_GROUPS = (GROUP_THEME, GROUP_CALENDAR, GROUP_RUNWAY, GROUP_QUIET_HOURS)
ADVANCED_GROUPS = (GROUP_LED, GROUP_WAKE_INTERVAL, GROUP_NOTIFICATIONS)

DEFAULT_SCREEN_ID = "plane-frame"

SCREEN_TYPES = {
    DEFAULT_SCREEN_ID: {
        "label": "Plane frame",
        "description": (
            "The e-ink frame showing the aircraft currently using the "
            "watched Orly runway."),
        # Order doesn't dictate rendered order: config_page.render()
        # groups these into its own supersections.
        "everyday_groups": (
            GROUP_THEME, GROUP_CALENDAR, GROUP_RUNWAY, GROUP_QUIET_HOURS),
        # "Manual refresh" is rendered directly by render()'s own
        # has_manual_poll branch, never through this tuple.
        "advanced_groups": (GROUP_LED, GROUP_WAKE_INTERVAL, GROUP_NOTIFICATIONS),
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
