"""companion/ui_filter.py: the one filter-bar component Flights, Airlines
and Health's unresolved-prefix list share, driven client-side by
static/list-filter.js's `[data-filter-*]` attribute contract.

The bar is a search field (a magnifier, a 16px input, an inline clear
button), an optional segmented chip group whose segments carry live
counts, a count element, and a hidden-until-needed empty state with its
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
    inside a whole-segment label, a live count and a short label. The
    first chip is checked and carries the empty kind (every row).
    `chips` is a sequence of `(kind, label_text, count)`.
    """
    parts = []
    for position, (kind, text, count) in enumerate(chips):
        parts.append(
            '<label class="filter-chip">'
            '<input type="radio" class="visually-hidden" name="%s" '
            'value="%s" data-filter-chip%s>'
            '<span class="filter-chip__box">'
            '<span class="filter-chip__count" data-filter-chip-count>%d</span>'
            '<span class="filter-chip__text">%s</span>'
            "</span></label>" % (
                FILTER_CHIP_GROUP_NAME, escape_html(kind),
                " checked" if position == 0 else "", count, escape_html(text)))
    return (
        '<fieldset class="filter-bar__chips js-gate">'
        '<legend class="visually-hidden">%s</legend>%s</fieldset>'
    ) % (escape_html(legend), "".join(parts))


def filter_bar_html(
        input_id, label, placeholder, count_template, count_total,
        shown, empty_heading, empty_body, chips=None, chips_legend="",
        extra_html=""):
    """The filter bar plus its empty state, as one markup string.

    `chips` (optional) adds the segmented group and switches the search
    field to its collapsing form; omit it for the plain search pill.
    `count_total` and `shown` seed the live count the script rewrites
    from `count_template` ("%d of %d shown", already translated; served
    to the script with `#` for each `%d`).
    `extra_html` is the caller's own already-safe markup, placed in the
    bar's trailing meta group beside the count. Every other argument is
    escaped here, never by the caller.

    The input has no `name` (never submitted by a form) and carries the
    autofill-suppression attributes the WebKit contacts heuristic needs
    (see history_page.py's `_FILTER_INPUT_ID` note). A placeholder
    stands in for the visible label, which stays as a visually-hidden
    `<label for>`.
    """
    count_text = count_template % (shown, count_total)
    chips_markup = _chips_html(chips, chips_legend) if chips else ""
    modifier = " filter-bar--chips" if chips else ""
    return (
        '<div class="filter-bar%s">'
        '<label class="visually-hidden" for="%s">%s</label>'
        '<div class="filter-bar__search">'
        '<input type="search" id="%s" placeholder="%s" autocomplete="off" '
        'spellcheck="false" autocapitalize="characters" data-filter-input>'
        "%s"
        '<button type="button" class="filter-bar__clear" data-filter-clear '
        'aria-label="%s">%s</button>'
        "</div>"
        "%s"
        '<div class="filter-bar__meta">'
        '<span class="filter-bar__count" data-filter-count role="status" '
        'data-filter-count-template="%s">%s</span>'
        "%s"
        "</div>"
        "</div>"
        '<div class="empty-state empty-state--filter" data-filter-empty hidden>'
        '<span class="empty-state__halo">%s</span>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        '<button type="button" data-filter-clear data-filter-clear-all>%s</button>'
        "</div>"
    ) % (
        modifier, escape_html(input_id), escape_html(label),
        escape_html(input_id), escape_html(placeholder),
        icon_html("icon-search", 20),
        escape_html(i18n.t(FILTER_CLEAR_LABEL)), icon_html("icon-close", 14),
        chips_markup,
        escape_html(count_template.replace("%d", COUNT_PLACEHOLDER)),
        escape_html(count_text), extra_html,
        icon_html("icon-search", 22),
        escape_html(empty_heading), escape_html(empty_body),
        escape_html(i18n.t(FILTER_CLEAR_TEXT)),
    )
