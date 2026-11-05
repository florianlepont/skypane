"""The Airline collection (`/airlines`): a read-only, quiet page of the
airlines this frame has spotted, the same for every role.

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
from companion import ui_modal
import companion.layout as layout
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

PAGE_TITLE = i18n.msg("nav.airline_collection", "Airline collection")

PROGRESS_TEXT = i18n.msg("airlines.collection_progress", "%d of %d airlines spotted")
STATUS_TEXT = i18n.msg("airlines.collection_status", "%d airlines spotted")
GOAL_TEXT = i18n.msg("airlines.collection_next_goal", "%d more for the %d badge")
GOAL_FIRST_TEXT = i18n.msg(
    "airlines.collection_next_goal_first", "Spot one airline to earn the First sighting badge")
GOAL_COMPLETE_TEXT = i18n.msg(
    "airlines.collection_complete", "You have spotted every airline on the list.")
GOAL_ALL_BADGES_TEXT = i18n.msg(
    "airlines.collection_all_badges", "You have earned every badge.")
BADGES_LABEL = i18n.msg("airlines.collection_badges", "Collection badges")
BADGE_FIRST = i18n.msg("airlines.collection_badge_first", "First sighting")
BADGE_COUNT = i18n.msg("airlines.collection_badge_count", "%d airlines")
BADGE_EARNED = i18n.msg("airlines.collection_badge_earned", "Earned")
BADGE_LOCKED = i18n.msg("airlines.collection_badge_locked", "Locked: spot %d airlines")
BADGE_LOCKED_FIRST = i18n.msg("airlines.collection_badge_locked_first", "Locked: spot an airline")

SHOW_LEGEND = i18n.msg("airlines.collection_show", "Show")
SHOW_ALL = i18n.msg("airlines.collection_show_all", "All")
SHOW_SPOTTED = i18n.msg("airlines.collection_show_spotted", "Spotted")
SHOW_UNSEEN = i18n.msg("airlines.collection_show_unseen", "Not yet seen")
SORT_LABEL = i18n.msg("airlines.collection_sort_by", "Sort by")
SORT_MOST = i18n.msg("airlines.collection_sort_most", "Most seen")
SORT_LATEST = i18n.msg("airlines.collection_sort_latest", "Latest")
SORT_AZ = i18n.msg("airlines.collection_sort_az", "A to Z")
FILTER_LABEL = i18n.msg("airlines.collection_filter_label", "Filter airlines")
APPLY_TEXT = i18n.msg("airlines.collection_apply", "Apply")
COUNT_TEXT = i18n.msg("airlines.collection_count", "Airlines: %d")
COUNT_TEMPLATE = i18n.msg("airlines.collection_count_template", "Airlines: #")

SEEN_MANY = i18n.msg("airlines.collection_seen_many", "Seen %d times")
SEEN_ONCE = i18n.msg("airlines.collection_seen_once", "Seen once")
NOT_SEEN = i18n.msg("airlines.collection_not_seen", "Not seen yet")
NEW_PILL = i18n.msg("airlines.collection_new", "New")
RARITY_LABELS = {
    collection.RARITY_REGULAR: i18n.msg("airlines.collection_rarity_regular", "Regular"),
    collection.RARITY_OCCASIONAL: i18n.msg("airlines.collection_rarity_occasional", "Occasional"),
    collection.RARITY_RARE: i18n.msg("airlines.collection_rarity_rare", "Rare"),
}
RARITY_DOTS = {
    collection.RARITY_REGULAR: 3, collection.RARITY_OCCASIONAL: 2, collection.RARITY_RARE: 1}
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
RARITY_SENTENCE = i18n.msg(
    "airlines.collection_rarity_sentence",
    "Rarity depends on how often your frame has seen an airline.")

FACT_TIMES = i18n.msg("airlines.collection_fact_times", "Times seen")
FACT_FIRST = i18n.msg("airlines.collection_fact_first", "First seen")
FACT_LAST = i18n.msg("airlines.collection_fact_last", "Last seen")
FACT_TYPES = i18n.msg("airlines.collection_fact_types", "Aircraft types seen")
FACT_RARITY = i18n.msg("airlines.collection_fact_rarity", "Rarity")
FACT_CALLSIGNS = i18n.msg("airlines.collection_fact_callsigns", "Recent callsigns")
CLOSE_TEXT = i18n.msg("airlines.close", "Close")

EMPTY_HEADING = i18n.msg(
    "airlines.collection_empty_heading", "Your collection starts with the first plane")
EMPTY_BODY = i18n.msg(
    "airlines.collection_empty_body", "Airlines show up here as your frame sees them.")
NO_MATCH_HEADING = i18n.msg("airlines.no_matching_airlines", "No matching airlines")
NO_MATCH_BODY = i18n.msg(
    "airlines.collection_no_match_body", "Try another filter or a shorter name.")

SHOW_VALUES = (
    ("all", SHOW_ALL), ("spotted", SHOW_SPOTTED), ("unseen", SHOW_UNSEEN))
SORT_VALUES = (("most", SORT_MOST), ("latest", SORT_LATEST), ("az", SORT_AZ))
DEFAULT_SHOW = "all"
DEFAULT_SORT = "most"
QUERY_MAX_CHARS = 60
SHOW_PARAM = "show"
SORT_PARAM = "sort"
TEXT_PARAM = "q"

DIALOG_PREFIX = "dlg-airline-"
GRID_ID = "collection-grid"
_HISTORY_ERRORS = (sqlite3.Error, OSError)


class View:
    """The validated query: unknown values fall back to the defaults and
    the text is length-capped (it is only ever escaped, never trusted)."""

    def __init__(self, show, sort, text):
        self.show, self.sort, self.text = show, sort, text


def parse_view(query_string):
    params = parse_qs(query_string or "", keep_blank_values=True)

    def first(name):
        values = params.get(name) or [""]
        return values[0]

    show = first(SHOW_PARAM)
    sort = first(SORT_PARAM)
    return View(
        show if show in dict(SHOW_VALUES) else DEFAULT_SHOW,
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
        entry for entry in entries
        if (view.show == "all" or (view.show == "spotted") == entry.seen)
        and view.text.lower() in entry.name.lower()]
    if view.sort == "latest":
        return sorted(shown, key=lambda e: e.last_ts, reverse=True)
    if view.sort == "az":
        return sorted(shown, key=lambda e: e.name.casefold())
    return sorted(shown, key=lambda e: -e.times_seen)


def _picture_html(entry, state_dir):
    """The airline picture, or the dashed placeholder when it has none."""
    if illustrations.resolved_illustration_path(entry.picture_key, state_dir) is None:
        return '<span class="airline-card__placeholder collection-card__blank" aria-hidden="true"></span>'
    src = device_scope.scoped("%s%s.png" % (
        airlines_page.ILLUSTRATION_ROUTE_PREFIX, escape_html(entry.picture_key)))
    buster = airlines_page._illustration_cache_buster(entry.picture_key, state_dir)
    return (
        '<img class="collection-card__image" src="%s%s" width="%d" height="%d" '
        'loading="lazy" decoding="async" alt="%s">'
    ) % (src, buster, ILLUSTRATION_TARGET_WIDTH, ILLUSTRATION_TARGET_HEIGHT,
         escape_html(entry.name))


def _rarity_pill_html(rarity):
    dots = '<i class="rarity-dot"></i>' * RARITY_DOTS[rarity]
    return (
        '<span class="rarity-pill rarity-pill--%s"><span class="rarity-dots" aria-hidden="true">%s</span>'
        '<span>%s</span></span>') % (rarity, dots, escape_html(i18n.t(RARITY_LABELS[rarity])))


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


def _card_html(entry, state_dir):
    classes = "collection-card" + (
        " collection-card--" + entry.rarity if entry.seen else " collection-card--unseen")
    if entry.seen:
        pills = _rarity_pill_html(entry.rarity)
        if entry.is_new:
            pills += '<span class="rarity-pill rarity-pill--new">%s</span>' % (
                escape_html(i18n.t(NEW_PILL)))
        line = _seen_text(entry.times_seen)
        pills_html = '<span class="collection-card__pills">%s</span>' % pills
    else:
        line = i18n.t(NOT_SEEN)
        pills_html = ""
    link = ui_modal.trigger_html(
        DIALOG_PREFIX + entry.slug,
        '<span class="collection-card__art">%s</span>'
        '<span class="collection-card__name">%s</span>'
        '<span class="collection-card__seen text-label">%s</span>%s' % (
            _picture_html(entry, state_dir), escape_html(entry.name),
            escape_html(line), pills_html),
        extra_class=classes)
    return '<li class="collection-item" data-filter-text="%s">%s</li>' % (
        escape_html(entry.name.lower()), link)


def _date_text(day):
    if day is None:
        return ""
    return "%d %s %d" % (day.day, layout.month_abbr(day.month), day.year)


def _fact_html(label, value_html, wide=False):
    return '<div%s><dt>%s</dt><dd>%s</dd></div>' % (
        ' class="collection-facts__wide"' if wide else "",
        escape_html(i18n.t(label)), value_html)


def _types_html(entry):
    """Each aircraft type, tagged with its rarity in words when it is not a
    regular sight."""
    chips = []
    for code, rarity in entry.type_rarities:
        label = escape_html(panel_render._TYPE_DISPLAY_LABELS.get(code, code))
        tag = ""
        if rarity in (collection.RARITY_RARE, collection.RARITY_OCCASIONAL):
            tag = ' <span class="type-chip__tag">%s</span>' % escape_html(i18n.t(RARITY_LABELS[rarity]))
        chips.append('<span class="type-chip type-chip--%s">%s%s</span>' % (rarity, label, tag))
    return '<span class="type-chips">%s</span>' % "".join(chips)


def _facts_html(entry, now):
    callsigns = " ".join(
        '<span class="mono">%s</span>' % escape_html(c) for c in entry.callsigns)
    rows = [
        _fact_html(FACT_TIMES, escape_html(str(entry.times_seen))),
        _fact_html(FACT_RARITY, _rarity_pill_html(entry.rarity)),
        _fact_html(FACT_FIRST, escape_html(_date_text(entry.first_day))),
        _fact_html(FACT_LAST, "%s (%s)" % (
            escape_html(_date_text(entry.last_day)),
            layout.relative_time_html(entry.last_ts, now))),
    ]
    if entry.types:
        rows.append(_fact_html(FACT_TYPES, _types_html(entry), wide=True))
    if callsigns:
        rows.append(_fact_html(FACT_CALLSIGNS, callsigns, wide=True))
    return '<dl class="collection-facts">%s</dl>' % "".join(rows)


def _sheet_html(entry, state_dir, now):
    if entry.seen:
        body = _facts_html(entry, now) + '<p class="text-label collection-sheet__note">%s</p>' % (
            escape_html(i18n.t(RARITY_SENTENCE)))
    else:
        body = '<p class="text-body">%s</p>' % escape_html(i18n.t(NOT_SEEN))
    sections = '<div class="collection-sheet__art">%s</div>%s' % (
        _picture_html(entry, state_dir), body)
    return ui_modal.sections_dialog_html(
        DIALOG_PREFIX + entry.slug, entry.name, "", sections,
        i18n.t(CLOSE_TEXT), "#" + GRID_ID, extra_class="collection-sheet")


def _goal_text(summary, all_curated_seen):
    if all_curated_seen:
        return i18n.t(GOAL_COMPLETE_TEXT)
    if summary.next_goal is None:
        return i18n.t(GOAL_ALL_BADGES_TEXT)
    if summary.next_goal == 1:
        return i18n.t(GOAL_FIRST_TEXT)
    return i18n.t(GOAL_TEXT) % (summary.next_goal - summary.spotted, summary.next_goal)


def _status_text(summary, all_curated_seen):
    """The one progress line: the spotted count, then the next goal."""
    return "%s \u00b7 %s" % (
        i18n.t(STATUS_TEXT) % summary.spotted, _goal_text(summary, all_curated_seen))


def _badge_html(threshold, earned):
    """A small round icon: a filled check once earned, an outlined star
    while locked. The words (and the tooltip) carry the state and the goal."""
    label = i18n.t(BADGE_FIRST) if threshold == 1 else i18n.t(BADGE_COUNT) % threshold
    if earned:
        words = "%s: %s" % (i18n.t(BADGE_EARNED), label)
    else:
        words = (i18n.t(BADGE_LOCKED_FIRST) if threshold == 1
                 else i18n.t(BADGE_LOCKED) % threshold)
    icon = layout.icon_html("icon-check" if earned else "icon-star", 16)
    return (
        '<li class="collection-badge collection-badge--%s" title="%s">%s'
        '<span class="visually-hidden">%s</span></li>'
    ) % ("earned" if earned else "locked", escape_html(words), icon, escape_html(words))


def _status_html(summary, all_curated_seen):
    """The header's right-hand part: a thin progress bar with one short
    line under it, and the badge icons."""
    headline = i18n.t(PROGRESS_TEXT) % (summary.spotted, summary.total)
    badges = "".join(
        _badge_html(n, n in summary.earned) for n in collection.BADGE_THRESHOLDS)
    return (
        '<div class="collection-head__status"><div class="collection-progress">'
        '<progress class="collection-progress__bar" value="%d" max="%d" aria-label="%s">%s</progress>'
        '<p class="text-label collection-progress__headline">%s</p></div>'
        '<ul class="collection-badges" aria-label="%s">%s</ul></div>'
    ) % (min(summary.spotted, summary.total), max(summary.total, 1),
         escape_html(headline), escape_html(headline),
         escape_html(_status_text(summary, all_curated_seen)),
         escape_html(i18n.t(BADGES_LABEL)), badges)


def _chips_html(view, entries):
    seen = sum(1 for entry in entries if entry.seen)
    counts = {"all": len(entries), "spotted": seen, "unseen": len(entries) - seen}
    chips = []
    for value, label in SHOW_VALUES:
        chips.append(
            '<label class="filter-chip"><input type="radio" class="visually-hidden" '
            'name="%s" value="%s"%s data-autosubmit><span class="filter-chip__box">'
            '<span class="filter-chip__count">%d</span>'
            '<span class="filter-chip__text">%s</span></span></label>' % (
                SHOW_PARAM, value, " checked" if value == view.show else "",
                counts[value], escape_html(i18n.t(label))))
    return '<fieldset class="filter-bar__chips"><legend class="visually-hidden">%s</legend>%s</fieldset>' % (
        escape_html(i18n.t(SHOW_LEGEND)), "".join(chips))


def _sort_html(view):
    options = "".join(
        '<option value="%s"%s>%s</option>' % (
            value, " selected" if value == view.sort else "", escape_html(i18n.t(label)))
        for value, label in SORT_VALUES)
    return (
        '<label class="collection-sort"><span class="collection-sort__label">%s</span>'
        '<select name="%s" data-autosubmit>%s</select></label>'
    ) % (escape_html(i18n.t(SORT_LABEL)), SORT_PARAM, options)


def _search_html(view):
    label = escape_html(i18n.t(FILTER_LABEL))
    return (
        '<div class="filter-bar__search"><label class="visually-hidden" for="collection-filter">%s</label>'
        '%s<input type="search" id="collection-filter" name="%s" value="%s" maxlength="%d" '
        'placeholder="%s" autocomplete="off" spellcheck="false" data-filter-input></div>'
    ) % (label, layout.icon_html("icon-search", 20), TEXT_PARAM, escape_html(view.text),
         QUERY_MAX_CHARS, label)


def _count_html(shown):
    """The live count, read out by screen readers only: the segmented
    filter already shows the visible numbers."""
    return (
        '<p class="visually-hidden" role="status" data-filter-count '
        'data-filter-count-template="%s">%s</p>'
    ) % (escape_html(i18n.t(COUNT_TEMPLATE)), escape_html(i18n.t(COUNT_TEXT) % shown))


def _legend_menu_html():
    """The rarity legend behind a small info button (a native <details>
    that the shared menu script closes on Escape or an outside tap)."""
    label = escape_html(i18n.t(LEGEND_LABEL))
    return (
        '<details class="row-menu collection-legend"><summary class="row-menu__toggle" '
        'aria-label="%s" title="%s">%s</summary>'
        '<div class="row-menu__panel collection-legend__panel">%s</div></details>'
    ) % (label, label, layout.icon_html("icon-info", 20), _legend_html())


def _controls_html(view, entries, shown):
    """One bar: the filter field, the show segments, the sort and the
    legend button. With a script the sort and the segments submit on
    change; without one the Apply button stays visible."""
    return (
        '<form class="filter-bar collection-controls" method="get" action="%s">'
        '%s%s%s%s%s'
        '<button type="submit" class="collection-controls__apply">%s</button></form>'
    ) % (escape_html(device_scope.scoped(layout.AIRLINES_ROUTE)),
         _search_html(view), _chips_html(view, entries), _sort_html(view),
         _legend_menu_html(), _count_html(shown), escape_html(i18n.t(APPLY_TEXT)))


def _entries_for(ctx, now):
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
    curated = [entry for entry in entries if entry.curated]
    all_seen = bool(curated) and all(entry.seen for entry in curated)
    shown = _apply_view(entries, view)
    parts = [layout.page_header(
        i18n.t(PAGE_TITLE), None, action_html=_status_html(summary, all_seen))]
    if summary.spotted == 0:
        parts.append(layout.empty_state(
            i18n.t(EMPTY_HEADING), i18n.t(EMPTY_BODY), compact=True))
    parts.append(_controls_html(view, entries, len(shown)))
    if shown:
        parts.append('<ul class="collection-grid" id="%s">%s</ul>' % (GRID_ID, "".join(
            _card_html(entry, ctx.state_dir) for entry in shown)))
        parts.extend(_sheet_html(entry, ctx.state_dir, now) for entry in shown)
    else:
        parts.append(layout.empty_state(i18n.t(NO_MATCH_HEADING), i18n.t(NO_MATCH_BODY)))
    return "".join(parts)
