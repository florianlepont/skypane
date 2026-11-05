"""The Home title's decoration: a greeting line and a plane on a dotted trail,
both under the title.

Both are purely decorative (`aria-hidden`), so the page keeps one plain
`<h1>` ("Home"/"Accueil") for titles, screen readers and no-script visitors.
The greeting's server text is a neutral default; nav-dropdown.js swaps in the
wording for the viewer's local hour from the four `data-greeting-*`
attributes (morning 05-12, afternoon 12-17, evening 17-21, night otherwise,
the same edges as the sky). Its box is always reserved, so the swap never
moves the title. The plane is only rendered when the frame has a flight to
show, and flies in once through a finite CSS animation (style.css).
"""

import companion.device_scope as device_scope
import companion.i18n as i18n
from companion.layout import escape_html
from companion.ui_shell import device_display_name

GREETING_DEFAULT = i18n.msg("home.greeting_default", "Hello")
GREETING_MORNING = i18n.msg("home.greeting_morning", "Good morning")
GREETING_AFTERNOON = i18n.msg("home.greeting_afternoon", "Good afternoon")
GREETING_EVENING = i18n.msg("home.greeting_evening", "Good evening")
GREETING_NIGHT = i18n.msg("home.greeting_night", "Good night")

# The trail is a gentle rise from the lower left to the plane's resting
# point; the plane is a top-down silhouette drawn around its own origin and
# placed at the trail's end.
_TRAIL_PATH = "M 4 46 C 80 46 150 8 296 14"
_PLANE_PATH = (
    "M 12 0 L 4 -2 L -2 -10 L -5 -10 L -2 -2 L -8 -2 L -10 -6 L -12 -6 "
    "L -10 0 L -12 6 L -10 6 L -8 2 L -2 2 L -5 10 L -2 10 L 4 2 Z")


def _frame_name():
    """The active frame's name when the person has several frames, else ""."""
    device = device_scope.current_device()
    if device is None or len(device_scope.switcher_entries()) < 2:
        return ""
    return device_display_name(device)


def greeting_html():
    """The greeting line, with the frame name as a calm second line when the
    person has more than one frame."""
    name = _frame_name()
    frame = (
        '<span class="home-greeting__frame">%s</span>' % escape_html(name)) if name else ""
    return (
        '<p class="home-greeting%s" aria-hidden="true" data-greeting '
        'data-greeting-morning="%s" data-greeting-afternoon="%s" '
        'data-greeting-evening="%s" data-greeting-night="%s">'
        '<span class="home-greeting__hello" data-greeting-text>%s</span>%s</p>'
    ) % (
        " home-greeting--framed" if name else "",
        escape_html(i18n.t(GREETING_MORNING)), escape_html(i18n.t(GREETING_AFTERNOON)),
        escape_html(i18n.t(GREETING_EVENING)), escape_html(i18n.t(GREETING_NIGHT)),
        escape_html(i18n.t(GREETING_DEFAULT)), frame)


def trail_html(has_flight):
    """The plane on its dotted trail, or "" when the frame has no flight."""
    if not has_flight:
        return ""
    return (
        '<div class="home-trail" aria-hidden="true">'
        '<svg class="home-trail__svg" viewBox="0 0 320 56" focusable="false">'
        '<path class="home-trail__path" d="%s"/>'
        '<g transform="translate(296 14) rotate(-4)">'
        '<path class="home-trail__plane" d="%s"/></g></svg></div>'
    ) % (_TRAIL_PATH, _PLANE_PATH)
