"""The Personalisation page's body: a section navigation (Look, Special
looks, Calendar, Screen) and the one view it points at. Each view has its own
address; the Look view is the page's own address.

The Look view is the look picker. The other three are cards with a title and a
muted line stating the current value. Every view is a section carrying the
dirty-state attribute, so the save bar names the sections that changed. The
views only compose markup built by the settings modules; none of them decides
what is saved.
"""
from companion import i18n
from companion import device_scope
from companion import ui_components
import companion.layout as layout
from companion.layout import escape_html
from server.plane import colour_rules

from companion.settings.form import DIRTY_SECTION_ATTR
from companion.settings.calendar import CALENDAR_EMPTY_HEADING
from companion.settings.rules import (
    SPECIAL_LOOKS_EMPTY_HEADING, SPECIAL_LOOKS_HEADING, special_looks_html)
from companion.settings.theme import look_card_body_html, look_sheet_html

PAGE_ID = "personalisation"
NAV_LABEL = i18n.msg("display.personalisation_sections", "Personalisation sections")
CURRENT_LINE = i18n.msg("display.current_value", "Current: %s")

LOOK_TITLE = i18n.msg("look.look", "Look")
CALENDAR_TITLE = i18n.msg("look.calendar", "Calendar")
SCREEN_TITLE = i18n.msg("health.screen", "Screen")

SPECIAL_LOOKS_NONE = SPECIAL_LOOKS_EMPTY_HEADING
SPECIAL_LOOKS_ONE = i18n.msg("display.special_looks_one", "1 special look")
SPECIAL_LOOKS_MANY = i18n.msg("display.special_looks_many", "%d special looks")
CALENDAR_CONNECTED = i18n.msg("display.calendar_connected", "Connected")
CALENDAR_NOT_CONNECTED = CALENDAR_EMPTY_HEADING
SCREEN_ON = i18n.msg("display.on", "On")
SCREEN_OFF = i18n.msg("display.off", "Off")

QUICK_DISPLAY_ROUTE = "/quick/display"

# One address per view. The Look view keeps the page's original address.
VIEW_LOOK = "look"
VIEW_SPECIAL_LOOKS = "special-looks"
VIEW_CALENDAR = "calendar"
VIEW_SCREEN = "screen"
VIEW_ROUTES = {
    VIEW_LOOK: layout.DISPLAY_ROUTE,
    VIEW_SPECIAL_LOOKS: layout.DISPLAY_SPECIAL_LOOKS_ROUTE,
    VIEW_CALENDAR: layout.DISPLAY_CALENDAR_ROUTE,
    VIEW_SCREEN: layout.DISPLAY_SCREEN_ROUTE,
}
ROUTE_VIEWS = {route: view for view, route in VIEW_ROUTES.items()}
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


def _look_view(values, errors, submitted):
    """The Look view: no card chrome, the picker is the page. The title stays
    for assistive technology and names the section in the save bar."""
    title = i18n.t(LOOK_TITLE)
    return (
        '<section class="personalisation-look" id="%s-look" aria-labelledby="%s-look-title" %s="%s">'
        '<h2 class="visually-hidden" id="%s-look-title">%s</h2>%s</section>'
    ) % (
        PAGE_ID, PAGE_ID, DIRTY_SECTION_ATTR, escape_html(title),
        PAGE_ID, escape_html(title),
        look_card_body_html(values["theme_id"], values["theme_arriving"], errors, submitted))


def _special_looks_card(ctx, sheet_html):
    return _card_html(
        "special-looks", i18n.t(SPECIAL_LOOKS_HEADING),
        _current_line_html(_special_looks_value(_special_looks_count(ctx))),
        special_looks_html(ctx, "") + sheet_html)


def _calendar_card(calendar_row_html, configured, sheet_html):
    value = i18n.t(CALENDAR_CONNECTED if configured else CALENDAR_NOT_CONNECTED)
    return _card_html(
        "calendar", i18n.t(CALENDAR_TITLE), _current_line_html(value),
        '<ul class="special-list">%s</ul>' % calendar_row_html + sheet_html)


def _screen_card(device_cfg):
    """The Screen card: the instant on/off switch, named by the card title.
    The muted current line is the switch's own state text, so it flips with
    the switch before the server answers."""
    is_on = device_cfg.get("display_enabled") is not False
    state_html = ui_components.quick_switch_state_html(
        SCREEN_STATE_ID, _current(i18n.t(SCREEN_ON)), _current(i18n.t(SCREEN_OFF)), is_on,
        extra_class="text-label section-caption personalisation-card__current")
    switch_html = ui_components.quick_switch_html(
        QUICK_DISPLAY_ROUTE, VIEW_ROUTES[VIEW_SCREEN], is_on, SCREEN_TITLE_ID, SCREEN_STATE_ID)
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


def _views():
    """(slug, title message, icon id) of the four views in navigation order."""
    return (
        (VIEW_LOOK, LOOK_TITLE, "icon-palette"),
        (VIEW_SPECIAL_LOOKS, SPECIAL_LOOKS_HEADING, "icon-star"),
        (VIEW_CALENDAR, CALENDAR_TITLE, "icon-calendar"),
        (VIEW_SCREEN, SCREEN_TITLE, "icon-nav-display"))


def view_for_route(route):
    """The view an address names: an unknown address is the Look view."""
    return ROUTE_VIEWS.get(route, VIEW_LOOK)


def _nav_html(view):
    """The section navigation: one plain link per view, the current one marked.
    A script adds the sliding highlight over it; the links work without."""
    links = "".join(
        '<a class="personalisation-nav__link" href="%s" data-pers-view="%s"%s>%s<span>%s</span></a>' % (
            escape_html(device_scope.scoped(VIEW_ROUTES[slug])), slug,
            ' aria-current="page"' if slug == view else "",
            layout.icon_html(icon), escape_html(i18n.t(title)))
        for slug, title, icon in _views())
    return (
        '<nav class="personalisation-nav" aria-label="%s" data-pers-nav>'
        '<span class="personalisation-nav__thumb" data-pers-thumb aria-hidden="true"></span>%s</nav>'
    ) % (escape_html(i18n.t(NAV_LABEL)), links)


def page_html(ctx, values, calendar_row_html, calendar_status, errors, submitted, view=None):
    """The Personalisation body: the section navigation, then the one view it
    names. `view=None` renders all four views in navigation order (one look
    sheet, the Look view's), for checks against every control at once; no
    route serves that.

    The Special looks and Calendar views carry the hidden look sheet their
    openers use; the Look view's own sheet is the inline picker.
    """
    configured = calendar_status["calendar_configured"]
    sheet_html = look_sheet_html() if view is not None else ""
    parts = {
        VIEW_LOOK: lambda: _look_view(values, errors, submitted),
        VIEW_SPECIAL_LOOKS: lambda: _special_looks_card(ctx, sheet_html),
        VIEW_CALENDAR: lambda: _calendar_card(calendar_row_html, configured, sheet_html),
        VIEW_SCREEN: lambda: _screen_card(values["device_cfg"]),
    }
    shown = (view,) if view is not None else tuple(parts)
    return '<div class="personalisation">%s<div class="personalisation__view">%s</div></div>' % (
        _nav_html(view), "".join(parts[name]() for name in shown))
