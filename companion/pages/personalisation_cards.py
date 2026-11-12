"""The Personalisation page's body: the frame's Layout card, one navigation
(Departures, Arrivals, Special looks, Calendar) and the one view it points at.
Each view has its own address; Departures is the page's own address. The layout
is one setting per frame, so its card sits above the navigation and shows
whichever view is open.

Departures and Arrivals are two views of the look picker. Special looks and
Calendar are one glass group of rows with an add row under it. Every view is a section carrying the
dirty-state attribute, so the save bar names the sections that changed. The
views only compose markup built by the settings modules; none of them decides
what is saved.

Four more addresses are pages that edit one thing with a floating Cancel and
Save bar: a new special look, an edited special look, the calendar connection
(each posting to a route of its own, picture on the left and options on the
right) and the calendar's look (the settings route, the look picker). Each belongs to the Special looks or Calendar view
(`PARENT_VIEWS`), which the navigation marks as current.
"""
from companion import i18n, theme_preview, ui_save_bar, ui_segmented
from companion import device_scope
import companion.layout as layout
from companion.layout import escape_html

from companion.settings import calendar as calendar_settings
from companion.settings import layout_picker
from companion.settings import rules
from companion.settings.form import DIRTY_SECTION_ATTR
from companion.settings.rules import SPECIAL_LOOKS_HEADING, special_looks_html
from companion.settings.theme import (
    COLOUR_USAGE_ARRIVALS, COLOUR_USAGE_CALENDAR, COLOUR_USAGE_DEPARTURES,
    FRAME_COLOURS_ROW_LABELS, departures_safe_theme_id, look_card_body_html, look_frame_html,
    look_sheet_html)
from server import screen_layouts

PAGE_ID = "personalisation"
NAV_LABEL = i18n.msg("display.personalisation_sections", "Style sections")

LOOK_TITLE = i18n.msg("look.look", "Look")
CALENDAR_TITLE = i18n.msg("look.calendar", "Calendar")

# One address per view. Departures keeps the page's original address.
VIEW_DEPARTURES = "departures"
VIEW_ARRIVALS = "arrivals"
VIEW_SPECIAL_LOOKS = "special-looks"
VIEW_CALENDAR = "calendar"
VIEW_LOOK_NEW = "special-look-new"
VIEW_LOOK_EDIT = "special-look-edit"
VIEW_CALENDAR_CONNECT = "calendar-connect"
VIEW_CALENDAR_LOOK = "calendar-look"
VIEW_ROUTES = {
    VIEW_DEPARTURES: layout.DISPLAY_ROUTE,
    VIEW_ARRIVALS: layout.DISPLAY_ARRIVALS_ROUTE,
    VIEW_SPECIAL_LOOKS: layout.DISPLAY_SPECIAL_LOOKS_ROUTE,
    VIEW_CALENDAR: layout.DISPLAY_CALENDAR_ROUTE,
    VIEW_LOOK_NEW: layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE,
    VIEW_LOOK_EDIT: layout.DISPLAY_SPECIAL_LOOK_EDIT_ROUTE,
    VIEW_CALENDAR_CONNECT: layout.DISPLAY_CALENDAR_CONNECT_ROUTE,
    VIEW_CALENDAR_LOOK: layout.DISPLAY_CALENDAR_LOOK_ROUTE,
}
# The pages that edit one thing, and the list view each one returns to.
PARENT_VIEWS = {
    VIEW_LOOK_NEW: VIEW_SPECIAL_LOOKS,
    VIEW_LOOK_EDIT: VIEW_SPECIAL_LOOKS,
    VIEW_CALENDAR_CONNECT: VIEW_CALENDAR,
    VIEW_CALENDAR_LOOK: VIEW_CALENDAR,
}
FORM_VIEWS = tuple(PARENT_VIEWS)
ROUTE_VIEWS = {route: view for view, route in VIEW_ROUTES.items()}
# The two views of the look picker, and the picture each one shows first.
LOOK_VIEW_USAGES = {
    VIEW_DEPARTURES: COLOUR_USAGE_DEPARTURES,
    VIEW_ARRIVALS: COLOUR_USAGE_ARRIVALS,
}
# The address that used to hold the Screen switch (now on Home) and the one
# that held the Layout view (now a card on every view) redirect to Departures.
RETIRED_VIEW_ROUTES = (layout.DISPLAY_SCREEN_ROUTE, layout.DISPLAY_LAYOUT_ROUTE)


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
        _look_body_html(values, errors, submitted, usage))


def _look_body_html(values, errors, submitted, usage):
    """The picker a frame's layout calls for: the five pairing cards on a
    giant-lettering layout, the three-axis look picker on the classic one."""
    layout_id = screen_layouts.normalise_layout_id(values["layout"])
    if screen_layouts.is_giant_layout(layout_id):
        return layout_picker.pairing_view_html(
            layout_id, values["theme_id"], values["theme_arriving"], errors, submitted, usage)
    return look_card_body_html(
        values["theme_id"], values["theme_arriving"], errors, submitted, usage)


def _layout_card(values, errors, submitted):
    """The frame-level Layout card: a section carrying the dirty-state
    attribute, so the save bar names it when the layout changed."""
    return layout_picker.layout_card_html(
        values["layout"], values["theme_id"], errors, submitted)


def _special_looks_card(ctx, sheet_html):
    return _card_html(
        "special-looks", i18n.t(SPECIAL_LOOKS_HEADING),
        special_looks_html(ctx, "") + sheet_html)


def _calendar_card(calendar_row_html):
    return _card_html(
        "calendar", i18n.t(CALENDAR_TITLE), '<ul class="special-list">%s</ul>' % calendar_row_html)


def _calendar_look_controls(values, errors):
    """The calendar look's picture and radio table, for the render that holds
    every view at once (no route serves it): the controls of the look page,
    without its form, sheet or bar."""
    return look_frame_html(
        COLOUR_USAGE_CALENDAR, values["calendar_theme_id"],
        departures_safe_theme_id(values["theme_id"], None), errors,
        theme_preview.FRAME_PREVIEW_STATE_DEPARTING, carries_departures=True)


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
    """The section navigation: one plain link per view, the current one marked
    (a form page marks the list it belongs to). A script adds the sliding
    highlight over it; the links work without."""
    view = PARENT_VIEWS.get(view, view)
    links = [
        (escape_html(device_scope.scoped(VIEW_ROUTES[slug])),
         "%s<span>%s</span>" % (layout.icon_html(icon), escape_html(i18n.t(title))),
         slug == view, ' data-pers-view="%s"' % slug)
        for slug, title, icon in _views()]
    return ui_segmented.segmented_links_html(
        links, i18n.t(NAV_LABEL), nav_attrs=' data-tabs="display"', carry=True)


def _bar_html(title, cancel_href, form_id, pending_label=None, shown=False):
    """The floating Cancel and Save bar of a form page. Cancel is a link back
    to the list; Save submits the page's form (`form=`). It appears once a
    field differs from the loaded value (always, without script), and from the
    start on a page redrawn with a refused value (`shown`)."""
    pending = (
        'data-pending-label="%s"' % escape_html(pending_label) if pending_label else "")
    return ui_save_bar.save_bar_html(
        form_id, cancel_href=cancel_href, title=title, save_attrs=pending,
        reveal_on_change=True, shown=shown)


def _back_html(parent_view):
    """The link above a form page that returns to its list."""
    title = i18n.t(dict((slug, label) for slug, label, _icon in _views())[parent_view])
    return (
        '<a class="form-back" href="%s">%s<span>%s</span></a>'
    ) % (escape_html(device_scope.scoped(VIEW_ROUTES[parent_view])),
         layout.icon_html("icon-chevron-right", 18), escape_html(title))


def _redrawn_with_error(ctx, errors):
    """True when the form page shows a refused value the person has to fix."""
    return bool(errors) or ctx.rule_draft is not None or ctx.calendar_sheet_error is not None


def _form_view(ctx, values, view, errors, scope_fields_html, submitted=None):
    """One form page: the link back to its list, the picture and options, and
    the floating bar."""
    parent = PARENT_VIEWS[view]
    cancel_href = device_scope.scoped(VIEW_ROUTES[parent])
    if view == VIEW_CALENDAR_LOOK:
        markup, title = calendar_settings.look_page_html(
            values["calendar_theme_id"], departures_safe_theme_id(values["theme_id"], None),
            errors, calendar_settings.LOOK_FORM_ID, calendar_settings.SETTINGS_POST_ROUTE,
            scope_fields_html, values["layout"], submitted)
        form_id, pending, extra = calendar_settings.LOOK_FORM_ID, None, ""
    elif view == VIEW_CALENDAR_CONNECT:
        error_message = (errors or {}).get("calendar_url") or {
            "invalid": calendar_settings.CALENDAR_ERROR_INVALID,
            "unreachable": calendar_settings.CALENDAR_ERROR_UNREACHABLE,
        }.get(ctx.calendar_sheet_error)
        markup, title, _submit = calendar_settings.connect_page_html(
            ctx.calendar_configured, ctx.calendar_drift, ctx.state_dir, error_message)
        form_id = calendar_settings.CONNECT_FORM_ID
        pending = i18n.t(calendar_settings.CALENDAR_CHECKING_TEXT)
        extra = ""
    else:
        edit = rules.edit_target(ctx) if view == VIEW_LOOK_EDIT else None
        if view == VIEW_LOOK_NEW and ctx.rule_draft is not None:
            from companion import flash  # late: flash imports the page modules
            errors = {"rule_key": flash.FLASH_MESSAGES[flash.FLASH_KEY_RULE_KEY_INVALID]}
            submitted = ctx.rule_draft
        markup, title, _submit = rules.rule_form_html(ctx, edit, errors, submitted)
        form_id, pending = rules.RULE_FORM_ID, None
        extra = look_sheet_html()
    return (
        '<div class="form-view">%s%s%s%s</div>'
    ) % (_back_html(parent), markup, extra,
         _bar_html(title, cancel_href, form_id, pending, shown=_redrawn_with_error(ctx, errors)))


def page_html(
        ctx, values, calendar_row_html, calendar_status, errors, submitted, view=None,
        scope_fields_html=""):
    """The Personalisation body: the Layout card, the navigation, then the one
    view it names.
    `view=None` renders every view in navigation order (one look view holding
    both pictures, one look sheet), for checks against every control at once;
    no route serves that.

    The Special looks and Calendar views carry the hidden look sheet their
    openers use; the look views' own sheet is the inline picker.
    """
    if view in FORM_VIEWS:
        return '<div class="personalisation">%s<div class="personalisation__view">%s</div></div>' % (
            _nav_html(view), _form_view(ctx, values, view, errors, scope_fields_html, submitted))
    sheet_html = look_sheet_html() if view is not None else ""
    usage = LOOK_VIEW_USAGES.get(view)
    parts = {
        VIEW_DEPARTURES: lambda: _look_view(values, errors, submitted, usage),
        VIEW_SPECIAL_LOOKS: lambda: _special_looks_card(ctx, sheet_html),
        VIEW_CALENDAR: lambda: _calendar_card(calendar_row_html) + (
            _calendar_look_controls(values, errors) if view is None else ""),
    }
    parts[VIEW_ARRIVALS] = parts[VIEW_DEPARTURES]
    shown = (view,) if view is not None else (
        VIEW_DEPARTURES, VIEW_SPECIAL_LOOKS, VIEW_CALENDAR)
    return '<div class="personalisation">%s%s<div class="personalisation__view">%s</div></div>' % (
        _layout_card(values, errors, submitted), _nav_html(view),
        "".join(parts[name]() for name in shown))
