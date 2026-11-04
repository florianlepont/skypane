"""The Personalisation page's body: an "On this page" list and four cards in
a fixed order (Look, Special looks, Calendar, Screen), each with a title and
a muted line stating its current value.

Every card is a section carrying the dirty-state attribute, so the save bar
names the sections that changed. The cards only compose markup built by the
settings modules; none of them decides what is saved.
"""
from companion import i18n
from companion import ui_components
import companion.layout as layout
from companion.layout import escape_html
from server import device_config
from server.plane import colour_rules

from companion.settings import look
from companion.settings.form import DIRTY_SECTION_ATTR
from companion.settings.rules import SPECIAL_LOOKS_HEADING, special_looks_html
from companion.settings.theme import look_card_body_html

PAGE_ID = "personalisation"
NAV_LABEL = i18n.msg("display.on_this_page", "On this page")
CURRENT_LINE = i18n.msg("display.current_value", "Current: %s")

LOOK_TITLE = i18n.msg("look.look", "Look")
CALENDAR_TITLE = i18n.msg("look.calendar", "Calendar")
SCREEN_TITLE = i18n.msg("health.screen", "Screen")

SPECIAL_LOOKS_NONE = i18n.msg("display.special_looks_none", "No special looks yet")
SPECIAL_LOOKS_ONE = i18n.msg("display.special_looks_one", "1 special look")
SPECIAL_LOOKS_MANY = i18n.msg("display.special_looks_many", "%d special looks")
CALENDAR_CONNECTED = i18n.msg("display.calendar_connected", "Connected")
CALENDAR_NOT_CONNECTED = i18n.msg(
    "display.calendar_not_connected", "No calendar connected")
SCREEN_ON = i18n.msg("display.on", "On")
SCREEN_OFF = i18n.msg("display.off", "Off")

QUICK_DISPLAY_ROUTE = "/quick/display"
SCREEN_TITLE_ID = "personalisation-screen-title"
SCREEN_STATE_ID = "personalisation-screen-state"


def _current(value):
    return i18n.t(CURRENT_LINE) % value


def _special_looks_count(ctx):
    registry = ctx.colour_rules
    if not isinstance(registry, dict):
        return 0
    return len(colour_rules.rule_rows(registry))


def _special_looks_value(count):
    if count == 0:
        return i18n.t(SPECIAL_LOOKS_NONE)
    if count == 1:
        return i18n.t(SPECIAL_LOOKS_ONE)
    return i18n.t(SPECIAL_LOOKS_MANY) % count


def _card_html(slug, title, current_html, body_html):
    """One card: a section named after `slug`, its 16px title, the muted
    current-value line (`current_html` is markup already escaped by the
    caller) and the body."""
    return (
        '<section class="page-section personalisation-card" id="%s-%s" '
        'aria-labelledby="%s-%s-title" %s="%s">'
        '<h2 class="text-heading personalisation-card__title" id="%s-%s-title">%s</h2>'
        "%s%s</section>"
    ) % (
        PAGE_ID, slug, PAGE_ID, slug, DIRTY_SECTION_ATTR, escape_html(title),
        PAGE_ID, slug, escape_html(title), current_html, body_html)


def _current_line_html(value):
    return '<p class="text-label section-caption personalisation-card__current">%s</p>' % (
        escape_html(_current(value)))


def _look_card(values, errors, submitted):
    title = i18n.t(LOOK_TITLE)
    theme_id = values["theme_id"]
    shown = theme_id if theme_id in device_config.THEMES else None
    sentence = look.look_sentence(shown) if shown else ""
    return _card_html(
        "look", title, _current_line_html(sentence),
        look_card_body_html(theme_id, values["theme_arriving"], errors, submitted))


def _special_looks_card(ctx):
    return _card_html(
        "special-looks", i18n.t(SPECIAL_LOOKS_HEADING),
        _current_line_html(_special_looks_value(_special_looks_count(ctx))),
        special_looks_html(ctx, ""))


def _calendar_card(calendar_row_html, configured):
    value = i18n.t(CALENDAR_CONNECTED if configured else CALENDAR_NOT_CONNECTED)
    return _card_html(
        "calendar", i18n.t(CALENDAR_TITLE), _current_line_html(value),
        '<ul class="special-list">%s</ul>' % calendar_row_html)


def _screen_card(device_cfg):
    """The Screen card: the instant on/off switch, named by the card title.
    The muted current line is the switch's own state text, so it flips with
    the switch before the server answers."""
    is_on = device_cfg.get("display_enabled") is not False
    state_html = ui_components.quick_switch_state_html(
        SCREEN_STATE_ID, _current(i18n.t(SCREEN_ON)), _current(i18n.t(SCREEN_OFF)), is_on,
        extra_class="text-label section-caption personalisation-card__current")
    switch_html = ui_components.quick_switch_html(
        QUICK_DISPLAY_ROUTE, layout.DISPLAY_ROUTE, is_on, SCREEN_TITLE_ID, SCREEN_STATE_ID)
    title = i18n.t(SCREEN_TITLE)
    return (
        '<section class="page-section personalisation-card" id="%s-screen" '
        'aria-labelledby="%s" %s="%s" %s>'
        '<h2 class="text-heading personalisation-card__title" id="%s">%s</h2>'
        '<div class="personalisation-switch">%s%s</div></section>'
    ) % (
        PAGE_ID, SCREEN_TITLE_ID, DIRTY_SECTION_ATTR, escape_html(title),
        layout.QUICK_SWITCH_REGION_ATTR, SCREEN_TITLE_ID, escape_html(title),
        state_html, switch_html)


def _cards():
    """(slug, title message) of the four cards in page order."""
    return (
        ("look", LOOK_TITLE), ("special-looks", SPECIAL_LOOKS_HEADING),
        ("calendar", CALENDAR_TITLE), ("screen", SCREEN_TITLE))


def _nav_html():
    links = "".join(
        '<li><a class="personalisation__link" href="#%s-%s">%s</a></li>' % (
            PAGE_ID, slug, escape_html(i18n.t(title)))
        for slug, title in _cards())
    return (
        '<nav class="personalisation__nav" aria-label="%s">'
        '<p class="text-label section-caption personalisation__nav-title" aria-hidden="true">%s</p>'
        '<ul class="personalisation__links">%s</ul></nav>'
    ) % (escape_html(i18n.t(NAV_LABEL)), escape_html(i18n.t(NAV_LABEL)), links)


def page_html(ctx, values, calendar_row_html, calendar_status, errors, submitted):
    """The whole Personalisation body: the nav list, then Look, Special
    looks, Calendar and Screen."""
    return (
        '<div class="personalisation">%s<div class="personalisation__cards">%s%s%s%s</div></div>'
    ) % (
        _nav_html(),
        _look_card(values, errors, submitted),
        _special_looks_card(ctx),
        _calendar_card(calendar_row_html, calendar_status["calendar_configured"]),
        _screen_card(values["device_cfg"]))
