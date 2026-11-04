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
GROUP_LED = "led"
GROUP_WAKE_INTERVAL = "wake_interval"
GROUP_CALENDAR = "calendar"

# Where the wake interval lives and who may change it. This is the single
# access decision point: the group tuples below, user_view's form
# sanitising and the page cards all follow it, and nothing else tests a
# role for the wake interval.
#   DEVICE_ADMIN: only administrators, on the Console Device page.
#   DISPLAY_ALL: every signed-in role, on the Personalisation page.
DEVICE_ADMIN = "device_admin"
DISPLAY_ALL = "display_all"
WAKE_INTERVAL_PLACEMENT = DEVICE_ADMIN

_WAKE_ON_DISPLAY = WAKE_INTERVAL_PLACEMENT == DISPLAY_ALL

# Documentation only — these two tuples gate nothing; each screen
# type's own "everyday_groups"/"advanced_groups" below is what
# config_page.scope_groups() reads. GROUP_DISPLAY is not listed: the
# Frame strip is the only on/off control, but the constant stays
# defined since handle_post() still validates a crafted value against it.
# The quiet-hours group stays registered for the legacy whole-page
# render; no live page renders it (Home's dialog owns the controls).
EVERYDAY_GROUPS = (
    (GROUP_THEME, GROUP_CALENDAR, GROUP_QUIET_HOURS)
    + ((GROUP_WAKE_INTERVAL,) if _WAKE_ON_DISPLAY else ()))
ADVANCED_GROUPS = (
    (GROUP_LED,) + (() if _WAKE_ON_DISPLAY else (GROUP_WAKE_INTERVAL,)))

DEFAULT_SCREEN_ID = "plane-frame"

SCREEN_TYPES = {
    DEFAULT_SCREEN_ID: {
        "label": "Plane frame",
        "description": (
            "The e-ink frame showing the aircraft currently using the "
            "watched runway or flying near the watched location."),
        # Order doesn't dictate rendered order: config_page.render()
        # groups these into its own supersections.
        "everyday_groups": EVERYDAY_GROUPS,
        "advanced_groups": ADVANCED_GROUPS,
        "has_colour_rules": True,
    },
}



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
    """The single frame type configured by the companion."""
    return DEFAULT_SCREEN_ID
