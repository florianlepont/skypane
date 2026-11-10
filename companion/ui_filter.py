"""companion/ui_filter.py: the one filter-bar component Flights, Airlines
and Health's unresolved-prefix list share, driven client-side by
static/list-filter.js's `[data-filter-*]` attribute contract.

The bar is a search field (a magnifier, a 16px input, an inline clear
button), an optional segmented chip group, a count element, and a hidden-until-needed empty state with its
own Clear button. Everything is inert without a script: the unfiltered
list stays complete, and the chip group (which cannot filter anything
without one) stays hidden behind the `.js-gate` rule.
"""
import companion.i18n as i18n
from companion.ui_base import escape_html, icon_html

FILTER_CLEAR_LABEL = i18n.msg("common.clear_search", "Clear search")
FILTER_CLEAR_TEXT = i18n.msg("health.clear", "Clear")

# The quantity placeholder the script substitutes in the count template
# attribute. Not "%d": the template is rendered unformatted for the
# script, and the French-render scan treats a stray "%d" in a served page
# as a formatting bug.
COUNT_PLACEHOLDER = "#"

# The shared name of every chip radio group: they live outside any form
# and are never submitted, so the name only groups the radios.
FILTER_CHIP_GROUP_NAME = "filter_kind"


def _chips_html(chips, legend):
    """The segmented chip group: one visually-hidden radio per segment
    inside a whole-segment label and a short label. The
    first chip is checked and carries the empty kind (every row).
    `chips` is a sequence of `(kind, label_text)`.
    """
    parts = []
    for position, (kind, text) in enumerate(chips):
        parts.append(
            '<label class="filter-chip">'
            '<input type="radio" class="visually-hidden" name="%s" '
            'value="%s" data-filter-chip%s>'
            '<span class="filter-chip__box">'
            '<span class="filter-chip__text">%s</span>'
            "</span></label>" % (
                FILTER_CHIP_GROUP_NAME, escape_html(kind),
                " checked" if position == 0 else "", escape_html(text)))
    return (
        '<fieldset class="filter-bar__chips js-gate">'
        '<legend class="visually-hidden">%s</legend>%s</fieldset>'
    ) % (escape_html(legend), "".join(parts))


def chip_links_html(chips, aria_label):
    """The segmented chips as plain links (a navigation between filtered
    views of one list, no script): the same chip look as the filter bar's
    radios, wrapping onto a second row of the track on a narrow phone.
    `chips` is a sequence of `(href, label, current)` with `href` already
    escaped."""
    parts = []
    for href, label, current in chips:
        parts.append(
            '<a class="filter-chip%s" href="%s"%s>'
            '<span class="filter-chip__box"><span class="filter-chip__text">%s</span></span>'
            "</a>" % (
                " filter-chip--current" if current else "", href,
                ' aria-current="true"' if current else "", escape_html(label)))
    return '<nav class="filter-bar__chips filter-bar__chips--links" aria-label="%s">%s</nav>' % (
        escape_html(aria_label), "".join(parts))


def _search_html(input_id, label, placeholder, server=None):
    """The visually-hidden label, the field (a magnifier, the 16px input)
    and its inline clear button: the one search control both bar forms use.
    The input has no `name` (never submitted by a form) and carries the
    autofill-suppression attributes the WebKit contacts heuristic needs
    (see history_page.py's `_FILTER_INPUT_ID` note). A placeholder stands in
    for the visible label, which stays as a visually-hidden `<label for>`.
    With `server` (a `(name, value, clear_href)` triple) the field is a real
    form field the server answers: it is named, holds the current text, is
    marked `data-flights-search` instead of `data-filter-input` (list-filter.js
    does not filter it) and its clear control is a link to `clear_href`."""
    if server is None:
        field = "data-filter-input"
        clear = (
            '<button type="button" class="filter-bar__clear" data-filter-clear '
            'aria-label="%s">%s</button>') % (
                escape_html(i18n.t(FILTER_CLEAR_LABEL)), icon_html("icon-close", 14))
    else:
        name, value, clear_href = server
        field = 'name="%s" value="%s" maxlength="60" data-flights-search' % (
            escape_html(name), escape_html(value))
        clear = (
            '<a class="filter-bar__clear" href="%s" data-flights-clear '
            'aria-label="%s">%s</a>') % (
                escape_html(clear_href), escape_html(i18n.t(FILTER_CLEAR_LABEL)),
                icon_html("icon-close", 14))
    return (
        '<label class="visually-hidden" for="%s">%s</label>'
        '<div class="filter-bar__search">'
        '<input type="search" id="%s" placeholder="%s" autocomplete="off" '
        'spellcheck="false" autocapitalize="characters" %s>'
        "%s%s"
        "</div>"
    ) % (
        escape_html(input_id), escape_html(label),
        escape_html(input_id), escape_html(placeholder), field,
        icon_html("icon-search", 20), clear)


def filter_title_search_html(input_id, label, placeholder):
    """The search field for a page header's title row: a magnifier at the
    row's right edge that opens into the field in place, over the title and
    without moving anything below (the bar's own search is then omitted
    with `search_in_bar=False`)."""
    return '<div class="filter-bar filter-bar--title">%s</div>' % _search_html(
        input_id, label, placeholder)


def filter_title_search_form_html(
        input_id, label, placeholder, form_id, action, name, value, clear_href):
    """The same title-row search as a GET form the server answers: `name`
    and `value` are the field's, `clear_href` the address that clears it.
    Other controls join the form with `form="<form_id>"`, so Enter sends the
    search together with them and the page works without a script."""
    return (
        '<form class="filter-bar filter-bar--title" id="%s" method="get" action="%s" '
        'role="search" data-flights-form%s>%s</form>'
    ) % (escape_html(form_id), escape_html(action), " data-filter-active" if value else "", _search_html(
        input_id, label, placeholder, (name, value, clear_href)))


def filter_empty_html(heading, body, action_html, attrs):
    """The soft card a search or filter that matches nothing shows: a search
    glyph in a halo, the heading, the body and the card's own Clear action
    (`action_html`, the caller's already-safe markup). `attrs` are the raw
    attributes that mark it (`data-filter-empty hidden` for the one a script
    reveals, `data-flights-empty` for the one the server renders)."""
    return (
        '<div class="empty-state empty-state--filter" %s>'
        '<span class="empty-state__halo">%s</span>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "%s</div>"
    ) % (attrs, icon_html("icon-search", 22), escape_html(heading), escape_html(body), action_html)


def filter_bar_html(
        input_id, label, placeholder, count_template, count_total,
        shown, empty_heading, empty_body, chips=None, chips_legend="",
        search_in_bar=True):
    """The filter bar plus its empty state, as one markup string.

    `chips` (optional) adds the segmented group and switches the search
    field to its collapsing form; omit it for the plain search pill.
    `search_in_bar=False` leaves the search field out: the page places it
    itself with `filter_title_search_html()` under the same `input_id`.
    `count_total` and `shown` seed the live count the script rewrites
    from `count_template` ("%d of %d shown", already translated; served
    to the script with `#` for each `%d`).
    Every argument is escaped here, never by the caller.
    """
    count_text = count_template % (shown, count_total)
    chips_markup = _chips_html(chips, chips_legend) if chips else ""
    modifier = " filter-bar--chips" if chips else ""
    search_markup = _search_html(input_id, label, placeholder) if search_in_bar else ""
    return (
        '<div class="filter-bar%s">'
        "%s"
        "%s"
        '<div class="filter-bar__meta">'
        '<span class="filter-bar__count" data-filter-count role="status" '
        'data-filter-count-template="%s">%s</span>'
        "</div>"
        "</div>"
        "%s"
    ) % (
        modifier, search_markup, chips_markup,
        escape_html(count_template.replace("%d", COUNT_PLACEHOLDER)),
        escape_html(count_text),
        filter_empty_html(
            empty_heading, empty_body,
            '<button type="button" class="btn btn--secondary" data-filter-clear data-filter-clear-all>%s</button>'
            % escape_html(i18n.t(FILTER_CLEAR_TEXT)),
            "data-filter-empty hidden"),
    )


def sort_menu_html(param, values, current, label, radio_attrs="", summary_attrs=""):
    """The sort as a small menu shared by the Airlines collection and the
    Flights list: an icon button naming the current order opens a panel of
    radio rows, the chosen one marked with a tick. The radios are plain form
    fields, so without a script the page's Apply button sends the choice.
    `values` is a sequence of (value, message) pairs; `radio_attrs` is extra
    markup for every radio (a `form=` attribute, script hooks) and
    `summary_attrs` for the menu button."""
    name = "%s: %s" % (i18n.t(label), i18n.t(dict(values)[current]))
    options = "".join(
        '<label class="collection-sort__option"><input type="radio" class="visually-hidden" '
        'name="%s" value="%s"%s%s><span class="collection-sort__row">'
        '<span>%s</span>%s</span></label>' % (
            param, value, " checked" if value == current else "", radio_attrs,
            escape_html(i18n.t(text)), icon_html("icon-check", 16))
        for value, text in values)
    return (
        '<details class="row-menu collection-sort"><summary class="row-menu__toggle '
        'collection-sort__toggle" aria-label="%s" title="%s"%s>%s</summary>'
        '<div class="row-menu__panel collection-sort__panel" role="radiogroup" '
        'aria-label="%s">%s</div></details>'
    ) % (escape_html(name), escape_html(name), summary_attrs, icon_html("icon-sort", 20),
         escape_html(i18n.t(label)), options)
