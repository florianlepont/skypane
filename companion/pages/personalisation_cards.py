"""The Personalisation page's body: one navigation (Departures, Arrivals,
Special looks, Calendar) and the one view it points at. Each view has its own
address; Departures is the page's own address.

Departures and Arrivals are two views of the look picker. Special looks and
Calendar are one glass group of rows with an add row under it. Every view is a section carrying the
dirty-state attribute, so the save bar names the sections that changed. The
views only compose markup built by the settings modules; none of them decides
what is saved.
"""
from companion import i18n
from companion import device_scope
import companion.layout as layout
from companion.layout import escape_html

from companion.settings.form import DIRTY_SECTION_ATTR
from companion.settings.rules import SPECIAL_LOOKS_HEADING, special_looks_html
from companion.settings.theme import (
    COLOUR_USAGE_ARRIVALS, COLOUR_USAGE_DEPARTURES, FRAME_COLOURS_ROW_LABELS,
    look_card_body_html, look_sheet_html)

PAGE_ID = "personalisation"
NAV_LABEL = i18n.msg("display.personalisation_sections", "Personalisation sections")

LOOK_TITLE = i18n.msg("look.look", "Look")
CALENDAR_TITLE = i18n.msg("look.calendar", "Calendar")

# One address per view. Departures keeps the page's original address.
VIEW_DEPARTURES = "departures"
VIEW_ARRIVALS = "arrivals"
VIEW_SPECIAL_LOOKS = "special-looks"
VIEW_CALENDAR = "calendar"
VIEW_ROUTES = {
    VIEW_DEPARTURES: layout.DISPLAY_ROUTE,
    VIEW_ARRIVALS: layout.DISPLAY_ARRIVALS_ROUTE,
    VIEW_SPECIAL_LOOKS: layout.DISPLAY_SPECIAL_LOOKS_ROUTE,
    VIEW_CALENDAR: layout.DISPLAY_CALENDAR_ROUTE,
}
ROUTE_VIEWS = {route: view for view, route in VIEW_ROUTES.items()}
# The two views of the look picker, and the picture each one shows first.
LOOK_VIEW_USAGES = {
    VIEW_DEPARTURES: COLOUR_USAGE_DEPARTURES,
    VIEW_ARRIVALS: COLOUR_USAGE_ARRIVALS,
}
# The address that used to hold the Screen switch (now on Home) redirects here.
RETIRED_VIEW_ROUTES = (layout.DISPLAY_SCREEN_ROUTE,)


def _card_html(slug, title, body_html):
    """One list view: a section named after `slug` whose title stays for
    assistive technology and the save bar, then the body. The body is a
    glass group of rows, so the section carries no card chrome of its own."""
    return (
        '<section class="page-section personalisation-card personalisation-card--list" '
        'id="%s-%s" aria-labelledby="%s-%s-title" %s="%s">'
        '<h2 class="text-heading personalisation-card__title" id="%s-%s-title">%s</h2>'
        "%s</section>"
    ) % (
        PAGE_ID, slug, PAGE_ID, slug, DIRTY_SECTION_ATTR, escape_html(title),
        PAGE_ID, slug, escape_html(title), body_html)


def _look_view(values, errors, submitted, usage):
    """A look view: no card chrome, the picker is the page. The title stays
    for assistive technology and names the section in the save bar. `usage`
    is the picture shown, or None for both."""
    title = i18n.t(LOOK_TITLE)
    return (
        '<section class="personalisation-look" id="%s-look" aria-labelledby="%s-look-title" %s="%s">'
        '<h2 class="visually-hidden" id="%s-look-title">%s</h2>%s</section>'
    ) % (
        PAGE_ID, PAGE_ID, DIRTY_SECTION_ATTR, escape_html(title),
        PAGE_ID, escape_html(title),
        look_card_body_html(
            values["theme_id"], values["theme_arriving"], errors, submitted, usage))


def _special_looks_card(ctx, sheet_html):
    return _card_html(
        "special-looks", i18n.t(SPECIAL_LOOKS_HEADING),
        special_looks_html(ctx, "") + sheet_html)


def _calendar_card(calendar_row_html, sheet_html):
    return _card_html(
        "calendar", i18n.t(CALENDAR_TITLE),
        '<ul class="special-list">%s</ul>' % calendar_row_html + sheet_html)


def _views():
    """(slug, title message, icon id) of the four views in navigation order."""
    return (
        (VIEW_DEPARTURES, FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_DEPARTURES], "icon-plane"),
        (VIEW_ARRIVALS, FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_ARRIVALS], "icon-plane"),
        (VIEW_SPECIAL_LOOKS, SPECIAL_LOOKS_HEADING, "icon-star"),
        (VIEW_CALENDAR, CALENDAR_TITLE, "icon-calendar"))


def view_for_route(route):
    """The view an address names: an unknown address is Departures."""
    return ROUTE_VIEWS.get(route, VIEW_DEPARTURES)


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
    """The Personalisation body: the navigation, then the one view it names.
    `view=None` renders every view in navigation order (one look view holding
    both pictures, one look sheet), for checks against every control at once;
    no route serves that.

    The Special looks and Calendar views carry the hidden look sheet their
    openers use; the look views' own sheet is the inline picker.
    """
    sheet_html = look_sheet_html() if view is not None else ""
    usage = LOOK_VIEW_USAGES.get(view)
    parts = {
        VIEW_DEPARTURES: lambda: _look_view(values, errors, submitted, usage),
        VIEW_SPECIAL_LOOKS: lambda: _special_looks_card(ctx, sheet_html),
        VIEW_CALENDAR: lambda: _calendar_card(calendar_row_html, sheet_html),
    }
    parts[VIEW_ARRIVALS] = parts[VIEW_DEPARTURES]
    shown = (view,) if view is not None else (
        VIEW_DEPARTURES, VIEW_SPECIAL_LOOKS, VIEW_CALENDAR)
    return '<div class="personalisation">%s<div class="personalisation__view">%s</div></div>' % (
        _nav_html(view), "".join(parts[name]() for name in shown))
