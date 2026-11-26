"""The Airline collection (`/airlines`): a read-only, quiet page of the
airlines the frame the page is opened on has spotted, the same for every
role: only airlines that frame saw are listed. Frame access is decided by the
route (a user reaches their own and co-managed frames only), so counts, dates,
types, names and pictures of an airline only another frame saw never reach it.
The fleet-wide list is the administrator's editor.

Counts, rarity, dates, types and callsigns come from the frame's own
`runway_events` and the curated airline list through
`companion.airline_collection`; nothing is stored and nothing on the page
edits an airline (the editing page is `/airlines/manage`, administrator
only). Stored text (airline names, callsigns, aircraft types) reaches the
markup only through `escape_html`; dialog ids are slugs derived from the
normalised airline key.
"""
import sqlite3
from urllib.parse import parse_qs, urlencode

from companion import access
from companion import airline_collection as collection
from companion import device_scope
from companion import i18n
from companion import illustration_normalize
from companion import ui_components, ui_filter
from companion import ui_modal
import companion.layout as layout
from companion import prefs
from companion.illustration_normalize import (
    ILLUSTRATION_TARGET_HEIGHT,
    ILLUSTRATION_TARGET_WIDTH,
)
from companion.layout import escape_html
import companion.page_context as page_context
from companion.pages import airlines_page
from server import history_db
from server.plane import illustrations
from server.plane import render as panel_render

PAGE_TITLE = i18n.msg("nav.airline_collection", "Airlines")

GOAL_TEXT = i18n.msg("airlines.collection_next_goal", "%d more for the %d badge")
GOAL_FIRST_TEXT = i18n.msg(
    "airlines.collection_next_goal_first", "Spot one airline to earn the First sighting badge")
GOAL_ALL_BADGES_TEXT = i18n.msg(
    "airlines.collection_all_badges", "You have earned every badge.")
BADGES_LABEL = i18n.msg("airlines.collection_badges", "Collection badges")
BADGE_FIRST = i18n.msg("airlines.collection_badge_first", "First sighting")
BADGE_COUNT = i18n.msg("airlines.collection_badge_count", "%d airlines")
BADGE_EARNED = i18n.msg("airlines.collection_badge_earned", "Earned")
BADGE_LOCKED = i18n.msg("airlines.collection_badge_locked", "Locked: spot %d airlines")
BADGE_LOCKED_FIRST = i18n.msg("airlines.collection_badge_locked_first", "Locked: spot an airline")

SORT_LABEL = i18n.msg("airlines.collection_sort_by", "Sort by")
SORT_MOST = i18n.msg("airlines.collection_sort_most", "Most seen")
SORT_RAREST = i18n.msg("airlines.collection_sort_rarest", "Rarest")
SORT_LATEST = i18n.msg("airlines.collection_sort_latest", "Latest")
SORT_AZ = i18n.msg("airlines.collection_sort_az", "A to Z")
FILTER_LABEL = i18n.msg("airlines.collection_filter_label", "Filter airlines")
# The field's placeholder is shorter than its label so it never clips on a phone.
FILTER_PLACEHOLDER = i18n.msg("airlines.collection_filter_placeholder", "Filter")
APPLY_TEXT = i18n.msg("airlines.collection_apply", "Apply")
COUNT_TEXT = i18n.msg("airlines.collection_count_of_total", "%d of %d airlines")
COUNT_TEMPLATE = i18n.msg("airlines.collection_count_of_total_template", "# of # airlines")
CHIPS_LEGEND = i18n.msg("airlines.chips_legend", "Filter the airlines")
CHIP_ALL = i18n.msg("airlines.chip_all", "All")
CHIP_ART = i18n.msg("airlines.collection_chip_artwork", "With artwork")
CHIP_NO_ART = i18n.msg("airlines.collection_chip_no_artwork", "No artwork")
CHIP_MONTH = i18n.msg("airlines.collection_chip_month", "Seen this month")
KIND_ART, KIND_NO_ART, KIND_MONTH = "art", "noart", "month"

SEEN_MANY = i18n.msg("airlines.collection_seen_many", "Seen %d times")
SEEN_ONCE = i18n.msg("airlines.collection_seen_once", "Seen once")
NEW_PILL = i18n.msg("airlines.collection_new", "New")
RARITY_LABELS = {
    collection.RARITY_REGULAR: i18n.msg("airlines.collection_rarity_regular", "Regular"),
    collection.RARITY_OCCASIONAL: i18n.msg("airlines.collection_rarity_occasional", "Occasional"),
    collection.RARITY_RARE: i18n.msg("airlines.collection_rarity_rare", "Rare"),
}
# The legend's range text per tier, built from the one threshold table.
RARITY_RANGES = (
    (collection.RARITY_RARE, i18n.msg(
        "airlines.collection_range_rare", "Fewer than %d sightings")),
    (collection.RARITY_OCCASIONAL, i18n.msg(
        "airlines.collection_range_occasional", "%d to %d sightings")),
    (collection.RARITY_REGULAR, i18n.msg(
        "airlines.collection_range_regular", "%d or more sightings")),
)
LEGEND_LABEL = i18n.msg("airlines.collection_legend", "Rarity of airlines and aircraft")

FACT_TIMES = i18n.msg("airlines.collection_fact_times", "Seen")
FACT_LAST = i18n.msg("airlines.collection_fact_last", "Last seen")
FACT_TYPES = i18n.msg("airlines.collection_fact_types", "Aircraft")
CLOSE_TEXT = i18n.msg("airlines.close", "Close")

PURPOSE_TEXT = i18n.msg("airlines.collection_purpose", "Airlines your frame has seen")
EMPTY_HEADING = i18n.msg(
    "airlines.collection_empty_heading", "Your collection starts with the first plane")
EMPTY_BODY = i18n.msg(
    "airlines.collection_empty_body", "Airlines show up here as your frame sees them.")
NO_MATCH_HEADING = i18n.msg("airlines.no_matching_airlines", "No matching airlines")
NO_MATCH_BODY = i18n.msg(
    "airlines.collection_no_match_body", "Try another filter or a shorter name.")

SORT_VALUES = (
    ("most", SORT_MOST), ("rarest", SORT_RAREST), ("latest", SORT_LATEST), ("az", SORT_AZ))
DEFAULT_SORT = "rarest"
QUERY_MAX_CHARS = 60
SORT_PARAM = "sort"
TEXT_PARAM = "q"

DIALOG_PREFIX = "dlg-airline-"
GRID_ID = "collection-grid"
_HISTORY_ERRORS = (sqlite3.Error, OSError)


class View:
    """The validated query: unknown values fall back to the defaults and
    the text is length-capped (it is only ever escaped, never trusted)."""

    def __init__(self, sort, text):
        self.sort, self.text = sort, text


def parse_view(query_string):
    params = parse_qs(query_string or "", keep_blank_values=True)

    def first(name):
        values = params.get(name) or [""]
        return values[0]

    sort = first(SORT_PARAM)
    return View(
        sort if sort in dict(SORT_VALUES) else DEFAULT_SORT,
        first(TEXT_PARAM).strip()[:QUERY_MAX_CHARS])


def resolve_redirect(is_admin, query_string):
    """The editing page's address for an administrator asking to resolve a
    prefix, else None. The target is the fixed manage path plus the
    re-encoded prefix, never the raw query."""
    if not is_admin:
        return None
    prefix = parse_qs(query_string or "").get(airlines_page.RESOLVE_QUERY_PARAM, [None])[0]
    if not prefix:
        return None
    return "%s?%s" % (
        device_scope.scoped(airlines_page.MANAGE_ROUTE),
        urlencode({airlines_page.RESOLVE_QUERY_PARAM: prefix}))


def get(handler, device):
    """GET /airlines: the editing-page redirect for an administrator who
    followed a resolve link, else the collection for every role."""
    principal = handler._safe_principal()
    query = handler.path.partition("?")[2]
    target = resolve_redirect(
        principal is not None and principal.role == access.ADMIN, query)
    if target:
        return handler.redirect(target)
    return handler._render_tab(
        layout.AIRLINES_ROUTE, lambda ctx: render(ctx, query), device)


def _apply_view(entries, view):
    shown = [
        entry for entry in entries if view.text.lower() in entry.name.lower()]
    return _sorted(shown, view.sort)


def _sorted(entries, sort):
    """`entries` in the order `sort` names; entries that compare equal keep
    the order they came in."""
    if sort == "latest":
        return sorted(entries, key=lambda e: e.last_ts, reverse=True)
    if sort == "az":
        return sorted(entries, key=lambda e: e.name.casefold())
    if sort == "rarest":
        return sorted(entries, key=lambda e: (e.times_seen, e.name.casefold()))
    return sorted(entries, key=lambda e: -e.times_seen)


# The attribute a card carries its place in every order under, one number per
# entry of SORT_VALUES: list-filter.js reorders the cards by it, so a sort
# costs no request. Must equal RANK_ATTR in static/list-filter.js.
RANK_ATTR = "data-sort-rank"


def _sort_ranks(entries):
    """`{slug: "<rank under each SORT_VALUES order>"}` over every entry, so
    the ranks of any subset give the order the server itself would show."""
    ranks = {entry.slug: [] for entry in entries}
    for value, _label in SORT_VALUES:
        for position, entry in enumerate(_sorted(entries, value)):
            ranks[entry.slug].append(str(position))
    return {slug: " ".join(places) for slug, places in ranks.items()}


def _picture_html(entry, state_dir):
    """The picture of the airline's default type, or the dashed placeholder
    when it has none."""
    picture_key = illustrations.display_key(entry.picture_key, state_dir)
    if picture_key is None:
        return (
            '<span class="airline-card__placeholder collection-card__blank" aria-hidden="true">'
            "%s</span>" % layout.icon_html("icon-plane", size=24))
    src = device_scope.scoped("%s%s.png" % (
        airlines_page.ILLUSTRATION_ROUTE_PREFIX, escape_html(picture_key)))
    buster = airlines_page._illustration_cache_buster(picture_key, state_dir)
    return (
        '<img class="collection-card__image" src="%s%s" width="%d" height="%d" '
        'loading="lazy" decoding="async" fetchpriority="low" alt="%s">'
    ) % (src, illustration_normalize.thumbnail_query(buster, ILLUSTRATION_TARGET_WIDTH),
         ILLUSTRATION_TARGET_WIDTH, ILLUSTRATION_TARGET_HEIGHT,
         escape_html(entry.name))


def _rarity_pill_html(rarity):
    """The rarity as a filled pill: a dot and the word, so colour is never the only signal."""
    return (
        '<span class="rarity-pill rarity-pill--%s"><i class="rarity-dot" aria-hidden="true"></i>'
        '<span>%s</span></span>') % (rarity, escape_html(i18n.t(RARITY_LABELS[rarity])))


def _range_text(rarity, template):
    if rarity == collection.RARITY_RARE:
        return i18n.t(template) % collection.OCCASIONAL_MIN
    if rarity == collection.RARITY_OCCASIONAL:
        return i18n.t(template) % (collection.OCCASIONAL_MIN, collection.REGULAR_MIN - 1)
    return i18n.t(template) % collection.REGULAR_MIN


def _legend_html():
    """Every tier with its dots, its name and its sighting range: the same
    words the cards carry, so colour is never the only signal."""
    tiers = "".join(
        '<li class="rarity-legend__tier">%s<span class="text-label">%s</span></li>' % (
            _rarity_pill_html(rarity), escape_html(_range_text(rarity, template)))
        for rarity, template in reversed(RARITY_RANGES))
    return '<ul class="rarity-legend" aria-label="%s">%s</ul>' % (
        escape_html(i18n.t(LEGEND_LABEL)), tiers)


def _seen_text(times):
    return i18n.t(SEEN_ONCE) if times == 1 else i18n.t(SEEN_MANY) % times


def _card_html(entry, state_dir, ranks="", kinds=""):
    """A calm card: the picture, the name, the sighting count and the rarity
    pill; the New pill sits in the card's corner, outside the picture, and
    only while it applies."""
    classes = "collection-card collection-card--" + entry.rarity
    new = ""
    if entry.is_new:
        new = '<span class="rarity-pill rarity-pill--new">%s</span>' % (
            escape_html(i18n.t(NEW_PILL)))
    line_html = (
        '<span class="collection-card__seen text-label">%s</span>'
        '<span class="collection-card__pill">%s</span>'
    ) % (escape_html(_seen_text(entry.times_seen)), _rarity_pill_html(entry.rarity))
    link = ui_modal.trigger_html(
        DIALOG_PREFIX + entry.slug,
        '<span class="collection-card__art">%s</span>%s'
        '<span class="collection-card__name">%s</span>%s' % (
            _picture_html(entry, state_dir), new, escape_html(entry.name), line_html),
        extra_class=classes)
    unlock = ' data-unlock="%s"' % escape_html(entry.slug) if entry.is_new else ""
    return '<li class="collection-item" data-filter-text="%s" data-filter-kind="%s" %s="%s"%s>%s</li>' % (
        escape_html(entry.name.lower()), kinds, RANK_ATTR, ranks, unlock, link)


def _date_text(day):
    if day is None:
        return ""
    return "%d %s %d" % (day.day, layout.month_abbr(day.month), day.year)


def _fact_html(label, value_html):
    return '<div><dt>%s</dt><dd>%s</dd></div>' % (escape_html(i18n.t(label)), value_html)


def _types_text(entry):
    """The aircraft types seen, as the names the frame shows, in plain words."""
    return ", ".join(
        panel_render._TYPE_DISPLAY_LABELS.get(code, code) for code, _rarity in entry.type_rarities)


def _facts_html(entry):
    rows = [
        _fact_html(FACT_TIMES, escape_html(_seen_text(entry.times_seen).lower())),
        _fact_html(FACT_LAST, escape_html(_date_text(entry.last_day))),
    ]
    if entry.types:
        rows.append(_fact_html(FACT_TYPES, escape_html(_types_text(entry))))
    return '<dl class="collection-facts">%s</dl>' % "".join(rows)


def _sheet_html(entry, state_dir):
    """The detail sheet: the picture, the name (the dialog's title) and the rarity pill
    on top, then the facts in one card. Nothing scrolls inside it."""
    body = '<div class="collection-sheet__rarity">%s</div>%s' % (
        _rarity_pill_html(entry.rarity), _facts_html(entry))
    has_picture = illustrations.display_key(entry.picture_key, state_dir) is not None
    art = '<div class="collection-sheet__art">%s</div>' % _picture_html(
        entry, state_dir) if has_picture else ""
    return ui_modal.sections_dialog_html(
        DIALOG_PREFIX + entry.slug, entry.name, "", art + body,
        i18n.t(CLOSE_TEXT), "#" + GRID_ID, extra_class="collection-sheet")


def _goal_text(summary):
    if summary.next_goal is None:
        return i18n.t(GOAL_ALL_BADGES_TEXT)
    if summary.next_goal == 1:
        return i18n.t(GOAL_FIRST_TEXT)
    return i18n.t(GOAL_TEXT) % (summary.next_goal - summary.spotted, summary.next_goal)


def _badge_words(threshold, earned):
    label = i18n.t(BADGE_FIRST) if threshold == 1 else i18n.t(BADGE_COUNT) % threshold
    if earned:
        return "%s: %s" % (i18n.t(BADGE_EARNED), label)
    return (i18n.t(BADGE_LOCKED_FIRST) if threshold == 1
            else i18n.t(BADGE_LOCKED) % threshold)


def _badges_html(summary):
    """One compact pill, a star and "earned/total". The tooltip and the
    visually hidden list spell out every badge in words."""
    words = [_badge_words(n, n in summary.earned) for n in collection.BADGE_THRESHOLDS]
    earned = sum(1 for n in collection.BADGE_THRESHOLDS if n in summary.earned)
    total = len(collection.BADGE_THRESHOLDS)
    return (
        '<p class="collection-badges" title="%s">%s<span aria-hidden="true">%d/%d</span>'
        '<span class="visually-hidden">%s: %d/%d. %s</span></p>'
    ) % (escape_html("; ".join(words)), layout.icon_html("icon-star", 16), earned, total,
         escape_html(i18n.t(BADGES_LABEL)), earned, total, escape_html(". ".join(words)))


def _status_html(summary):
    """The header's progress, under the title: the next badge goal and the
    compact badge pill."""
    return (
        '<div class="collection-head__status">'
        '<p class="collection-progress__goal">%s</p>%s</div>'
    ) % (escape_html(_goal_text(summary)), _badges_html(summary))


def _sort_html(view):
    return ui_filter.sort_menu_html(
        SORT_PARAM, SORT_VALUES, view.sort, SORT_LABEL, " data-autosubmit")


def _search_html(view):
    return ui_filter.named_search_html(
        "collection-filter", i18n.t(FILTER_LABEL), i18n.t(FILTER_PLACEHOLDER),
        TEXT_PARAM, view.text, QUERY_MAX_CHARS)


def _count_html(shown, total):
    """The live count under the controls ("N of M airlines"); the script
    rewrites it as the text and the chips narrow the list."""
    return ui_filter.count_line_html(i18n.t(COUNT_TEXT) % (shown, total), i18n.t(COUNT_TEMPLATE))


def _info_html():
    """The rarity legend behind the info button."""
    return ui_filter.info_menu_html(LEGEND_LABEL, _legend_html())


def _this_month(now):
    """`(year, month)` of the Paris date `now` falls on, or None."""
    parsed = layout.parse_iso(now)
    if parsed is None:
        return None
    local = parsed.astimezone(layout.LOCAL_TZ)
    return local.year, local.month


def _kinds(entry, state_dir, month):
    """The filter kinds of an airline's card: whether it has artwork, and
    whether it was last seen this month (several kinds are space separated)."""
    has_art = illustrations.display_key(entry.picture_key, state_dir) is not None
    kinds = [KIND_ART if has_art else KIND_NO_ART]
    if month is not None and entry.last_day is not None and (
            entry.last_day.year, entry.last_day.month) == month:
        kinds.append(KIND_MONTH)
    return " ".join(kinds)


def _chips_html(kinds):
    """The filter chips with how many airlines each holds; they filter the
    cards in the page, so a page without a script hides them."""
    counts = {}
    for entry_kinds in kinds:
        for kind in entry_kinds.split():
            counts[kind] = counts.get(kind, 0) + 1
    chips = [("", i18n.t(CHIP_ALL), len(kinds))] + [
        (kind, i18n.t(label), counts.get(kind, 0))
        for kind, label in ((KIND_ART, CHIP_ART), (KIND_NO_ART, CHIP_NO_ART),
                            (KIND_MONTH, CHIP_MONTH))]
    return ui_filter.chips_row_html(chips, i18n.t(CHIPS_LEGEND))


def _controls_html(view, shown, kinds):
    """The shared filter controls: the search, the sort and the rarity info on
    one row, the artwork and recency chips on the next. With a script the sort
    submits on change; without one the Apply button stays visible."""
    return ui_filter.controls_html(
        device_scope.scoped(layout.AIRLINES_ROUTE), _search_html(view), _sort_html(view),
        _info_html(), _chips_html(kinds), i18n.t(APPLY_TEXT), attrs=" data-collection-form",
        extra_html=ui_filter.list_offline_template_html()) + _count_html(shown, shown)


def _no_match_html(action_html, attrs):
    """The card for a search or a filter that matches no airline, with its
    Clear action."""
    return ui_filter.filter_empty_html(
        i18n.t(NO_MATCH_HEADING), i18n.t(NO_MATCH_BODY), action_html, attrs)


def _entries_for(ctx, now):
    """The collection over this frame's own sightings; an unreadable history
    gives an empty one."""
    overrides = ctx.name_overrides or {}
    try:
        with history_db.open_db(ctx.state_dir) as conn:
            return collection.airline_collection(conn, now, overrides)
    except _HISTORY_ERRORS:
        return collection.collection_from_events([], now, overrides)


def render(ctx, query_string=""):
    ctx = page_context.coerce(ctx)
    now = ctx.now or history_db.utc_now_iso()
    view = parse_view(query_string)
    entries, summary = _entries_for(ctx, now)
    # Only airlines this frame saw are listed.
    entries = [entry for entry in entries if entry.seen]
    shown = _apply_view(entries, view)
    parts = [layout.page_header(
        i18n.t(PAGE_TITLE), i18n.t(PURPOSE_TEXT), action_html=_status_html(summary))]
    if not entries:
        parts.append(layout.empty_state(
            i18n.t(EMPTY_HEADING), i18n.t(EMPTY_BODY), compact=True))
        return "".join(parts)
    month = _this_month(now)
    kinds = {entry.slug: _kinds(entry, ctx.state_dir, month) for entry in entries}
    parts.append(_controls_html(view, len(shown), list(kinds.values())))
    if shown:
        ranks = _sort_ranks(entries)
        # Revealed by list-filter.js when the typed text hides every card.
        parts.append(_no_match_html(
            ui_components.button_html(
                i18n.t(ui_filter.FILTER_CLEAR_TEXT), "secondary",
                attrs=" data-filter-clear data-filter-clear-all"),
            "data-filter-empty hidden"))
        parts.append('<ul class="collection-grid" id="%s" data-unlock-scope="%s">%s</ul>' % (
            GRID_ID, escape_html(prefs.current_principal_email() or "shared"),
            "".join(_card_html(entry, ctx.state_dir, ranks[entry.slug], kinds[entry.slug])
                    for entry in shown)))
        parts.extend(_sheet_html(entry, ctx.state_dir) for entry in shown)
    else:
        parts.append(_no_match_html(
            ui_components.button_html(
                i18n.t(ui_filter.FILTER_CLEAR_TEXT), "secondary",
                href=device_scope.scoped(layout.AIRLINES_ROUTE)),
            "data-collection-empty"))
    return "".join(parts)
