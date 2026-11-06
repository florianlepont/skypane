"""The Home page title: a personal greeting.

The visible `<h1>` is the greeting ("Good morning, Florian" / "Bonjour
Florian"); its accessible name stays the page's plain name ("Home"/"Accueil",
also the document title), so screen readers, titles and no-script visitors
keep a stable page name. The server text is the neutral default; nav-dropdown.js
swaps in the wording for the viewer's local hour from the four
`data-greeting-*` attributes (morning 05-12, afternoon 12-17, evening 17-21,
night otherwise, the same edges as the sky). The first name comes from the
signed-in e-mail's local part, only when it has a separator (`.`, `_`, `-`,
`+`) so a handle such as "marcoalfinito" is never shown; with no usable name
the greeting is the bare wording. An e-mail address is never put in the title.
"""

import re

import companion.device_scope as device_scope
import companion.i18n as i18n
from companion import prefs
from companion.layout import escape_html
from companion.ui_shell import device_display_name

# The same id as the navigation label and the document title.
_PAGE_NAME = i18n.msg("nav.home", "Home")
GREETING_DEFAULT = i18n.msg("home.greeting_default", "Hello")
GREETING_WITH_NAME = i18n.msg("home.greeting_with_name", "%s, %s")
GREETING_MORNING = i18n.msg("home.greeting_morning", "Good morning")
GREETING_AFTERNOON = i18n.msg("home.greeting_afternoon", "Good afternoon")
GREETING_EVENING = i18n.msg("home.greeting_evening", "Good evening")
GREETING_NIGHT = i18n.msg("home.greeting_night", "Good night")

_SEPARATORS = re.compile(r"[._+\-]+")


def first_name(email):
    """The first name read from `email`'s local part, or "" when it cannot be
    told from a handle: the local part needs a separator, and the first token
    must be letters only (at least two) to count as a name."""
    local = (email or "").split("@", 1)[0]
    if not _SEPARATORS.search(local):
        return ""
    token = next((part for part in _SEPARATORS.split(local) if part), "")
    return token.title() if len(token) >= 2 and token.isalpha() else ""


def _viewer_first_name():
    return first_name(prefs.current_principal_email())


def _frame_name():
    """The active frame's name when the person has several frames, else ""."""
    device = device_scope.current_device()
    if device is None or len(device_scope.switcher_entries()) < 2:
        return ""
    return device_display_name(device)


def _wording(greeting, name):
    word = i18n.t(greeting)
    return i18n.t(GREETING_WITH_NAME) % (word, name) if name else word


def title_html():
    """The greeting `<h1>`: visible greeting text, accessible name "Home"."""
    name = _viewer_first_name()
    return (
        '<h1 class="page-title page-title--greeting" aria-label="%s" data-greeting '
        'data-greeting-morning="%s" data-greeting-afternoon="%s" '
        'data-greeting-evening="%s" data-greeting-night="%s">'
        '<span data-greeting-text>%s</span></h1>'
    ) % (
        escape_html(i18n.t(_PAGE_NAME)),
        escape_html(_wording(GREETING_MORNING, name)),
        escape_html(_wording(GREETING_AFTERNOON, name)),
        escape_html(_wording(GREETING_EVENING, name)),
        escape_html(_wording(GREETING_NIGHT, name)),
        escape_html(_wording(GREETING_DEFAULT, name)))


def frame_line_html():
    """The active frame's name as a second line under the title, for people
    with several frames; "" otherwise."""
    name = _frame_name()
    if not name:
        return ""
    return '<p class="home-greeting__frame">%s</p>' % escape_html(name)
