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
import companion.ui_segmented as ui_segmented
from companion.ui_base import escape_html, icon_html

FILTER_CLEAR_LABEL = i18n.msg("common.clear_search", "Clear search")
FILTER_CLEAR_TEXT = i18n.msg("health.clear", "Clear")

# What a list says when the server could not be reached for a search, a
# filter, a sort or Load more: the page stays as it is.
LIST_OFFLINE_TEXT = i18n.msg(
    "common.couldn_t_update_the_list_check_your_connection",
    "Couldn't update the list — check your connection and try again.")
# The template list-filter.js clones into the page's alert region. Must
# equal OFFLINE_TEMPLATE_ATTR in static/list-filter.js.
LIST_OFFLINE_TEMPLATE_ATTR = "data-list-offline-template"

# The quantity placeholder the script substitutes in the count template
# attribute. Not "%d": the template is rendered unformatted for the
# script, and the French-render scan treats a stray "%d" in a served page
# as a formatting bug.
COUNT_PLACEHOLDER = "#"

# The shared name of every chip radio group: they live outside any form
# and are never submitted, so the name only groups the radios.
FILTER_CHIP_GROUP_NAME = "filter_kind"


def _chips_html(chips, legend, scroll=False, server=None):
    """The segmented chip group: one visually-hidden radio per segment
    inside a whole-segment label and a short label. The
    first chip is checked and carries the empty kind (every row).
    `chips` is a sequence of `(kind, label_text)`; a third item is a count
    shown after the label in a quieter weight. With `scroll` the group is the
    scrolling pill row (`filter-bar__chips--scroll`): separate pills on one
    line that scrolls sideways when they do not fit.
    With `server` (a `(name, current, attrs)` triple) the radios are fields of
    the page's GET form, named `name`, checked on `current` and carrying the
    extra attributes `attrs`; the group then works without a script (it is not
    gated). Otherwise they are the script-driven chips of `list-filter.js`."""
    parts = []
    for position, chip in enumerate(chips):
        kind, text = chip[0], chip[1]
        count = ('<span class="filter-chip__count">%s</span>' % escape_html(str(chip[2]))
                 if len(chip) > 2 else "")
        if server is None:
            radio = 'name="%s" value="%s" data-filter-chip%s' % (
                FILTER_CHIP_GROUP_NAME, escape_html(kind), " checked" if position == 0 else "")
        else:
            name, current, attrs = server
            radio = 'name="%s" value="%s"%s %s' % (
                name, escape_html(kind), " checked" if kind == current else "",
                attrs.replace("{kind}", kind or "all"))
        parts.append(
            '<label class="filter-chip"><input type="radio" class="visually-hidden" %s>'
            '<span class="filter-chip__box">'
            '<span class="filter-chip__text">%s</span>%s'
            "</span></label>" % (radio, escape_html(text), count))
    return (
        '<fieldset class="filter-bar__chips%s%s">'
        '<legend class="visually-hidden">%s</legend>%s</fieldset>'
    ) % (" filter-bar__chips--scroll" if scroll else "",
         "" if server is not None else " js-gate", escape_html(legend), "".join(parts))


def chip_links_html(chips, aria_label, tabs=""):
    """The segmented chips as plain links (a navigation between filtered
    views of one list, no script): the same chip look as the filter bar's
    radios, wrapping onto a second row of the track on a narrow phone.
    `chips` is a sequence of `(href, label, current)` with `href` already
    escaped. `tabs` names the strip for the shared tab behaviour (the sliding
    thumb) and marks it as the page's own strip, whose selection the page
    change carries across (a page shows one such strip at most)."""
    parts = []
    for href, label, current in chips:
        parts.append(
            '<a class="filter-chip%s" href="%s"%s>'
            '<span class="filter-chip__box"><span class="filter-chip__text">%s</span></span>'
            "</a>" % (
                " filter-chip--current" if current else "", href,
                ' aria-current="true"' if current else "", escape_html(label)))
    strip = (' data-tabs="%s"%s' % (escape_html(tabs), ui_segmented.CARRY_ATTR)) if tabs else ""
    return '<nav class="filter-bar__chips filter-bar__chips--links" aria-label="%s"%s>%s%s</nav>' % (
        escape_html(aria_label), strip, "".join(parts),
        ui_segmented.CARRY_END_HTML if tabs else "")


def _search_html(input_id, label, placeholder, server=None, named=None):
    """The visually-hidden label, the field (a magnifier, the 16px input)
    and its inline clear button: the one search control both bar forms use.
    The input has no `name` (never submitted by a form) and carries the
    autofill-suppression attributes the WebKit contacts heuristic needs
    (see history_page.py's `_FILTER_INPUT_ID` note). A placeholder stands in
    for the visible label, which stays as a visually-hidden `<label for>`.
    With `server` (a `(name, value, clear_href)` triple) the field is a real
    form field the server answers: it is named, holds the current text, is
    marked `data-flights-search` instead of `data-filter-input` (list-filter.js
    does not filter it) and its clear control is a link to `clear_href`.
    With `named` (a `(name, value, max_length)` triple) the field is the
    script-filtered one (`data-filter-input`) that is also a form field, so
    the server answers the same text when no script runs."""
    if server is None:
        field = "data-filter-input"
        if named is not None:
            field = 'name="%s" value="%s" maxlength="%d" data-filter-input' % (
                escape_html(named[0]), escape_html(named[1]), named[2])
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


def search_field_html(input_id, label, placeholder):
    """The search control alone (label, magnifier, field, clear button) for a
    list that filters in the page and is not part of a form."""
    return _search_html(input_id, label, placeholder)


def list_offline_template_html():
    """The translated error toast a list that asks the server for its rows
    shows when the request never got an answer. It has no role of its own:
    the live region it is cloned into announces it."""
    # Imported here: ui_components reaches this module again through layout.
    from companion.ui_components import TOAST_TONE_ERROR, split_toast_message, toast_html
    title, detail = split_toast_message(i18n.t(LIST_OFFLINE_TEXT))
    return "<template %s>%s</template>" % (LIST_OFFLINE_TEMPLATE_ATTR, toast_html(
        title, detail, tone=TOAST_TONE_ERROR, role="", dismiss_href=True))


def server_search_html(input_id, label, placeholder, name, value, clear_href):
    """The search control of a list the server answers: a named field holding
    the current text, with a clear link to `clear_href`."""
    return _search_html(input_id, label, placeholder, (name, value, clear_href))


def named_search_html(input_id, label, placeholder, name, value, max_length):
    """The search control of a list that filters in the page and is also a
    field of the page's GET form, so the same text works without a script."""
    return _search_html(input_id, label, placeholder, named=(name, value, max_length))


def chips_row_html(chips, legend, server=None):
    """The chips of the shared filter controls: always the scrolling pill row,
    with a count after each label. `server` is as in `_chips_html`."""
    return _chips_html(chips, legend, scroll=True, server=server)


def info_menu_html(label, body_html):
    """The info button that ends the first row of the filter controls: an icon
    button naming `label` opens a small panel holding `body_html` (a native
    <details> that the shared menu script closes on Escape or an outside tap)."""
    label = escape_html(i18n.t(label))
    return (
        '<details class="row-menu filter-info"><summary class="row-menu__toggle" '
        'aria-label="%s" title="%s">%s</summary>'
        '<div class="row-menu__panel filter-info__panel">%s</div></details>'
    ) % (label, label, icon_html("icon-info", 20), body_html)


def controls_html(action, search_html, sort_html, info_html, chips_html, apply_text,
                  attrs="", extra_html=""):
    """The one filter and search module of Flights and Airlines, a GET form:
    row 1 is the search field (taking the remaining width), the sort menu and
    the info button; row 2 is the filter chips with their counts. The Apply
    button is how the form is sent without a script. `attrs` are the page's
    own raw form attributes (its script hooks) and `extra_html` more markup
    inside the form (the offline notice template)."""
    return (
        '<form class="filter-bar filter-bar--scroll-chips filter-controls" method="get" '
        'action="%s" role="search"%s>'
        '<div class="filter-controls__row">%s%s%s</div>%s'
        '<button type="submit" class="filter-controls__apply">%s</button>%s</form>'
    ) % (escape_html(action), attrs, search_html, sort_html, info_html, chips_html,
         escape_html(apply_text), extra_html)


def count_line_html(text, template="", attrs=""):
    """The one line that counts the rows under the filter controls of Flights
    and Airlines ("34 of 148 flights"): a single status paragraph, the form's
    next sibling. `text` and `template` (the translated text with a `#` for
    each number, which the live filter rewrites) are escaped here. `attrs` is
    the caller's own raw script hook, such as ` data-flights-view`: it is
    inserted verbatim, so pass only a literal, never user input."""
    template_attr = (' data-filter-count-template="%s"' % escape_html(template)) if template else ""
    return '<p class="filter-count" data-filter-count%s role="status"%s>%s</p>' % (
        attrs, template_attr, escape_html(text))


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
        search_in_bar=True, chips_scroll=False):
    """The filter bar plus its empty state, as one markup string.

    `chips` (optional) adds the segmented group and switches the search
    field to its collapsing form; omit it for the plain search pill.
    `chips_scroll=True` renders the chips as the scrolling pill row.
    `search_in_bar=False` leaves the search field out: the page places it
    itself with `filter_title_search_html()` under the same `input_id`.
    `count_total` and `shown` seed the live count the script rewrites
    from `count_template` ("%d of %d shown", already translated; served
    to the script with `#` for each `%d`).
    Every argument is escaped here, never by the caller.
    """
    count_text = count_template % (shown, count_total)
    chips_markup = _chips_html(chips, chips_legend, chips_scroll) if chips else ""
    modifier = " filter-bar--chips" if chips else ""
    if chips and chips_scroll:
        modifier += " filter-bar--scroll-chips"
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
