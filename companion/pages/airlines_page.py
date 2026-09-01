"""companion/pages/airlines_page.py — an illustration gallery over the
panel renderer's own airline art (D-13 through D-17, 06.6.4.1-CONTEXT.md).

Presentation-only: reads exactly one public accessor,
`server.plane.illustrations.target_variants_by_airline()`, and touches no
database and no poll-state file — the gallery renders the full static
curated list from `_ILLUSTRATION_TARGETS`, never a detection-history
cross-reference (D-17: this module opens no database and reads no poll
state).

The unresolved-callsign-prefix registry (formerly CFG-04) and the
resolution-rate statistics breakdown (formerly CFG-08) that used to live
on this page moved to `companion/pages/health_page.py` in this same
phase (06.6.4.1, plan 04, D-11/D-12) — that is now the one page in the
app that renders them (D-13). A reader hunting for that content should
look there, not here. This move is complete as of plan 06 Task 3: this
module no longer imports the history-database module or the poll-state
module, and opens no database connection of any kind.
"""
import re

from companion.layout import escape_html
import companion.layout as layout
from server.plane import illustrations

# D-15: this page's illustration image route mirrors companion/app.py's
# own ILLUSTRATION_IMAGE_ROUTE_PREFIX exactly — duplicated, not imported,
# since app.py imports this module (the reverse import would be a
# cycle). Same duplicated-not-imported discipline this codebase already
# uses for its static-script route constants; pinned by a cross-module
# equality check in companion/test_status_pages.py.
ILLUSTRATION_ROUTE_PREFIX = "/illustration/"

GALLERY_PURPOSE_TEXT = (
    "Illustration reference for every airline this frame can recognize.")

CARD_IMAGE_ALT_TEMPLATE = "%s illustration"

# variant_chip_label()'s two shape-domain patterns. An alphanumeric type
# code is a letter prefix immediately followed by digits, optionally with
# a hyphenated numeric suffix ("a320", "atr72", "a330", "b737",
# "a350-1000"). Anything else is a word-form manufacturer shape
# ("embraer", "beechcraft1900d") — see variant_chip_label()'s own
# docstring for the domain-mismatch trap neither pattern may fall into.
_TYPE_CODE_RE = re.compile(r"^[a-z]+\d[\d-]*$")
_WORD_MODEL_RE = re.compile(r"^([a-z]+)(\d.*)$")


def variant_chip_label(shape):
    """Display transform for one fleet-variant chip
    (06.6.4.1-UI-SPEC.md §7.1). `shape` is a free-text filename suffix
    from `_ILLUSTRATION_TARGETS`, reached only through
    `illustrations.target_variants_by_airline()` — e.g. `"a350-1000"` —
    a DIFFERENT domain from `illustrations.SHAPE_SLUGS`' seven-member
    ICAO-type classification.

    TRAP: this function must never validate `shape` against
    `SHAPE_SLUGS` membership before deciding how (or whether) to render
    it — `"a350-1000"` is a real, live entry that such a check would
    silently drop, since it is not itself a `SHAPE_SLUGS` member (only
    its un-suffixed `"a350"` root is). The branch below is derived from
    the shape string's own form, never from that tuple.

    An alphanumeric type code upper-cases verbatim (`"a320"` ->
    `"A320"`, `"atr72"` -> `"ATR72"`, `"a330"` -> `"A330"`, `"b737"` ->
    `"B737"`, `"a350-1000"` -> `"A350-1000"`). A word-form manufacturer
    shape title-cases instead (`"embraer"` -> `"Embraer"`), splitting a
    trailing digit-led model number into its own word
    (`"beechcraft1900d"` -> `"Beechcraft 1900D"`).
    """
    if not isinstance(shape, str) or not shape:
        return ""
    if _TYPE_CODE_RE.match(shape):
        return shape.upper()
    word_match = _WORD_MODEL_RE.match(shape)
    if word_match:
        word, model = word_match.groups()
        return "%s %s" % (word.title(), model.upper())
    return shape.title()


def _airline_card_html(index, airline_name, shapes):
    """One `.airline-card` (06.6.4.1-UI-SPEC.md §7.1): an image pointing
    at the session-gated `/illustration/{key}.png` route, the airline's
    name, and one chip per fleet-type variant — the chips container is
    omitted entirely (not rendered empty) when `shapes` is empty. Every
    interpolated value — the key inside the URL, the name, each chip
    label, and the alt text — goes through `escape_html()` exactly once,
    at the point of interpolation (T-06.6.4.1-05). Returns the empty
    string (skips the card, never crashes) for an airline whose
    normalised key comes back falsy, mirroring
    `illustrations.target_filenames()`'s own documented skip discipline.

    `index` becomes the card's `data-filter-group` value (D-16/D-20):
    this page renders one representation per airline (no mobile-card
    pairing like History), but `companion/static/list-filter.js` counts
    distinct groups rather than raw elements, so every filterable card
    still needs its own group. `data-filter-text` carries the lower-cased
    airline name, escaped before interpolation into the attribute — the
    same discipline the old registry rows applied to their prefix value.
    """
    key = illustrations.normalise_airline_key(airline_name)
    if not key:
        return ""
    image_html = (
        '<img class="airline-card__image" src="%s%s.png" '
        'loading="lazy" decoding="async" alt="%s">'
    ) % (
        ILLUSTRATION_ROUTE_PREFIX, escape_html(key),
        escape_html(CARD_IMAGE_ALT_TEMPLATE % airline_name),
    )
    chips_html = ""
    if shapes:
        chips = "".join(
            '<span class="airline-card__chip">%s</span>' % escape_html(variant_chip_label(shape))
            for shape in shapes
        )
        chips_html = '<div class="airline-card__chips">%s</div>' % chips
    filter_text = escape_html(
        airline_name.lower() if isinstance(airline_name, str) else str(airline_name).lower())
    return (
        '<div class="airline-card" data-filter-text="%s" data-filter-group="%d">'
        "%s"
        '<p class="airline-card__name">%s</p>'
        "%s"
        "</div>"
    ) % (filter_text, index, image_html, escape_html(airline_name), chips_html)


def _gallery_grid_html(pairs):
    """Wrap one `_airline_card_html()` card per `(airline_name, shapes)`
    pair in the `.illustration-grid` container (06.6.4.1-UI-SPEC.md
    §7.1, companion/static/style.css from plan 01). Skips (renders
    nothing for) any pair whose card comes back empty.
    """
    cards = "".join(
        _airline_card_html(index, airline_name, shapes)
        for index, (airline_name, shapes) in enumerate(pairs))
    return '<div class="illustration-grid">%s</div>' % cards


# D-16 (06.6.4.1-UI-SPEC.md §7.2): the gallery's filter-bar copy, driven
# client-side by companion/static/list-filter.js's shared
# [data-filter-input]/[data-filter-count]/[data-filter-clear]/
# [data-filter-empty] attribute contract — the same script History's own
# _filter_bar_html() already consumes, no script change needed here.
# Unlike the retired diagnostics page, this gallery carries no read-only
# constraint, so the Clear control below is a real <button>, matching
# History's variant rather than the old Airlines page's anchor-link one.
_FILTER_INPUT_ID = "airlines-gallery-filter-input"
_FILTER_LABEL_TEXT = "Filter by airline name"
_FILTER_EMPTY_HEADING = "No matching airlines"
_FILTER_EMPTY_BODY_TEMPLATE = (
    "Try a different search, or Clear filter to see all %d airlines.")


def _filter_bar_html(total):
    """D-16's filter bar over the gallery — History's `<button
    type="button" data-filter-clear>Clear</button>` variant
    (06.6.4.1-UI-SPEC.md §7.2), not the old read-only Airlines page's
    `<a href="#...">` variant: that anchor existed only because the old
    diagnostics page was forbidden any button element (D-16, retired),
    and this gallery carries no such constraint. Entirely inert without
    JS — `companion/static/list-filter.js`'s own early-return guard
    means the full unfiltered card grid underneath stays completely
    usable if the script never loads.
    """
    count_text = "%d of %d shown" % (total, total)
    empty_body = _FILTER_EMPTY_BODY_TEMPLATE % total
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        '<input type="search" id="%s" data-filter-input>'
        "</div>"
        '<span class="filter-bar__count" data-filter-count>%s</span>'
        '<button type="button" data-filter-clear>Clear</button>'
        "</div>"
        '<div class="empty-state" data-filter-empty hidden>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (
        _FILTER_INPUT_ID, escape_html(_FILTER_LABEL_TEXT),
        layout.icon_html("icon-search"),
        _FILTER_INPUT_ID,
        escape_html(count_text),
        escape_html(_FILTER_EMPTY_HEADING),
        escape_html(empty_body),
    )


def render(ctx):
    """The Airlines gallery (D-13 through D-17): the page header, the
    D-16 filter bar, then one card per airline in
    `illustrations.target_variants_by_airline()` order. `ctx` is accepted
    for call-site parity with every other page module's `render(ctx)`
    signature but is otherwise unused — this page reads one static
    in-memory list, no database and no poll state.

    The filter bar renders only when there is at least one card — this
    codebase's consistent "no chrome with no data" rule — though with a
    static curated list that branch is unreachable today; it stays a
    genuine guard, not a claim that the list can ever be empty.
    """
    pairs = illustrations.target_variants_by_airline()
    filter_html = _filter_bar_html(len(pairs)) if pairs else ""
    return (
        layout.page_header("Airlines", purpose=GALLERY_PURPOSE_TEXT)
        + filter_html
        + _gallery_grid_html(pairs)
    )
