"""Health page markup builders for the registry ("Airlines we could not
name"), the resolution-statistics breakdown ("How well we name flights")
and the check-in regularity grid, extracted out of
companion/pages/health_page.py to keep that file under the companion
app's own file-size ceiling (companion/test_structure_guards.py).

This module lives outside companion/pages/ on purpose: a page module may
not import another page module (companion/pages/__init__.py's own
contract), so a markup helper shared by exactly one page still needs a
home next to companion/battery_chart.py and companion/health_signals.py
rather than beside history_page.py or airlines_page.py.

health_page.py imports this module and re-exports the names its own
render() and its remaining tile builders still call as bare names, and a
number of tests still read as `health_page.X` — this module is never the
one importing health_page.py back (that would be circular, since
health_page.py imports this module at load time).
"""

from datetime import date, datetime, time, timedelta, timezone

from companion.layout import escape_html
import companion.battery_chart as battery_chart
import companion.draw as draw
import companion.health_signals as health_signals_module
import companion.i18n as i18n
import companion.layout as layout
import companion.wake as wake
from server import device_config, history_db

# Re-read under their own bare names purely for this module's own
# internal use (never re-exported back to health_page.py under these
# names) — `_DB_UNAVAILABLE` is the sentinel health_signals.py's own
# functions return, and `_full_local_timestamp_text` is
# battery_chart.py's own full-timestamp formatter, already used
# elsewhere in this file's registry table.
_DB_UNAVAILABLE = health_signals_module._DB_UNAVAILABLE
_full_local_timestamp_text = battery_chart._full_local_timestamp_text


HEALTH_UNAVAILABLE_TEXT = i18n.msg(
    "health.health_history_is_temporarily_unavailable_check",
    "Health history is temporarily unavailable — check the companion "
    "service logs.")


# The check-in regularity grid reports what is observable — the
# regularity of the record of check-ins, not the interval the device was
# expected to keep (nowhere in history, and not even a constant, since
# wake.effective_wake_interval_s() switches by screen state and quiet
# hours) — and its caption says so. Every verdict comes from
# wake.classify_check_in_gap(), derived from the same
# wake.device_staleness_thresholds() the Frame tile consumes, so this
# grid and that tile can never disagree about "late".
CHECK_IN_SECTION_HEADING = i18n.msg("health.check_in_regularity", "Check-in regularity")

# One cell per Europe/Paris calendar day. Inside draw.regularity_grid()'s
# own bound (ten columns by six rows = 60 cells at the measured card
# width), so the window can never be what the drawing truncates.
CHECK_IN_WINDOW_DAYS = 30

CHECK_IN_GRID_CLASS = "check-in-grid"
CHECK_IN_SCALE_CLASS = "check-in-grid__scale"
CHECK_IN_KEY_CLASS = "check-in-key"
CHECK_IN_KEY_ITEM_CLASS = "check-in-key__item"
CHECK_IN_KEY_SWATCH_CLASS = "check-in-key__swatch"

# The four states' own words, keyed on the classifier's own vocabulary.
# Colour is not a reading: four squares in four colours need their four
# names in text beside them, which is what the key below the grid is.
CHECK_IN_STATE_TEXT = {
    wake.CHECK_IN_ON_CADENCE: i18n.msg("health.on_cadence", "On cadence"),
    wake.CHECK_IN_LATE: i18n.msg("health.late", "Late"),
    wake.CHECK_IN_MISSING: i18n.msg("health.missing", "Missing"),
    wake.CHECK_IN_UNKNOWN: i18n.msg("health.no_record", "No record"),
}

# The caption's clauses, one constant each: only CHECK_IN_CAPTION_OBSERVED
# renders in the card's always-visible caption; every other clause moves
# into a `<details class="readings-disclosure">` immediately after it
# (see `_check_in_regularity_section_html()`).
CHECK_IN_CAPTION_OBSERVED = i18n.msg(
    "health.each_cell_is_one_day_of_observed_check_in",
    "Each cell is one day of observed check-in regularity, oldest first.")
# The cadence actually in force on an earlier day is not recoverable
# (device_config.json is a current-state file), so naming it without
# this qualifier would be a claim about the past made from a present value.
CHECK_IN_CAPTION_CADENCE = i18n.msg(
    "health.judged_against_the_cadence_configured_now_a",
    "Judged against the cadence configured now — a check-in every %s — not "
    "necessarily the cadence in force on an earlier day.")
# When there is no cadence to name at all: device_staleness_thresholds()'
# bare floors apply, and the caption must say so rather than print an
# assumed default.
CHECK_IN_CAPTION_CADENCE_FALLBACK = i18n.msg(
    "health.this_frame_s_cadence_cannot_be_determined_so",
    "This frame's cadence cannot be determined, so the grid is judged against "
    "the fallback staleness floors rather than against a configured cadence.")
# What a gap is not: the record cannot tell a wake the frame missed from
# a log range this server lost, so a grid without this sentence would
# make a claim its own data cannot support.
CHECK_IN_CAPTION_NOT_PROOF = i18n.msg(
    "health.a_day_with_no_record_is_not_proof_the_frame_did",
    "A day with no record is not proof the frame did not wake: a log rotation "
    "this server missed leaves exactly the same gap.")
# The empty deployment: a real case, rendering an honest grid of
# no-observation cells rather than a missing section.
CHECK_IN_CAPTION_EMPTY = i18n.msg(
    "health.no_check_in_intervals_are_recorded_yet_so_every",
    "No check-in intervals are recorded yet, so every day below is a day the "
    "record says nothing about.")

# The per-cell tooltip and the grid's own accessible name. The gap is
# named as a DURATION in the app's own form (layout.duration_text()) and
# the day as a local date — every visible instant in this app is
# Europe/Paris and a raw ISO string survives only behind a copy control.
CHECK_IN_CELL_TITLE = i18n.msg(
    "health.longest_observed_gap", "%s — %s: longest observed gap %s")
# A bare "%s — %s" join carries no translatable words of its own — the
# id exists only so i18n.t() (Message-only) can still be called on it;
# its French BY_ID entry is the identical template, listed in
# test_i18n.py's _UNCHANGED_IN_FRENCH.
CHECK_IN_CELL_TITLE_NONE = i18n.msg("health.day_dash_verdict", "%s — %s")
CHECK_IN_GRID_LABEL = i18n.msg(
    "health.observed_check_in_regularity_one_cell_per_day",
    "Observed check-in regularity, one cell per day over the last %d days: "
    "%d on cadence, %d late, %d missing, %d with no record.")


UNRESOLVED_SECTION_HEADING = i18n.msg(
    "health.airlines_we_could_not_name", "Airlines we could not name")
STATS_SECTION_HEADING = i18n.msg(
    "health.how_well_we_name_flights", "Flight identification")


_NO_GAPS_HEADING = i18n.msg("health.no_coverage_gaps", "No coverage gaps.")
_NO_GAPS_BODY = i18n.msg(
    "health.every_airline_we_ve_seen_recently_has_been",
    "Every airline we've seen recently has been named — nothing left to look up.")

# The genuine reference material — where resolution happens and what it
# does — lives in _READ_ONLY_NOTE_DETAIL below, rendered in a `<details
# class="readings-disclosure">` immediately after this visible sentence.
_READ_ONLY_NOTE = i18n.msg("health.this_list_is_read_only_here", "This list is read-only here.")
_READ_ONLY_NOTE_DETAIL = i18n.msg(
    "health.each_row_s_resolve_link_opens_the_airlines_page",
    "Each row's Resolve link opens the Airlines page to name that airline "
    "(and add artwork, if it needs one).")

# The heading is a %-template interpolated with RESOLUTION_WINDOW_DAYS
# at the one call site, never a literal "30", so it cannot silently
# drift from the window constant.
_NO_STATS_HEADING = i18n.msg(
    "health.no_flights_in_the_last_days", "No flights in the last %d days")
_NO_STATS_BODY = i18n.msg(
    "health.the_frame_has_not_recorded_a_detection_in_this",
    "The frame has not recorded a detection in this window. It will "
    "appear here after the next wake.")

# Only the event count varies between these templates; the day count is
# always RESOLUTION_WINDOW_DAYS, so a "1 day" singular form would be
# dead copy. Singular chosen at the call site, never a runtime "add an
# s" rule, which French cannot express (it pluralises the noun and
# needs article agreement too).
_RESOLUTION_DETAIL_TEMPLATE = i18n.msg(
    "health.over_the_last_days_events", "over the last %d days, %d events")
_RESOLUTION_DETAIL_SINGULAR_TEMPLATE = i18n.msg(
    "health.over_the_last_days_event", "over the last %d days, %d event")

RESOLUTION_WINDOW_DAYS = 30  # A month smooths over a quiet week at this
# single-airport traffic volume, while still reading as "recent".

# The four categories server/plane/enrich.py's resolve_route() documents,
# plus a fifth ("manual", an operator answering by hand at runtime from
# this companion web interface), in a fixed display order with a
# plain-English gloss so the page is readable without the source. The
# live/cache/static-table distinction is kept deliberately: collapsing
# it would hide which mechanism actually resolved the route.
_SOURCE_ROWS = (
    ("fresh_hit", i18n.msg("health.fresh_lookup", "Fresh lookup"),
     i18n.msg(
         "health.a_live_lookup_in_the_route_database_resolved_a",
         "A live lookup in the route database resolved a full route this cycle.")),
    ("cache_hit", i18n.msg("health.cached_hit", "Cached hit"),
     i18n.msg(
         "health.a_previously_cached_route_was_reused_sparing_a",
         "A previously-cached route was reused, sparing a network request.")),
    ("airline_only", i18n.msg("health.airline_only", "Airline only"),
     i18n.msg(
         "health.the_route_database_had_no_route_but_the",
         "The route database had no route, but the callsign's ICAO prefix "
         "identified the airline from the static prefix table.")),
    ("miss", i18n.msg("health.miss", "Miss"),
     i18n.msg(
         "health.neither_the_route_database_nor_the_static",
         "Neither the route database nor the static prefix table resolved "
         "anything for this callsign, so it shows up in the %s list above."
         % UNRESOLVED_SECTION_HEADING)),
    ("manual", i18n.msg("health.manual", "Manual"),
     i18n.msg(
         "health.the_operator_resolved_this_callsign_s_prefix_by",
         "The operator resolved this callsign's prefix by hand, from the "
         "companion web interface.")),
)

# A sixth, catch-all row for any route_source value outside the five
# above; folded in rather than dropped from the total. Kept out of
# _SOURCE_ROWS itself: that tuple is the fixed, ordered enumeration of
# known mechanisms, and folding an "unknown" bucket into it would
# misrepresent it as a sixth understood mechanism.
_OTHER_SOURCE_LABEL = i18n.msg("health.other", "Other")
_OTHER_SOURCE_GLOSS = i18n.msg(
    "health.a_route_source_this_page_does_not_recognise_or",
    "A route source this page does not recognise, or none was recorded "
    "at all — still counted here so the total always matches every "
    "event in the window.")

# Single-sourced so the table and the mobile card list can never
# disagree on a header word. Index 2 ("Count") is read directly by the
# card builder; "Description" has no card-side equivalent, since the
# mobile card renders the full description as stacked prose.
_STATS_HEADERS = (
    i18n.msg("health.source", "Source"),
    i18n.msg("health.description", "Description"),
    i18n.msg("health.count", "Count"),
)

# Driven client-side by list-filter.js's data-filter-* attribute
# contract. No hyphen in this value: see history_page.py's own
# `_FILTER_INPUT_ID` comment for the WebKit/Safari contacts-autofill
# explanation.
_FILTER_INPUT_ID = "airlines_filter_input"
_FILTER_LABEL_TEXT = i18n.msg("health.filter_by_prefix", "Filter by prefix")
_FILTER_EMPTY_HEADING = i18n.msg("health.no_matching_prefixes", "No matching prefixes")
_FILTER_EMPTY_BODY_TEMPLATE = i18n.msg(
    "health.try_a_different_search_or_clear_filter_to_see",
    "Try a different search, or Clear filter to see all %d prefixes.")


_MORE_DETAILS_TEXT = i18n.msg("health.more_details", "More details")


_FILTER_COUNT_TEMPLATE = i18n.msg("health.of_shown", "%d of %d shown")
_CLEAR_TEXT = i18n.msg("health.clear", "Clear")
_RESOLVED_PCT_TEMPLATE = i18n.msg("health.1f_resolved", "%.1f%% resolved")


def _unavailable_block():
    return '<p class="text-body">%s</p>' % escape_html(i18n.t(HEALTH_UNAVAILABLE_TEXT))


_TILE_DETAIL_CLASS = "text-label widget-detail"


def resolution_stats(conn, window_days=RESOLUTION_WINDOW_DAYS, now=None):
    """Windowed resolution-rate breakdown, mapped onto `_SOURCE_ROWS`'s
    categories. Resolved percentage is the share that produced any
    usable route (everything except `"miss"`); real traffic measured
    around 52.6%, so that region is expected, not a defect. Returns
    `{"rows": [...], "total": N, "resolved_pct": float_or_None}`;
    `resolved_pct` is `None` when `total` is zero. `total` counts every
    row in the window, folding an unrecognised `route_source` into
    `_OTHER_SOURCE_LABEL` rather than dropping it.
    """
    now_dt = now or datetime.now(timezone.utc)
    since = (now_dt - timedelta(days=window_days)).isoformat(timespec="seconds")
    counts = history_db.route_source_counts(conn, since=since)

    total = sum(counts.values())
    if total == 0:
        return {"rows": [], "total": 0, "resolved_pct": None}

    resolved = total - counts.get("miss", 0)
    resolved_pct = round((resolved / total) * 100, 1)
    # label/gloss are translated here, the one place both
    # _stats_cards_html() and _stats_table_html() read them from.
    rows = [
        (i18n.t(label), i18n.t(gloss), counts.get(source, 0))
        for source, label, gloss in _SOURCE_ROWS
    ]
    known_sources = {source for source, _label, _gloss in _SOURCE_ROWS}
    other_count = sum(
        n for source, n in counts.items() if source not in known_sources)
    if other_count:
        rows.append((
            i18n.t(_OTHER_SOURCE_LABEL), i18n.t(_OTHER_SOURCE_GLOSS), other_count))
    return {"rows": rows, "total": total, "resolved_pct": resolved_pct}


def _registry_filter_bar_html(total):
    """Filter bar over the unresolved-prefix registry, only rendered when
    there is data to filter. The count and Clear control share one
    `.filter-bar__meta` flex item, since two `nowrap` siblings in a
    `flex-wrap: wrap` container can still break apart from each other.
    The clear control is a plain link (no `<button>` on this page)
    pointing at the filter input's id, which both scrolls to and focuses
    it via fragment navigation.
    """
    count_text = i18n.t(_FILTER_COUNT_TEMPLATE) % (total, total)
    empty_body = i18n.t(_FILTER_EMPTY_BODY_TEMPLATE) % total
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        # autocomplete/spellcheck/autocapitalize: same Safari
        # contact-autofill fix as history_page.py's _filter_bar_html().
        '<input type="search" id="%s" autocomplete="off" spellcheck="false" autocapitalize="characters" data-filter-input>'
        "</div>"
        '<div class="filter-bar__meta">'
        '<span class="filter-bar__count" data-filter-count>%s</span>'
        '<a href="#%s" data-filter-clear>%s</a>'
        "</div>"
        "</div>"
        '<div class="empty-state" data-filter-empty hidden>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (
        _FILTER_INPUT_ID, escape_html(i18n.t(_FILTER_LABEL_TEXT)),
        layout.icon_html("icon-search"),
        _FILTER_INPUT_ID,
        escape_html(count_text),
        _FILTER_INPUT_ID,
        escape_html(i18n.t(_CLEAR_TEXT)),
        escape_html(i18n.t(_FILTER_EMPTY_HEADING)),
        escape_html(empty_body),
    )


# Single-sourced so the table builder and the mobile card builder can't
# disagree on a header word. Indices 1-4 are read directly by
# _registry_cards_html() for its field labels; index 0 ("Prefix") has no
# card-side label because the prefix is the card's primary line. "Resolve"
# is always appended, never inserted, since those index lookups are
# positional. "Prefix"/"First seen"/"Last seen"/"Example callsign" are
# the same ids airlines_page.py's own RESOLVE_CONTEXT_LABELS uses.
_REGISTRY_HEADERS = (
    i18n.msg("health.prefix", "Prefix"),
    i18n.msg("health.count", "Count"),
    i18n.msg("health.first_seen", "First seen"),
    i18n.msg("health.last_seen", "Last seen"),
    i18n.msg("health.example_callsign", "Example callsign"),
    i18n.msg("health.resolve", "Resolve"),
)

# The per-row deep link to the Airlines resolve surface. Both
# representations (_registry_row_html()'s <td> and
# _registry_cards_html()'s .data-card__action block) build their anchor
# from these same constants, so href/aria-label/text can't drift apart.
RESOLVE_LINK_HREF_TEMPLATE = "/airlines?resolve=%s"
RESOLVE_LINK_ARIA_TEMPLATE = i18n.msg("health.resolve_prefix", "Resolve prefix %s")
RESOLVE_LINK_TEXT = i18n.msg("health.resolve", "Resolve")
RESOLVE_CARD_LINK_TEXT = i18n.msg("health.resolve_this_prefix", "Resolve this prefix")


def _registry_filter_text(prefix):
    """The lowercased, escaped `data-filter-text` value shared by a
    registry `<tr>` (`_registry_row_html()`) and its paired
    `<li class="data-card">` (`_registry_cards_html()`), so the two
    representations' filter text can never diverge.
    """
    return escape_html(prefix.lower() if isinstance(prefix, str) else str(prefix).lower())


# Restated rather than imported from history_page.py: page modules may
# not import each other. display: none inside this table's stacked
# cells, but kept in the DOM in case a future change un-scopes the rule.
_REGISTRY_CELL_SEPARATOR_TEXT = "·"


def _registry_seen_cell_html(raw_ts, now):
    """The First seen / Last seen cell's two stacked lines: a
    Europe/Paris local clock primary line and a relative-age secondary
    line, the same shape `history_page._when_cell_html()` builds for
    Flights' When column. Stacked because the one-line form measured too
    wide for two of six columns to fit unwrapped in French. Degrades
    like `_when_cell_html()`: a falsy timestamp renders empty, an
    unparseable one renders the raw value with no secondary line.

    The secondary line is `layout.relative_time_html()`'s own
    pre-escaped `<time data-relative>` markup, not
    `escape_html(layout.relative_age_text(age))` — interpolated verbatim,
    never re-escaped, so a ticker script can find and update it.
    """
    if not raw_ts:
        return ""
    parsed = layout.parse_iso(raw_ts)
    if parsed is None:
        return '<span class="cell-primary">%s</span>' % escape_html(raw_ts)
    clock_text = layout.local_clock_text(parsed, layout.parse_iso(now))
    age = layout.age_seconds(raw_ts, now)
    html = '<span class="cell-primary" title="%s">%s</span>' % (
        escape_html(_full_local_timestamp_text(raw_ts)), escape_html(clock_text))
    if age is not None:
        html += (
            '<span class="cell-inline-sep">%s</span>'
            '<span class="cell-secondary">%s</span>'
        ) % (
            escape_html(_REGISTRY_CELL_SEPARATOR_TEXT),
            layout.relative_time_html(raw_ts, now))
    return html


def _registry_row_html(index, prefix, count, first_seen, last_seen, example_callsign, now):
    """One `<tr>` for the unresolved-prefix registry table. First
    seen/Last seen return already-safe markup, interpolated verbatim,
    never re-escaped. Appends a sixth `<td>`: a plain `<a>` navigating
    to `/airlines?resolve={prefix}`, never a submit-type control, so
    Health stays read-only.
    """
    row_class = "row-alt" if index % 2 else "row"
    # The desktop table's timestamp cells are stacked (see
    # _registry_seen_cell_html()); the mobile card below keeps calling
    # concise_timestamp_html() directly since it has no width budget to
    # protect. Both still build from the same underlying formatters over
    # the same `now`, so they cannot disagree about what a value is.
    first_seen_html = _registry_seen_cell_html(first_seen, now)
    last_seen_html = _registry_seen_cell_html(last_seen, now)
    escaped_prefix = escape_html(prefix)
    resolve_href = RESOLVE_LINK_HREF_TEMPLATE % escaped_prefix
    resolve_aria = escape_html(i18n.t(RESOLVE_LINK_ARIA_TEMPLATE)) % escaped_prefix
    cells = (
        '<td class="mono">%s</td>' % escaped_prefix,
        "<td>%s</td>" % escape_html(count),
        "<td>%s</td>" % first_seen_html,
        "<td>%s</td>" % last_seen_html,
        '<td class="mono">%s</td>' % escape_html(example_callsign),
        '<td><a href="%s" aria-label="%s">%s</a></td>' % (
            resolve_href, resolve_aria, escape_html(i18n.t(RESOLVE_LINK_TEXT))),
    )
    filter_text = _registry_filter_text(prefix)
    # data-filter-group must match the paired mobile card's value exactly:
    # list-filter.js counts distinct groups, not raw elements, so a
    # mismatch would double "N of N shown" once a row has two DOM forms.
    return '<tr class="%s" data-filter-text="%s" data-filter-group="%d">%s</tr>' % (
        row_class, filter_text, index, "".join(cells))


def _registry_table_html(rows, now):
    """The unresolved-prefix registry table, hand-rolled rather than via
    `layout.data_table()` so each row can carry its own `data-filter-text`
    attribute (that builder has no per-row attribute hook). Matches
    `data_table()`'s CSS classes for visual consistency.
    """
    header_cells = "".join("<th>%s</th>" % escape_html(i18n.t(h)) for h in _REGISTRY_HEADERS)
    body_rows = [
        _registry_row_html(index, prefix, count, first_seen, last_seen, example_callsign, now)
        for index, (prefix, count, first_seen, last_seen, example_callsign) in enumerate(rows)
    ]
    # data-table--registry scopes the stacked-cell rule to this table,
    # additively: the base data-table class and its rules are unchanged.
    return (
        '<div class="data-table-wrap">'
        '<table class="data-table data-table--registry">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (header_cells, "".join(body_rows))


def _registry_cards_html(rows, now):
    """Mobile two-line-plus-disclosure representation of the registry:
    one card per prefix (Prefix/Count and Last seen at rest, First
    seen/Example callsign in a `<details>` disclosure), since a
    horizontal scroller would break the First-seen/Last-seen comparison.
    `data-filter-text`/`data-filter-group` use the same helper and loop
    index as the paired `<tr>`, so the two can't diverge.
    """
    if not rows:
        return ""
    items = []
    for index, (prefix, count, first_seen, last_seen, example_callsign) in enumerate(rows):
        filter_text = _registry_filter_text(prefix)
        primary = (
            '<div class="data-card__primary">'
            '<span class="cell-primary mono">%s</span>'
            '<span class="data-card__value">'
            '<span class="data-card__label">%s</span> %s'
            "</span>"
            "</div>"
        ) % (escape_html(prefix), escape_html(i18n.t(_REGISTRY_HEADERS[1])), escape_html(count))
        secondary = (
            '<div class="data-card__secondary">'
            '<span class="data-card__label">%s</span>%s'
            "</div>"
        ) % (
            escape_html(i18n.t(_REGISTRY_HEADERS[3])),
            layout.concise_timestamp_html(last_seen, now, fallback=""))
        escaped_prefix = escape_html(prefix)
        resolve_href = RESOLVE_LINK_HREF_TEMPLATE % escaped_prefix
        resolve_aria = escape_html(i18n.t(RESOLVE_LINK_ARIA_TEMPLATE)) % escaped_prefix
        action = (
            '<div class="data-card__action">'
            '<a href="%s" aria-label="%s">%s</a>'
            "</div>"
        ) % (resolve_href, resolve_aria, escape_html(i18n.t(RESOLVE_CARD_LINK_TEXT)))
        details = (
            '<details class="data-card__details">'
            "<summary>%s</summary>"
            "<dl>"
            "<dt>%s</dt><dd>%s</dd>"
            '<dt>%s</dt><dd class="mono">%s</dd>'
            "</dl>"
            "</details>"
        ) % (
            escape_html(i18n.t(_MORE_DETAILS_TEXT)),
            escape_html(i18n.t(_REGISTRY_HEADERS[2])),
            layout.concise_timestamp_html(first_seen, now, fallback=""),
            escape_html(i18n.t(_REGISTRY_HEADERS[4])),
            escape_html(example_callsign),
        )
        items.append(
            '<li class="data-card" data-filter-text="%s" data-filter-group="%d">%s%s%s%s</li>'
            % (filter_text, index, primary, secondary, action, details))
    return '<ul class="data-cards">%s</ul>' % "".join(items)


def _registry_section(rows, now):
    header_html = '<p class="text-body section-caption">%s</p>' % escape_html(
        i18n.t(_READ_ONLY_NOTE))

    if not rows:
        return header_html + layout.empty_state(i18n.t(_NO_GAPS_HEADING), i18n.t(_NO_GAPS_BODY))

    filter_html = _registry_filter_bar_html(len(rows))
    cards_html = _registry_cards_html(rows, now)
    table_html = _registry_table_html(rows, now)
    # Cards must render before the table: style.css's
    # `.data-cards ~ .data-table-wrap` sibling-combinator toggle depends
    # on this DOM order.
    return header_html + filter_html + cards_html + table_html


def _stats_cards_html(rows):
    """Mobile stacked-prose representation of the resolution-statistics
    table: one `<li class="data-card">` per `(label, gloss, count)` in
    `rows`. A column of full sentences must wrap, not scroll
    (`.data-table--prose` in style.css), so the Description sentence
    renders full and untruncated rather than behind a disclosure.
    """
    if not rows:
        return ""
    items = []
    for label, gloss, count in rows:
        primary = (
            '<div class="data-card__primary">'
            '<span class="cell-primary">%s</span>'
            '<span class="data-card__value">'
            '<span class="data-card__label">%s</span> %s'
            "</span>"
            "</div>"
        ) % (escape_html(label), escape_html(i18n.t(_STATS_HEADERS[2])), escape_html(count))
        desc = '<p class="data-card__desc">%s</p>' % escape_html(gloss)
        items.append('<li class="data-card">%s%s</li>' % (primary, desc))
    return '<ul class="data-cards">%s</ul>' % "".join(items)


def _stats_table_html(stats):
    """The resolution-statistics breakdown table, with its `.data-cards`
    mobile sibling emitted first (style.css's sibling-combinator toggle
    depends on that order — do not reorder). Empty when there is nothing
    to show: `_resolution_rate_tile_html()` already carries that message.
    The only table whose Description column holds real prose, so it is
    the only one opted into `layout.data_table()`'s `prose` keyword and
    `desc` column role.
    """
    if stats is _DB_UNAVAILABLE or stats["total"] == 0:
        return ""
    return _stats_cards_html(stats["rows"]) + layout.data_table(
        [i18n.t(header) for header in _STATS_HEADERS], stats["rows"],
        desc_columns=(1,), prose=True)


def _resolution_rate_tile_html(stats):
    """The Resolution-rate stat_tile's content: a two-line figure inside
    the tile card.
    """
    if stats is _DB_UNAVAILABLE:
        return _unavailable_block()
    if stats["total"] == 0:
        # Translate the heading first, then interpolate, so the "%d"
        # placeholder survives translation. Compact variant: this block
        # lands inside a .stat-tile, whose 12px caption inverts under the
        # default form's 22px heading. No .widget-verdict here — this
        # tile makes no pass/fail judgement (status=None, no status
        # function exists for it).
        return layout.empty_state(
            i18n.t(_NO_STATS_HEADING) % RESOLUTION_WINDOW_DAYS,
            i18n.t(_NO_STATS_BODY), compact=True)
    # The Emphasis slot holds the figure (.stat-tile__value), not a
    # verdict word, since this tile carries no pass/fail judgement.
    detail_template = (
        _RESOLUTION_DETAIL_SINGULAR_TEMPLATE if stats["total"] == 1
        else _RESOLUTION_DETAIL_TEMPLATE)
    return (
        '<p class="stat-tile__value">%s</p>'
        '<div class="%s">%s</div>'
    ) % (
        escape_html(i18n.t(_RESOLVED_PCT_TEMPLATE) % stats["resolved_pct"]),
        _TILE_DETAIL_CLASS,
        escape_html(i18n.t(detail_template) % (
            RESOLUTION_WINDOW_DAYS, stats["total"])),
    )


def _check_in_regularity_cells(gap_rows, wake_interval_s, now):
    """`(cells, counts, day_labels)` for the check-in regularity grid:
    one entry per Europe/Paris calendar day, oldest first. Every
    verdict, including a day with no record, goes through
    `wake.classify_check_in_gap()`, the same function the Frame tile
    consumes. A day is judged by its longest observed gap, not an
    average, so one long hole isn't hidden by an otherwise-ordinary day.
    Calendar arithmetic is ordinal, correct across a DST boundary where
    a fixed per-day second count is not. Never raises.
    """
    worst = {}
    for row in gap_rows or ():
        try:
            day, gap = row.get("day"), row.get("gap_s")
        except AttributeError:
            continue
        if not isinstance(day, str) or not draw.is_number(gap):
            continue
        if day not in worst or gap > worst[day]:
            worst[day] = gap

    parsed = layout.parse_iso(now)
    if parsed is None:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    last = parsed.astimezone(layout.LOCAL_TZ).date().toordinal()

    cells = []
    labels = []
    counts = dict.fromkeys(CHECK_IN_STATE_TEXT, 0)
    for ordinal in range(last - CHECK_IN_WINDOW_DAYS + 1, last + 1):
        day = date.fromordinal(ordinal)
        gap = worst.get(day.isoformat())
        state = wake.classify_check_in_gap(gap, wake_interval_s)
        counts[state] = counts.get(state, 0) + 1
        day_text = "%d %s" % (day.day, layout.month_abbr(day.month))
        labels.append(day_text)
        verdict_text = i18n.t(CHECK_IN_STATE_TEXT.get(
            state, CHECK_IN_STATE_TEXT[wake.CHECK_IN_UNKNOWN]))
        if gap is None:
            title = i18n.t(CHECK_IN_CELL_TITLE_NONE) % (day_text, verdict_text)
        else:
            title = i18n.t(CHECK_IN_CELL_TITLE) % (
                day_text, verdict_text, layout.duration_text(gap))
        cells.append((state, title))
    return cells, counts, labels


def _check_in_regularity_section_html(gap_rows, wake_interval_s, now):
    """The "Check-in regularity" card: heading, visible caption plus its
    disclosure, the grid, its date labels and the four-state key.
    `wake_interval_s` of `None` degrades to
    `device_staleness_thresholds()`'s bare floors, and the caption names
    those floors rather than a cadence nobody configured. Only
    `CHECK_IN_CAPTION_OBSERVED` is visible; every other clause moves
    into a `<details>` disclosure, the same idiom `_battery_section()`
    and `_corroboration_details_html()` use.
    """
    if gap_rows is _DB_UNAVAILABLE:
        body = _unavailable_block()
    else:
        cells, counts, labels = _check_in_regularity_cells(
            gap_rows, wake_interval_s, now)
        observed = sum(
            counts.get(state, 0) for state in (
                wake.CHECK_IN_ON_CADENCE, wake.CHECK_IN_LATE, wake.CHECK_IN_MISSING))
        grid_html, dropped = draw.regularity_grid(
            cells,
            label=i18n.t(CHECK_IN_GRID_LABEL) % (
                CHECK_IN_WINDOW_DAYS,
                counts.get(wake.CHECK_IN_ON_CADENCE, 0),
                counts.get(wake.CHECK_IN_LATE, 0),
                counts.get(wake.CHECK_IN_MISSING, 0),
                counts.get(wake.CHECK_IN_UNKNOWN, 0)))
        # Read past anything the drawing dropped, so the two labels can
        # only ever name cells that are on screen.
        oldest = labels[dropped] if dropped < len(labels) else labels[-1]
        visible_caption = i18n.t(CHECK_IN_CAPTION_OBSERVED)
        disclosure_clauses = []
        if not observed:
            disclosure_clauses.append(i18n.t(CHECK_IN_CAPTION_EMPTY))
        if draw.is_number(wake_interval_s) and wake_interval_s > 0:
            disclosure_clauses.append(
                i18n.t(CHECK_IN_CAPTION_CADENCE) % layout.duration_text(wake_interval_s))
        else:
            disclosure_clauses.append(i18n.t(CHECK_IN_CAPTION_CADENCE_FALLBACK))
        disclosure_clauses.append(i18n.t(CHECK_IN_CAPTION_NOT_PROOF))
        disclosure_html = (
            '<details class="readings-disclosure"><summary>%s</summary><p>%s</p></details>'
        ) % (
            escape_html(i18n.t(_MORE_DETAILS_TEXT)),
            escape_html(" ".join(disclosure_clauses)))
        body = (
            '<p class="text-label section-caption">%s</p>'
            '%s'
            '<div class="%s">%s<div class="%s">%s%s</div></div>'
            '%s'
        ) % (
            escape_html(visible_caption),
            disclosure_html,
            escape_html(CHECK_IN_GRID_CLASS), grid_html,
            escape_html(CHECK_IN_SCALE_CLASS),
            draw.label_span(oldest, hidden=False),
            draw.label_span(labels[-1], hidden=False),
            _check_in_key_html())
    # Plain .page-section, not page-section--nested: that modifier is
    # reserved for the two cards migrated into Server & data.
    return (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>%s</section>'
    ) % (escape_html(i18n.t(CHECK_IN_SECTION_HEADING)), body)


def _check_in_key_html():
    """Legend for the regularity grid, in classifier order (best to worst,
    then absence). The swatch takes the cell's own class rather than a
    copied colour, so key and grid share one `currentColor` declaration
    and cannot disagree. aria-hidden: the label text is the reading.
    """
    items = []
    for state in (wake.CHECK_IN_ON_CADENCE, wake.CHECK_IN_LATE,
                  wake.CHECK_IN_MISSING, wake.CHECK_IN_UNKNOWN):
        items.append(
            '<span class="%s"><span class="%s %s" aria-hidden="true"></span>'
            '<span class="drawing-axis-label">%s</span></span>'
            % (escape_html(CHECK_IN_KEY_ITEM_CLASS),
               escape_html(CHECK_IN_KEY_SWATCH_CLASS),
               escape_html(draw.cell_class(state)),
               escape_html(i18n.t(CHECK_IN_STATE_TEXT[state]))))
    return '<div class="%s">%s</div>' % (
        escape_html(CHECK_IN_KEY_CLASS), "".join(items))


def _stats_section_html(stats):
    """The "How well we name flights" nested page-section, or the empty
    string when the window is genuinely empty (`stats["total"] == 0`).
    A DB-unavailable `stats` still renders: that is a different failure
    mode from an empty window.
    """
    if stats is not _DB_UNAVAILABLE and stats["total"] == 0:
        return ""
    # No status modifier: resolution_stats() returns no verdict, so this
    # card carries no pass/fail state — a neutral hairline is correct.
    return '<section class="page-section page-section--nested"><h2 class="text-heading">%s</h2>%s</section>' % (
        escape_html(i18n.t(STATS_SECTION_HEADING)), _stats_table_html(stats))


# The Today band: one Paris day of device check-ins.
# The read is bounded as a correctness constraint, not a performance one:
# recent_device_health() returns the newest N rows, so a limit smaller
# than a day's check-ins would silently hand the band a few hours and
# caption them as the whole day. _day_band_html() below also detects a
# truncated read and stops the caption claiming a total.
DAY_BAND_ROW_LIMIT = 3000

# "Today" is owned by companion/i18n_fr/flights.py, not home.py — the
# same id history_page.py's own day-separator heading uses.
DAY_BAND_HEADING = i18n.msg("flights.today", "Today")
# The canvas's accessible name; a named group rather than aria-hidden,
# since the band is the only statement of this data.
DAY_BAND_LABEL = i18n.msg(
    "home.the_frame_s_check_ins_through_the_day_midnight",
    "The frame's check-ins through the day, midnight to midnight")
DAY_BAND_HOUR_LABELS = ("00:00", "12:00", "24:00")
DAY_BAND_EMPTY_TEXT = i18n.msg(
    "home.no_check_ins_recorded_on", "No check-ins recorded on %s.")
DAY_BAND_ONE_TEXT = i18n.msg("home.1_check_in_on", "1 check-in on %s.")
DAY_BAND_COUNT_TEXT = i18n.msg("home.check_ins_on", "%s check-ins on %s.")
# Appended only when draw.day_band() reports a collapse, so a reader who
# counts the marks and gets fewer is not left thinking the band lost some.
DAY_BAND_COLLAPSED_TEXT = i18n.msg(
    "home.some_marks_are_merged_check_ins_closer_together",
    "Some marks are merged — check-ins closer together than the band can "
    "separate are drawn as one.")
DAY_BAND_QUIET_TEXT = i18n.msg(
    "home.shaded_quiet_hours_to", "Shaded: quiet hours, %s to %s.")


def _paris_day_bounds(now):
    """`(day, day_start_epoch, day_seconds)` for the Europe/Paris day
    `now` falls in, or None when `now` does not parse.

    `day_seconds` is measured between two real Paris midnights and never
    assumed to be 86400: a Europe/Paris day is 23 or 25 hours twice a
    year, and a band assuming 86400 would misplace midday and leave an
    hour of its own width unreachable. `layout.LOCAL_TZ` is the one
    timezone constant every timestamp on this page already formats
    through, so the band and the row beneath it cannot disagree about
    which day it is.
    """
    parsed = history_db.instant_or_none(now)
    if parsed is None:
        return None
    day = parsed.astimezone(layout.LOCAL_TZ).date()
    start = datetime.combine(day, time(0), tzinfo=layout.LOCAL_TZ)
    end = datetime.combine(day + timedelta(days=1), time(0), tzinfo=layout.LOCAL_TZ)
    return day, start.timestamp(), end.timestamp() - start.timestamp()


def _day_band_instants(rows, day):
    """The epoch seconds of every row in `rows` whose stored `ts` falls
    on the Europe/Paris calendar day `day`.

    Bucketed through `history_db.paris_day_or_none()`, the same date
    path `check_in_gaps()` and `daily_battery_averages()` use, so a mark
    on this band and a row in Health's own day-bucketed data can never
    disagree about which day a check-in belongs to. This is a real
    bucketing, not a filter: Paris is UTC+1 or UTC+2, so a check-in at
    00:30 Paris is stored as 22:30 UTC on the previous date, and
    comparing UTC dates directly would silently attribute it to the
    wrong day.
    """
    instants = []
    for row in rows or ():
        ts = row.get("ts") if isinstance(row, dict) else None
        if history_db.paris_day_or_none(ts) != day:
            continue
        parsed = history_db.instant_or_none(ts)
        if parsed is not None:
            instants.append(parsed.timestamp())
    return instants


def _quiet_hours_window(config, day_start, day_seconds):
    """`((start_epoch, end_epoch), start_hm, end_hm)` for the configured
    quiet-hours window placed on the band's own day, or `(None, None,
    None)` when quiet hours are not enabled or the config is unusable.

    The enabled test is `is True`, not truthiness, matching
    `device_config.quiet_hours_status()`; both time strings go through
    `device_config.normalise_quiet_hours_time()` so a hand-edited config
    cannot put an unvalidated string into the arithmetic.
    `quiet_hours_status()` itself answers an activity question
    (seconds remaining and when it ends), not the window's two absolute
    ends regardless of activity, so this function derives them directly
    instead. The end may precede the start for a night window;
    `draw.day_band()` is where that becomes two spans.
    """
    if not isinstance(config, dict) or config.get("quiet_hours_enabled") is not True:
        return None, None, None
    try:
        start_hm = device_config.normalise_quiet_hours_time(
            config.get("quiet_hours_start"), device_config.DEFAULT_QUIET_HOURS_START)
        end_hm = device_config.normalise_quiet_hours_time(
            config.get("quiet_hours_end"), device_config.DEFAULT_QUIET_HOURS_END)
        start = day_start + _hm_seconds(start_hm)
        end = day_start + _hm_seconds(end_hm)
    except (TypeError, ValueError):
        return None, None, None
    if start > day_start + day_seconds or end > day_start + day_seconds:
        # A DST day is 23 or 25 hours long, so an "HH:MM" offset counted
        # from midnight can land past the band's own right edge. Rather
        # than clamp — which would silently redraw the window the user
        # configured — the shading is dropped and the caption with it.
        return None, None, None
    return (start, end), start_hm, end_hm


def _hm_seconds(hm):
    """Seconds from midnight for a normalised "HH:MM" string."""
    hours, _, minutes = hm.partition(":")
    return int(hours) * 3600 + int(minutes) * 60


def _day_band_html(rows, now, config):
    """The day band's <section>, or "" when there is no day to draw.

    `rows` is the device_health read Health's render() makes; this
    function re-queries nothing. An unreadable history.db arrives as
    `_DB_UNAVAILABLE` and renders nothing at all, since an empty band
    would falsely say "no check-ins today" for a failed read. A day that genuinely
    holds no check-ins renders the band empty instead, matching this
    page's "no chrome with no data" rule.
    """
    if rows is _DB_UNAVAILABLE or rows is None:
        return ""
    bounds = _paris_day_bounds(now)
    if bounds is None:
        return ""
    day, day_start, day_seconds = bounds
    instants = _day_band_instants(rows, day)
    window, start_hm, end_hm = _quiet_hours_window(
        config, day_start, day_seconds)
    canvas, collapsed = draw.day_band(
        day_start, day_seconds, instants, window=window,
        label=i18n.t(DAY_BAND_LABEL))
    day_text = day.isoformat()

    # The caption is written from `collapsed`, not from the row count
    # alone: when the band merged anything it says so, so a reader who
    # counts the marks and gets fewer is not told the drawing lost some.
    total = len(instants)
    if not total:
        caption = i18n.t(DAY_BAND_EMPTY_TEXT) % (day_text,)
    elif total == 1:
        caption = i18n.t(DAY_BAND_ONE_TEXT) % (day_text,)
    else:
        caption = i18n.t(DAY_BAND_COUNT_TEXT) % (total, day_text)
    sentences = [escape_html(caption)]
    if collapsed or len(rows) >= DAY_BAND_ROW_LIMIT:
        sentences.append(escape_html(i18n.t(DAY_BAND_COLLAPSED_TEXT)))
    if window is not None:
        sentences.append(escape_html(i18n.t(DAY_BAND_QUIET_TEXT) % (start_hm, end_hm)))
    hours = "".join(
        "<span>%s</span>" % escape_html(label) for label in DAY_BAND_HOUR_LABELS)
    return (
        '<section class="page-section day-band" '
        'aria-labelledby="health-day-band">'
        '<h2 class="text-heading" id="health-day-band">%s</h2>'
        '%s'
        '<p class="day-band__hours text-label mono">%s</p>'
        '<p class="text-label">%s</p>'
        "</section>"
    ) % (escape_html(i18n.t(DAY_BAND_HEADING)), canvas, hours, " ".join(sentences))
